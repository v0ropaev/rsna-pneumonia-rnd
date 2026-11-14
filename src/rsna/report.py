"""HW2 experiment-tracking report: ledger, config-level summary, ablation deltas and figures.

CLI: python -m rsna.report [--results results [/abs/other/results ...]] [--primary-variant NAME] [--with-test]
                          [--n-boot 2000] [--out-md results/experiments.md] [--fig-dir reports/figures]

Inputs (all optional, partial results are fine; what is missing is printed):
* run dirs = children of every --results dir that hold config.yaml (training writes config.yaml first, meta.json and
  the prediction tables at the end, so a run without meta.json is "in progress"). Runs are grouped by the stem of
  `run.config_path` in config.yaml (+ `[overrides]` if any); smoke runs (limit_*/max_steps/smoke) are listed in the
  ledger but excluded from every summary.
* post-hoc variants of a run = `<run>/posthoc/<variant>/` with val_predictions.csv + val_image_scores.csv
  (+ threshold_sweep.csv, else the sweep is recomputed on val; optional variant.json {"description": ...}).
  `--primary-variant NAME` makes that variant the run's main result wherever it exists (e.g. a VAL-tuned box_scale);
  the raw training output then appears as the post-hoc ablation "no_boxscale" (it has box_scale 1.0 and the
  configured score_mode; "as_trained" if the config itself sets box_scale != 1.0) unless such a variant dir exists.
* `results/experiments.csv` of every --results dir, results/baseline_trivial/*/val_metrics.json, MLflow (sqlite db
  of this checkout, read only if the file exists).
Every val number uses the run's VAL-selected score threshold (argmax of its sweep), so val mAP is selection-biased.
Units whose box_scale was tuned on val (variant.json box_scale_source "tuned ...") carry one more selection on the same
images; val deltas of a tuned unit against an untuned one are flagged (Full − box_scale is >= 0 by construction) and
the selection-free estimates are the cross-fitted gain of `rsna.posthoc tune` and the test rows. B is the HW1 baseline
as trained (box_scale 1.0), so "Full − all (vs B)" includes I3 by design. The 2×2 aug × cls factorial uses the
as-trained tables of all four configs (box_scale 1.0 everywhere), so the post-hoc I3 never leaks into it.
Ablation deltas are paired bootstraps over val images, seed-matched; the pooled estimate averages the per-seed
differences and resamples images jointly for all seeds (image noise only; seed spread is shown by the per-seed points).
Test numbers come only from existing `test_metrics.json` (written by rsna.evaluate); test labels are read only with
--with-test (paired test deltas of Full vs every other config and vs its post-hoc ablations; reported, never used for
decisions). image AUC = ROC-AUC of the unit's own max box score (the score that decides sens/spec, so it differs between
post-hoc variants); cls AUC = ROC-AUC of the cls head probability (cls models only; identical across their variants).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from . import paths
from .evaluate import check_fresh, error_decomposition, load_meta, read_preds
from .metric import (_chunks, image_level_metrics, load_gt, paired_bootstrap_diff, preds_from_df, rsna_map,
                     threshold_sweep)

# ----------------------------------------------------------------------------- design of the HW2 study

CONFIG_ORDER = ["baseline", "b_aug", "b_cls", "full"]
CONFIG_LABEL = {"baseline": "B", "b_aug": "B+aug", "b_cls": "B+cls", "full": "Full"}
EXPECTED_SEEDS = {"baseline": [0, 1, 2], "b_aug": [0, 1], "b_cls": [0, 1], "full": [0, 1, 2]}
EXPECTED_VARIANTS = {"full": ["no_gating", "no_boxscale"]}
REF_CONFIG, BASE_CONFIG = "full", "baseline"
ABLATION_LABEL = {"b_cls": "Full − aug  (vs B+cls)", "b_aug": "Full − cls head & gating  (vs B+aug)",
                  "baseline": "Full − all  (vs B)", "no_gating": "Full − gating  (post hoc, same ckpt)",
                  "no_boxscale": "Full − box_scale  (post hoc, same ckpt)",
                  "as_trained": "Full − box_scale tuning  (as trained, same ckpt)"}
TRIVIAL = ["prior_boxes", "prior_boxes_ap"]

# light chart theme (dataviz reference palette); baseline is the neutral reference
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FIXED_COLOR = {"full": SLOTS[0], "b_aug": SLOTS[1], "b_cls": SLOTS[2], "baseline": "#8a8984"}
MARKERS = {"baseline": "o", "b_aug": "s", "b_cls": "^", "full": "D"}


def config_color(name: str, known: list[str]) -> str:
    if name in FIXED_COLOR:
        return FIXED_COLOR[name]
    extra = [c for c in known if c not in FIXED_COLOR]
    return SLOTS[3 + extra.index(name) % 5] if name in extra else INK2


def style() -> None:
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                         "axes.titlesize": 10, "legend.frameon": False, "lines.linewidth": 2})


# ----------------------------------------------------------------------------- discovery

@dataclass
class Run:
    name: str
    dir: Path
    cfg: dict[str, Any]
    meta: dict[str, Any]
    config: str
    seed: int | None
    smoke: bool
    complete: bool
    variants: dict[str, Path] = field(default_factory=dict)


@dataclass
class Unit:
    """One evaluated prediction set: a run as trained (variant "") or one of its post-hoc variants."""
    run: Run
    variant: str
    dir: Path

    @property
    def key(self) -> str:
        return self.run.name + (f"/{self.variant}" if self.variant else "")


def config_name(cfg: dict[str, Any], run_name: str) -> str:
    """Grouping key: stem of the config file the run was trained from (+ overrides, which change the config)."""
    r = cfg.get("run") or {}
    stem = Path(r["config_path"]).stem if r.get("config_path") else re.sub(r"_s\d+$", "", run_name)
    ov = r.get("overrides") or []
    return f"{stem}[{';'.join(ov)}]" if ov else stem


def is_smoke(cfg: dict[str, Any]) -> bool:
    r = cfg.get("run") or {}
    return bool(r.get("smoke")) or any(r.get(k) is not None for k in ("max_steps", "limit_train", "limit_val"))


def has_tables(d: Path, split: str = "val") -> bool:
    return (d / f"{split}_predictions.csv").exists() and (d / f"{split}_image_scores.csv").exists()


def load_run(d: Path) -> Run:
    cfg = yaml.safe_load((d / "config.yaml").read_text()) or {}
    meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
    seed = (cfg.get("run") or {}).get("seed", meta.get("seed"))
    ph = d / "posthoc"
    variants = {v.name: v for v in sorted(ph.iterdir()) if v.is_dir() and has_tables(v)} if ph.is_dir() else {}
    return Run(d.name, d, cfg, meta, config_name(cfg, d.name), None if seed is None else int(seed), is_smoke(cfg),
               bool(meta) and has_tables(d), variants)


def discover(results_dirs: Iterable[Path]) -> tuple[list[Run], list[str]]:
    """All run dirs under the results dirs (a dir may itself be a run); the first occurrence of a name wins."""
    runs: dict[str, Run] = {}
    notes: list[str] = []
    for root in results_dirs:
        if not root.is_dir():
            notes.append(f"results dir {root} does not exist")
            continue
        cands = [root] if (root / "config.yaml").exists() else sorted(p for p in root.iterdir() if (p / "config.yaml").exists())
        for d in cands:
            if d.name in runs:
                notes.append(f"duplicate run name {d.name}: using {runs[d.name].dir}, ignoring {d}")
                continue
            runs[d.name] = load_run(d)
    return list(runs.values()), notes


def primary_unit(run: Run, primary_variant: str | None) -> Unit:
    if primary_variant and primary_variant in run.variants:
        return Unit(run, primary_variant, run.variants[primary_variant])
    return Unit(run, "", run.dir)


def posthoc_units(run: Run, primary_variant: str | None) -> list[Unit]:
    """Variants other than the primary; the raw output joins them when a variant is primary (see module doc)."""
    prim = primary_unit(run, primary_variant)
    out = [Unit(run, v, d) for v, d in run.variants.items() if v != prim.variant]
    if prim.variant and not any(_is_as_trained(run, d) for d in run.variants.values()):
        raw = "no_boxscale" if float((run.cfg.get("decode") or {}).get("box_scale", 1.0)) == 1.0 else "as_trained"
        if raw not in run.variants:
            out.insert(0, Unit(run, raw, run.dir))
    return out


def _is_as_trained(run: Run, vdir: Path) -> bool:
    """A variant that reproduces the stored tables (box_scale 1.0 and the configured score_mode)."""
    p = vdir / "variant.json"
    if not p.exists():
        return False
    v = json.loads(p.read_text())
    d = run.cfg.get("decode") or {}
    return float(v.get("box_scale", -1)) == float(d.get("box_scale", 1.0)) == 1.0 and \
        v.get("score_mode") == d.get("score_mode", "heatmap")


def group_by_config(runs: list[Run]) -> dict[str, dict[int, Run]]:
    """config -> seed -> run, complete non-smoke runs only; ordered by CONFIG_ORDER, then by name."""
    g: dict[str, dict[int, Run]] = {}
    for r in runs:
        if r.complete and not r.smoke and r.seed is not None:
            g.setdefault(r.config, {})[r.seed] = r
    order = sorted(g, key=lambda c: (CONFIG_ORDER.index(c) if c in CONFIG_ORDER else len(CONFIG_ORDER), c))
    return {c: dict(sorted(g[c].items())) for c in order}


def missing_report(runs: list[Run], groups: dict[str, dict[int, Run]], primary_variant: str | None) -> list[str]:
    lines = []
    for c, seeds in EXPECTED_SEEDS.items():
        have = groups.get(c, {})
        for s in seeds:
            if s not in have:
                running = [r.name for r in runs if r.config == c and r.seed == s and not r.complete and not r.smoke]
                lines.append(f"{c} seed {s}: " + (f"in progress / incomplete ({', '.join(running)})" if running
                                                   else "not run"))
            else:
                run = have[s]
                want = list(EXPECTED_VARIANTS.get(c, [])) + ([primary_variant] if primary_variant and c != BASE_CONFIG
                                                             else [])  # B = HW1 baseline as trained, by design
                if primary_variant and primary_variant in run.variants:  # the raw tables serve as "no_boxscale"
                    want = [v for v in want if v != "no_boxscale"]
                for v in want:
                    if v not in run.variants:
                        lines.append(f"{c} seed {s}: post-hoc variant '{v}' missing ({run.dir / 'posthoc' / v})")
    for r in runs:
        if not r.complete and not r.smoke and r.config not in EXPECTED_SEEDS:
            lines.append(f"{r.name}: incomplete (no meta.json / prediction tables)")
    return lines


# ----------------------------------------------------------------------------- evaluation of one unit

@dataclass
class Evaluated:
    unit: Unit
    thr: float
    sweep: pd.DataFrame
    per_image: pd.Series  # AP per val image at thr (NaN = excluded)
    metrics: dict[str, Any]


def unit_metrics(pred_df: pd.DataFrame, img_df: pd.DataFrame | None, ids: list[str], gt: dict[str, np.ndarray],
                 target: pd.Series, thr: float) -> tuple[dict[str, Any], pd.Series]:
    """mAP, image-level and error-decomposition metrics of one prediction table at score threshold thr."""
    pred = preds_from_df(pred_df)
    m, per = rsna_map(gt, pred, ids, score_threshold=thr, return_per_image=True)
    t = target.loc[ids]
    has = pd.Series([i in pred and bool((pred[i][1] >= thr).any()) for i in ids], index=t.index)
    score = np.array([pred[i][1].max() if i in pred and len(pred[i][1]) else 0.0 for i in ids])  # the unit's own scores
    il = image_level_metrics(t.to_numpy(), score)
    cls_auc = np.nan
    if img_df is not None and "cls_prob" in img_df.columns:
        cls_auc = image_level_metrics(t.to_numpy(), img_df.set_index("patientId")["cls_prob"].reindex(ids).fillna(0.0)
                                      .to_numpy())["roc_auc"]
    e = error_decomposition(per, t, has)
    pos, neg = t == 1, t == 0
    return {"map": m, "thr": thr, "n_images": len(ids), "n_scored": int(per.notna().sum()),
            "image_auc": il["roc_auc"], "image_pr_auc": il["pr_auc"], "cls_auc": cls_auc,
            "sensitivity": float(has[pos].mean()) if pos.any() else np.nan,
            "specificity": float((~has[neg]).mean()) if neg.any() else np.nan,
            "fp_image_rate": e["fp_image_rate"], "map_pos": e["map_pos"], "loss_fp_neg": e["loss_fp_neg"],
            "loss_missed_pos": e["loss_missed_pos"], "loss_loc_pos": e["loss_loc_pos"]}, per


def evaluate_unit(u: Unit, gt: dict[str, np.ndarray], target: pd.Series, split: str = "val") -> Evaluated:
    img = pd.read_csv(u.dir / f"{split}_image_scores.csv", dtype={"patientId": str})
    ids = img["patientId"].tolist()
    pred_df = read_preds(u.dir / f"{split}_predictions.csv")
    sweep_path = u.dir / "threshold_sweep.csv"
    if sweep_path.exists():
        sweep = pd.read_csv(sweep_path)
    elif split == "val":
        sweep = threshold_sweep(gt, preds_from_df(pred_df), ids)
    else:  # recomputing the sweep here would select the threshold on `split`
        raise FileNotFoundError(f"{sweep_path} (the VAL sweep) missing: cannot evaluate {u.key} on {split}")
    thr = float(sweep.loc[sweep["map"].idxmax(), "thr"])  # always the VAL sweep, also for split=test
    mt, per = unit_metrics(pred_df, img, ids, gt, target, thr)
    return Evaluated(u, thr, sweep, per, mt)


def tuned_on_val(u: Unit) -> bool:
    """The unit's box_scale was selected on val (post-hoc variant with box_scale_source 'tuned ...')."""
    p = u.dir / "variant.json"
    return bool(u.variant) and p.exists() and str(json.loads(p.read_text()).get("box_scale_source", "")).startswith("tuned")


def load_test_metrics(u: Unit) -> dict[str, Any] | None:
    """Existing <unit>/test_metrics.json (rsna.evaluate) if it belongs to the current training run, else None."""
    p = u.dir / "test_metrics.json"
    if not p.exists():
        return None
    mt = json.loads(p.read_text())
    try:
        if not u.variant or "train_run" in mt:
            check_fresh(u.run.dir, mt, "test_metrics.json")
    except ValueError as e:
        print(f"[report] skip stale {p}: {e}")
        return None
    e = mt.get("errors") or {}
    return {"map": mt.get("map"), "ci_lo": mt.get("ci_lo"), "ci_hi": mt.get("ci_hi"), "image_auc": mt.get("image_roc_auc"),
            "sensitivity": mt.get("sensitivity"), "specificity": mt.get("specificity"),
            "fp_image_rate": e.get("fp_image_rate"), "map_pos": e.get("map_pos")}


# ----------------------------------------------------------------------------- paired statistics

def contrast_bootstrap(groups: list[list[tuple[float, pd.Series]]], n_boot: int = 2000, seed: int = 0,
                       alpha: float = 0.05) -> dict[str, Any]:
    """Bootstrap of a linear contrast of mAPs, averaged over groups (seeds), images resampled jointly.

    groups[g] = [(coef, per-image AP series), ...]; statistic = mean_g sum_t coef * mAP_t, mAP = nanmean (excluded
    images are NaN, as in metric.paired_bootstrap_diff). All series are restricted to their common image ids; each
    replicate draws ONE image resample used for every term and seed (pairing). A single group [(1, a), (-1, b)] on
    equal ids reproduces metric.paired_bootstrap_diff(a, b) exactly (same seed).
    """
    terms = [t for g in groups for t in g]
    if not terms:
        raise ValueError("empty contrast")
    idx = terms[0][1].index
    for _, s in terms[1:]:
        idx = idx.intersection(s.index, sort=False)
    n = len(idx)
    arr = [(c / len(groups), s.reindex(idx).to_numpy(np.float64)) for c, s in terms]
    x0 = [(c, np.where(np.isnan(x), 0.0, x), ~np.isnan(x)) for c, x in arr]
    point = float(sum(c * (np.nanmean(x) if (~np.isnan(x)).any() else np.nan) for c, x in arr))
    rng = np.random.default_rng(seed)
    out = []
    for m in _chunks(n_boot, n):
        r = rng.integers(0, n, (m, n))
        stat = np.zeros(m)
        with np.errstate(invalid="ignore", divide="ignore"):
            for c, v, ok in x0:
                stat += c * v[r].sum(1) / ok[r].sum(1)
        out.append(stat)
    d = np.concatenate(out)
    d = d[~np.isnan(d)]
    lo, hi = np.quantile(d, [alpha / 2, 1 - alpha / 2]) if len(d) else (np.nan, np.nan)
    return {"diff": point, "lo": float(lo), "hi": float(hi), "p_diff_le_0": float((d <= 0).mean()) if len(d) else np.nan,
            "n_images": n, "n_groups": len(groups), "n_boot": len(d)}


def seed_pairs(ref: dict[int, Any], other: dict[int, Any]) -> list[tuple[int, Any, Any]]:
    """Seed-matched pairs (seed, ref item, other item) over the seeds both sides have."""
    return [(s, ref[s], other[s]) for s in sorted(set(ref) & set(other))]


def ablation_rows(ref: dict[int, Evaluated], others: dict[str, dict[int, Evaluated]], n_boot: int,
                  split: str = "val") -> list[dict[str, Any]]:
    """Δ = mAP(ref) − mAP(ablation): per seed (paired bootstrap) and pooled over matched seeds."""
    rows = []
    for name, ev in others.items():
        pairs = seed_pairs(ref, ev)
        if not pairs:
            continue
        per_seed = []
        for s, a, b in pairs:
            ids = a.per_image.index.intersection(b.per_image.index, sort=False)
            d = paired_bootstrap_diff(a.per_image.loc[ids], b.per_image.loc[ids], n_boot=n_boot)
            per_seed.append({"seed": s, "diff": d["diff"], "lo": d["lo"], "hi": d["hi"],
                             "ref": a.unit.key, "abl": b.unit.key})
        pooled = contrast_bootstrap([[(1.0, a.per_image), (-1.0, b.per_image)] for _, a, b in pairs], n_boot=n_boot)
        biased = split == "val" and any(tuned_on_val(a.unit) and not tuned_on_val(b.unit) for _, a, b in pairs)
        rows.append({"ablation": name, "label": ABLATION_LABEL.get(name, f"Full vs {name}"), "split": split,
                     "seeds": [s for s, _, _ in pairs], **pooled, "per_seed": per_seed, "box_scale_selection": biased})
    return rows


def factorial_rows(ev: dict[str, dict[int, Evaluated]], n_boot: int) -> list[dict[str, Any]]:
    """2x2 (aug × cls) main effects and interaction on seeds where all four configs exist.

    `ev` must hold comparable cells (build() passes the as-trained units: box_scale 1.0 in every cell); mixing tuned
    and untuned cells shifts each main effect by δ/2 and the interaction by δ."""
    cells = ["baseline", "b_aug", "b_cls", "full"]
    if not all(c in ev for c in cells):
        return []
    seeds = sorted(set.intersection(*(set(ev[c]) for c in cells)))
    if not seeds:
        return []
    coefs = {"aug main effect": {"b_aug": .5, "full": .5, "baseline": -.5, "b_cls": -.5},
             "cls main effect": {"b_cls": .5, "full": .5, "baseline": -.5, "b_aug": -.5},
             "interaction aug×cls": {"full": 1, "baseline": 1, "b_aug": -1, "b_cls": -1}}
    return [{"effect": k, "seeds": seeds, **contrast_bootstrap(
        [[(c, ev[cfg][s].per_image) for cfg, c in w.items()] for s in seeds], n_boot=n_boot)} for k, w in coefs.items()]


# ----------------------------------------------------------------------------- ledger, summary, markdown

def _short(text: str, n: int = 90) -> str:
    t = " ".join(str(text or "").split())
    first = re.split(r"(?<=[.;:])\s", t, maxsplit=1)[0]
    return first if len(first) <= n else first[: n - 1] + "…"


def read_ledgers(results_dirs: Iterable[Path]) -> pd.DataFrame:
    frames = []
    for root in results_dirs:
        p = root / "experiments.csv"
        if p.exists():
            with open(p, newline="") as f:
                frames.append(pd.DataFrame(list(csv.DictReader(f))))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_ledger(runs: list[Run], ledgers: pd.DataFrame) -> pd.DataFrame:
    """experiments.csv rows + run dirs without a row (e.g. runs of another checkout); status per row."""
    by_name = {r.name: r for r in runs}
    rows = []
    for rec in ledgers.to_dict("records"):
        r = by_name.get(rec.get("run_name", ""))
        if r is None:
            status = "no results dir"
        elif not r.meta:
            status = "in progress"
        elif r.meta.get("start", "")[:16].replace("T", " ") != rec.get("date", ""):
            status = "superseded (overwritten)"
        else:
            status = "smoke" if r.smoke else "ok"
        rows.append({**rec, "status": status, "config": Path(rec.get("config") or "").stem or rec.get("config", "")})
    have = {(x.get("run_name"), x.get("date")) for x in rows}
    for r in runs:
        date = r.meta.get("start", "")[:16].replace("T", " ")
        if (r.name, date) in have:
            continue
        rows.append({"run_name": r.name, "date": date, "git_sha": r.meta.get("git_sha", ""), "config": r.config,
                     "seed": r.seed, "hypothesis": (r.cfg.get("meta") or {}).get("hypothesis", ""),
                     "best_epoch": r.meta.get("best_epoch", ""), "val_map": r.meta.get("val_map", ""),
                     "val_thr": r.meta.get("val_thr", ""), "val_auc": r.meta.get("val_auc", ""),
                     "train_min": r.meta.get("train_min", ""),
                     "status": ("smoke" if r.smoke else "ok (not in experiments.csv)") if r.complete else
                     ("smoke, in progress" if r.smoke else "in progress")})
    df = pd.DataFrame(rows)
    return df.sort_values(["date", "run_name"], kind="stable").reset_index(drop=True) if len(df) else df


def _f(x: Any, nd: int = 4) -> str:
    if x is None or x == "" or (isinstance(x, float) and np.isnan(x)):
        return "–"
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _pm(v: list[float], nd: int = 4) -> str:
    v = [x for x in v if x is not None and not np.isnan(x)]
    if not v:
        return "–"
    return f"{np.mean(v):.{nd}f} ± {np.std(v, ddof=1):.{nd}f}" if len(v) > 1 else f"{v[0]:.{nd}f}"


def md_table(header: list[str], rows: list[list[Any]]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def ledger_md(ledger: pd.DataFrame) -> str:
    if not len(ledger):
        return "_пусто_"
    rows = [[r.get("run_name"), r.get("date"), str(r.get("git_sha") or "")[:8], r.get("config"), r.get("seed"),
             _short(r.get("hypothesis", ""), 70), r.get("best_epoch"), _f(r.get("val_map")), _f(r.get("val_thr"), 2),
             _f(r.get("val_auc"), 3), _f(r.get("train_min"), 1), r.get("status")] for r in ledger.to_dict("records")]
    return md_table(["run", "date", "git sha", "config", "seed", "hypothesis (short)", "best ep", "val mAP", "val thr",
                     "val AUC", "train min", "status"], rows)


SUMMARY_KEYS = ["map", "image_auc", "cls_auc", "sensitivity", "specificity", "fp_image_rate", "map_pos"]


def summary_rows(units: dict[str, dict[int, Evaluated]], tests: dict[str, dict[int, dict | None]]) -> list[dict]:
    rows = []
    for name, ev in units.items():
        t = [x for x in tests.get(name, {}).values() if x]
        rows.append({"config": name, "n_seeds": len(ev), "seeds": list(ev),
                     "units": [e.unit.variant or "raw" for e in ev.values()],
                     **{f"val_{k}": [e.metrics[k] for e in ev.values()] for k in SUMMARY_KEYS},
                     "val_thr": [e.thr for e in ev.values()], "test_map": [x["map"] for x in t if x.get("map") is not None],
                     "n_test": len(t)})
    return rows


def summary_frame(rows: list[dict]) -> pd.DataFrame:
    """Machine-readable summary: mean / std (ddof=1) of every per-seed metric list."""
    out = []
    for r in rows:
        rec: dict[str, Any] = {"config": r["config"], "n_seeds": r["n_seeds"],
                               "seeds": " ".join(f"{s}/{u}" for s, u in zip(r["seeds"], r["units"]))}
        for k, v in r.items():
            if k in ("seeds", "units") or not isinstance(v, list):
                continue
            x = np.array([np.nan if e is None else e for e in v], dtype=float)
            rec[f"{k}_mean"] = float(np.nanmean(x)) if np.isfinite(x).any() else np.nan
            rec[f"{k}_std"] = float(np.nanstd(x, ddof=1)) if np.isfinite(x).sum() > 1 else np.nan
        out.append(rec)
    return pd.DataFrame(out)


def summary_md(rows: list[dict]) -> str:
    out = [[_label(r["config"]),
            r["n_seeds"], ", ".join(f"{s}{'' if u == 'raw' else '/' + u}" for s, u in zip(r["seeds"], r["units"])),
            _pm(r["val_map"]), _pm(r["val_thr"], 2),
            _pm(r["val_image_auc"], 3), _pm(r["val_cls_auc"], 3), _pm(r["val_sensitivity"], 3),
            _pm(r["val_specificity"], 3),
            _pm(r["val_fp_image_rate"], 3), _pm(r["val_map_pos"]),
            (_pm(r["test_map"]) + f" (n={r['n_test']})") if r["n_test"] else "–"] for r in rows]
    return md_table(["config", "n seeds", "seeds (/variant)", "val mAP", "val thr", "AUC max-box", "AUC cls", "sens",
                     "spec", "FP-img rate",
                     "mAP pos", "test mAP"], out)


def deltas_md(rows: list[dict]) -> str:
    out = [[r["label"] + (" †" if r.get("box_scale_selection") else ""), r["split"], ",".join(map(str, r["seeds"])),
            f"{r['diff']:+.4f}",
            f"[{r['lo']:+.4f}, {r['hi']:+.4f}]", _f(r["p_diff_le_0"], 3),
            "; ".join(f"s{p['seed']}: {p['diff']:+.4f} [{p['lo']:+.4f}, {p['hi']:+.4f}]" for p in r["per_seed"])]
           for r in rows]
    return md_table(["ablation (Δ = Full − ablated)", "split", "seeds", "Δ mAP (seed mean)", "95% CI (paired bootstrap)",
                     "P(Δ≤0)", "per seed Δ [95% CI]"], out)


# ----------------------------------------------------------------------------- figures

def _label(name: str) -> str:
    if "/" in name:
        c, v = name.split("/", 1)
        return f"{CONFIG_LABEL.get(c, c)} / {v}"
    return CONFIG_LABEL.get(name, name)


def unit_tag(ev: dict[int, Evaluated]) -> str:
    """Which tables a config entry uses: 'as trained' and/or the primary variant name(s)."""
    return ", ".join(sorted({e.unit.variant or "as trained" for e in ev.values()}))


def fig_map_by_config(units: dict[str, dict[int, Evaluated]], trivial: dict[str, float], path: Path) -> None:
    names = list(units)
    known = [n.split("/")[0] for n in names]
    fig, ax = plt.subplots(figsize=(max(5.5, 1.15 * len(names) + 2), 3.8))
    for i, n in enumerate(names):
        c = config_color(n.split("/")[0], known)
        vals = np.array([e.metrics["map"] for e in units[n].values()])
        seeds = list(units[n])
        hollow = "/" in n
        x = i + (np.linspace(-0.12, 0.12, len(vals)) if len(vals) > 1 else np.zeros(len(vals)))
        ax.scatter(x, vals, s=36, marker=MARKERS.get(n.split("/")[0], "o"), facecolor="none" if hollow else c,
                   edgecolor=c, linewidth=1.5, zorder=3)
        for xi, v, s in zip(x, vals, seeds):
            ax.annotate(f"s{s}", (xi, v), xytext=(5, 0), textcoords="offset points", fontsize=7, color=INK2, va="center")
        if len(vals):  # std bar only from >= 3 seeds; with 2 the points themselves are the spread
            sd = vals.std(ddof=1) if len(vals) >= 3 else None
            ax.errorbar(i + 0.32, vals.mean(), yerr=sd, fmt="_", ms=14, color=c, capsize=4, lw=2, zorder=2)
            ax.annotate(f"{vals.mean():.4f}" + (f"\n±{sd:.4f}" if sd is not None else f"\n(n={len(vals)})"),
                        (i + 0.4, vals.mean()), fontsize=7.5, color=INK, va="center")
    if BASE_CONFIG in units and units[BASE_CONFIG]:
        bm = np.mean([e.metrics["map"] for e in units[BASE_CONFIG].values()])
        ax.axhline(bm, color=FIXED_COLOR["baseline"], ls="--", lw=1.2, zorder=1)
        ax.annotate(f"B mean {bm:.4f}", (len(names) - 0.5, bm), fontsize=7.5, color=INK2, ha="right", va="bottom")
    for j, (k, v) in enumerate(trivial.items()):
        ax.axhline(v, color=INK2, ls=":", lw=1, zorder=1)
        ax.annotate(f"trivial {k} {v:.4f}", (-0.45, v), fontsize=7, color=INK2, va="bottom")
    ax.set_xticks(range(len(names)), [_label(n) if "/" in n else f"{_label(n)}\n({unit_tag(units[n])})" for n in names],
                  rotation=15 if len(names) > 5 else 0, fontsize=8)
    ax.set_xlim(-0.5, len(names) - 0.2)
    ax.set_ylabel("val RSNA mAP (VAL-selected thr)")
    ax.set_title("Val mAP by config (tick: tables used): points = seeds, bar = mean ± std, n ≥ 3 only", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_learning_curves(groups: dict[str, dict[int, Run]], path: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    known = list(groups)
    for c, seeds in groups.items():
        col = config_color(c, known)
        for k, (s, r) in enumerate(seeds.items()):
            h = r.dir / "history.csv"
            if not h.exists():
                continue
            hist = pd.read_csv(h)
            lab = CONFIG_LABEL.get(c, c) if k == 0 else None
            kw = dict(color=col, marker=MARKERS.get(c, "o"), ms=4, lw=1.5, alpha=0.9, label=lab)
            axs[0].plot(hist["epoch"], hist["val_map"], **kw)
            cls_w = float((r.cfg.get("loss") or {}).get("cls_weight", 1.0))
            det = hist["loss"] - cls_w * hist["loss_cls"] if "loss_cls" in hist else hist["loss"]
            axs[1].plot(hist["epoch"], det, **kw)
    axs[0].set(xlabel="epoch", ylabel="val mAP (best thr of epoch)", title="Validation mAP per epoch (one line per run)")
    axs[1].set(xlabel="epoch", ylabel="train loss, epoch mean (log)", yscale="log",
               title="Train detection loss (hm + w·wh + w·off; cls BCE excluded)")
    for a in axs:
        if a.get_legend_handles_labels()[0]:
            a.legend(fontsize=8)
    if not groups:
        axs[0].text(0.5, 0.5, "no finished runs yet", transform=axs[0].transAxes, ha="center", color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_deltas(rows: list[dict], path: Path) -> None:
    rows = [r for r in rows if np.isfinite(r["diff"])]
    fig, ax = plt.subplots(figsize=(8.5, 0.62 * max(len(rows), 1) + 1.4))
    for i, r in enumerate(rows):
        y = len(rows) - 1 - i
        col = SLOTS[0] if r["split"] == "val" else SLOTS[1]
        ax.plot([r["lo"], r["hi"]], [y, y], color=col, lw=2.5, solid_capstyle="round", zorder=2)
        ax.scatter([r["diff"]], [y], marker="D", s=44, color=col, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        for k, p in enumerate(r["per_seed"]):
            yy = y - 0.22 - 0.07 * k
            ax.plot([p["lo"], p["hi"]], [yy, yy], color=INK2, lw=0.8, alpha=0.7)
            ax.scatter([p["diff"]], [yy], s=12, facecolor="none", edgecolor=INK2, lw=0.8, zorder=3)
        ax.annotate(f"{r['diff']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]  seeds {','.join(map(str, r['seeds']))}",
                    (r["hi"], y), xytext=(6, 0), textcoords="offset points", va="center", fontsize=7.5)
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(range(len(rows)), [f"{r['label']}{' †' if r.get('box_scale_selection') else ''}  [{r['split']}]"
                                     for r in rows][::-1], fontsize=8)
    lo = min([r["lo"] for r in rows] + [p["lo"] for r in rows for p in r["per_seed"]] + [0])
    hi = max([r["hi"] for r in rows] + [p["hi"] for r in rows for p in r["per_seed"]] + [0])
    ax.set_xlim(lo - 0.1 * (hi - lo + 1e-3), hi + 0.6 * (hi - lo + 1e-3))
    ax.set_ylim(-0.8, len(rows) - 0.4)
    ax.set_xlabel("Δ mAP = Full − ablated  (> 0: the removed component helps)")
    ax.set_title("Ablations vs Full: diamond = seed-mean Δ, 95% paired-bootstrap CI over images only (seed variance\n"
                 "not included; small markers = per seed). † = val Δ includes box_scale selection on the same images",
                 fontsize=8.5)
    if not rows:
        ax.text(0.5, 0.5, "no seed-matched pairs yet", transform=ax.transAxes, ha="center", color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_threshold_curves(units: dict[str, dict[int, Evaluated]], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    known = [n.split("/")[0] for n in units]
    var_ls = iter(["--", ":", "-.", (0, (5, 1, 1, 1))] * 4)
    for n, ev in units.items():
        if not ev:
            continue
        col = config_color(n.split("/")[0], known)
        ls = next(var_ls) if "/" in n else "-"
        for e in ev.values():
            ax.plot(e.sweep["thr"], e.sweep["map"], color=col, lw=0.8, alpha=0.35, ls=ls)
        mean = pd.concat([e.sweep.set_index("thr")["map"] for e in ev.values()], axis=1).mean(axis=1)
        ax.plot(mean.index, mean.values, color=col, lw=2, ls=ls, label=f"{_label(n)} (n={len(ev)})")
        b = mean.idxmax()
        ax.scatter([b], [mean[b]], color=col, s=30, zorder=3, edgecolor=SURFACE, linewidth=1.5)
    ax.set(xlabel="score threshold (keep score ≥ thr)", ylabel="val RSNA mAP",
           title="Val mAP vs score threshold (thin = seeds, thick = seed mean, dot = argmax)")
    if ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ----------------------------------------------------------------------------- MLflow

def mlflow_runs(uri: str) -> pd.DataFrame | None:
    """Runs in the MLflow store (None if the sqlite file is absent or mlflow fails)."""
    if uri.startswith("sqlite:///") and not Path(uri[len("sqlite:///"):]).exists():
        return None
    try:
        import os

        os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
        import mlflow

        mlflow.set_tracking_uri(uri)
        df = mlflow.search_runs(search_all_experiments=True)
    except Exception as e:  # noqa: BLE001 — tracking store is optional
        print(f"[report] MLflow unavailable: {e}")
        return None
    if not len(df):
        return df
    if "start_time" in df:  # stored in UTC; show local time like the ledger
        df["start_time"] = pd.to_datetime(df["start_time"], utc=True).dt.tz_convert(datetime.now().astimezone().tzinfo)
    cols = {"tags.mlflow.runName": "run_name", "status": "status", "run_id": "run_id", "start_time": "start",
            "metrics.best_val_map": "best_val_map", "tags.seed": "seed", "tags.git_sha": "git_sha"}
    return df[[c for c in cols if c in df.columns]].rename(columns=cols)


def mlflow_md(df: pd.DataFrame | None, runs: list[Run]) -> str:
    if df is None:
        return "_MLflow store not found or unreadable (optional)._"
    if not len(df):
        return "_MLflow store has no runs._"
    meta_ids = {r.meta.get("mlflow_run_id") for r in runs if r.meta}
    rows = [[r.get("run_name"), r.get("status"), str(r.get("run_id"))[:8], str(r.get("start"))[:16],
             _f(r.get("best_val_map")), "yes" if r.get("run_id") in meta_ids else "no"] for r in df.to_dict("records")]
    return md_table(["run", "status", "mlflow id", "start", "best val mAP", "matches a results dir"], rows)


# ----------------------------------------------------------------------------- main

def trivial_refs(results_dirs: Iterable[Path]) -> dict[str, float]:
    out = {}
    for root in results_dirs:
        for v in TRIVIAL:
            p = root / "baseline_trivial" / v / "val_metrics.json"
            if p.exists() and v not in out:
                out[v] = float(json.loads(p.read_text())["map"])
    return out


def build(results_dirs: list[Path], primary_variant: str | None = None, with_test: bool = False, n_boot: int = 2000,
          out_md: Path | None = None, fig_dir: Path | None = None, mlflow_uri: str = paths.MLFLOW_URI) -> dict[str, Any]:
    out_md = out_md or paths.RESULTS / "experiments.md"
    fig_dir = fig_dir or paths.FIGURES
    fig_dir.mkdir(parents=True, exist_ok=True)
    runs, notes = discover(results_dirs)
    groups = group_by_config(runs)
    missing = missing_report(runs, groups, primary_variant)
    meta = load_meta()
    target = meta.set_index("patientId")["target"]
    val_ids = meta.loc[meta["split"] == "val", "patientId"].tolist()
    gt = load_gt(paths.BOXES, val_ids)

    def ev_or_none(u: Unit) -> Evaluated | None:
        ids = pd.read_csv(u.dir / "val_image_scores.csv", dtype={"patientId": str}, usecols=["patientId"])["patientId"]
        if not set(ids) <= set(val_ids):
            notes.append(f"{u.key}: val tables contain non-val ids (other split file?) — skipped")
            return None
        return evaluate_unit(u, gt, target)

    primary: dict[str, dict[int, Evaluated]] = {}
    as_trained: dict[str, dict[int, Evaluated]] = {}  # the run's own tables (box_scale 1.0): cells of the 2x2
    variants: dict[str, dict[int, Evaluated]] = {}
    tests: dict[str, dict[int, dict | None]] = {}
    for c, seeds in groups.items():
        for s, r in seeds.items():
            pu = primary_unit(r, primary_variant)
            e = ev_or_none(pu)
            if e:
                primary.setdefault(c, {})[s] = e
                tests.setdefault(c, {})[s] = load_test_metrics(pu)
            ae = e if e and not pu.variant else ev_or_none(Unit(r, "", r.dir))
            if ae:
                as_trained.setdefault(c, {})[s] = ae
            for vu in posthoc_units(r, primary_variant):
                ve = ev_or_none(vu)
                if ve:
                    variants.setdefault(f"{c}/{vu.variant}", {})[s] = ve
                    tests.setdefault(f"{c}/{vu.variant}", {})[s] = load_test_metrics(vu)
    all_units = {**primary, **{k: v for k, v in sorted(variants.items())}}

    # ablations vs Full: other configs (seed-matched) and Full's own post-hoc variants (same checkpoint)
    deltas: list[dict] = []
    if REF_CONFIG in primary:
        others = {c: primary[c] for c in primary if c != REF_CONFIG}
        others = dict(sorted(others.items(), key=lambda kv: ["b_cls", "b_aug", "baseline"].index(kv[0])
                             if kv[0] in ("b_cls", "b_aug", "baseline") else 9))
        others.update({k.split("/", 1)[1]: v for k, v in variants.items() if k.startswith(REF_CONFIG + "/")})
        deltas = ablation_rows(primary[REF_CONFIG], others, n_boot)
    factorial = factorial_rows(as_trained, n_boot)
    if with_test:
        deltas += final_test_deltas(groups, primary_variant, n_boot, notes)
    i3_lines, gating_lines = crossfit_lines(groups), gating_epoch_lines(groups)

    trivial = trivial_refs(results_dirs)
    style()
    figs = {"val_map": fig_dir / "hw2_val_map_by_config.png", "curves": fig_dir / "hw2_learning_curves.png",
            "deltas": fig_dir / "hw2_ablation_deltas.png", "thr": fig_dir / "hw2_threshold_curves.png"}
    fig_map_by_config(all_units, trivial, figs["val_map"])
    fig_learning_curves(groups, figs["curves"])
    fig_deltas(deltas, figs["deltas"])
    fig_threshold_curves(all_units, figs["thr"])

    ledger = build_ledger(runs, read_ledgers(results_dirs))
    srows = summary_rows(all_units, tests)
    ml = mlflow_runs(mlflow_uri)
    rel = lambda p: p.relative_to(paths.ROOT) if p.is_relative_to(paths.ROOT) else p
    md = [f"# Журнал экспериментов",
          f"_Сгенерировано `python -m rsna.report` {datetime.now():%Y-%m-%d %H:%M}; источники: "
          f"{', '.join(str(rel(d)) for d in results_dirs)}; primary variant: {primary_variant or '— (как обучено)'}._", "",
          "Все val-числа посчитаны при пороге score, выбранном на VAL (argmax свипа), поэтому смещены вверх. У единиц "
          "с box_scale, подобранным на VAL (вариант tuned), есть ещё один выбор на тех же снимках, так что их "
          "val-смещение больше, чем у B (B взят как обучен, box_scale 1.0). Строки, где tuned сравнивается с "
          "неподобранной единицей, помечены †: их val Δ включает выигрыш от подбора (у «Full − box_scale» он ≥ 0 по "
          "построению). Несмещённые проверки I3: cross-fit оценка ниже и test-строки. Test в решениях не участвует.", "",
          "## Чего не хватает", "", *(f"- {m}" for m in missing + notes), *(["- ничего"] if not missing + notes else []), "",
          "## Журнал запусков (ledger)", "", ledger_md(ledger), "",
          "## Сводка по конфигам (среднее ± std по сидам, ddof=1)", "", summary_md(srows), "",
          "Тривиальные ориентиры (val): " + (", ".join(f"{k} {v:.4f}" for k, v in trivial.items()) or "–"), "",
          "## Абляции: парные разности против Full", "",
          "Δ = mAP(Full) − mAP(абляция) на одних и тех же снимках; для конфигов пары по совпадающему seed, для post-hoc "
          "вариантов это тот же чекпойнт. Seed-mean Δ: CI учитывает только шум выборки снимков (общий ресэмпл для всех "
          "сидов), разброс между сидами виден по per-seed значениям.", "",
          deltas_md(deltas) if deltas else "_нет пар (нужны прогоны Full и хотя бы одна абляция с тем же seed)_", "",
          "† val Δ включает подбор box_scale на тех же снимках только у Full (смещение в пользу Full).", "",
          "### I3 (box_scale): cross-fit оценка на val", "",
          "Масштаб и порог выбираются на одной случайной половине val, выигрыш против box_scale 1.0 меряется на другой "
          "(2 фолда, среднее); в отличие от «Full − box_scale» эта оценка не завышена выбором.", "",
          *(i3_lines or ["_нет posthoc/box_scale.json_"]), "",
          "### I1: выбор эпохи и абляция «Full − gating»", "",
          "Лучшая эпоха cls-моделей выбрана по val mAP с гейтингом; no_gating переоценивает тот же чекпойнт. Если бы "
          "эпоху выбирали по скорингу heatmap, val mAP без гейтинга был бы выше на «зазор», т.е. Δ(Full − gating) на val "
          "завышена на эту величину (сам зазор тоже смещён вверх выбором). Основное свидетельство для I1 — обученный "
          "контраст «Full − cls head & gating (vs B+aug)» и 2×2.", "",
          *(gating_lines or ["_нет history.csv с val_map_heatmap (прогоны до этого изменения)_"]), ""]
    if factorial:
        md += ["## 2×2: главные эффекты и взаимодействие (val)", "",
               md_table(["effect", "seeds", "estimate", "95% CI", "P(≤0)"],
                        [[f["effect"], ",".join(map(str, f["seeds"])), f"{f['diff']:+.4f}",
                          f"[{f['lo']:+.4f}, {f['hi']:+.4f}]", _f(f["p_diff_le_0"], 3)] for f in factorial]), "",
               "Клетки 2×2 — таблицы прогонов как обучены (box_scale 1.0 во всех четырёх, порог из их val-свипа): "
               "post-hoc I3 сюда не входит. Единицы по клеткам: " + "; ".join(
                   f"{CONFIG_LABEL.get(c, c)}: {unit_tag(as_trained[c])}" for c in CONFIG_ORDER if c in as_trained), ""]
    md += ["## MLflow", "", mlflow_md(ml, runs), "", "## Рисунки", "",
           *(f"- `{rel(p)}`" for p in figs.values()), ""]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md))
    summary_frame(srows).to_csv(out_md.with_name(out_md.stem + "_summary.csv"), index=False, float_format="%.5f")
    pd.DataFrame([{k: v for k, v in r.items() if k != "per_seed"} for r in deltas]).to_csv(
        out_md.with_name(out_md.stem + "_deltas.csv"), index=False, float_format="%.5f")
    print("\n".join(md))
    print(f"-> {out_md}\n-> " + "\n-> ".join(map(str, figs.values())))
    return {"runs": runs, "groups": groups, "missing": missing, "summary": srows, "deltas": deltas,
            "factorial": factorial, "figures": figs}


def crossfit_lines(groups: dict[str, dict[int, Run]]) -> list[str]:
    """Cross-fitted box_scale gain per run from posthoc/box_scale.json (rsna.posthoc tune)."""
    out = []
    for c, seeds in groups.items():
        for s, r in seeds.items():
            p = r.dir / "posthoc" / "box_scale.json"
            if not p.exists():
                continue
            t = json.loads(p.read_text())
            cf = (f"cross-fit {t['crossfit_gain']:+.4f} (масштабы по фолдам "
                  f"{', '.join(str(f['box_scale']) for f in t['crossfit_folds'])})" if "crossfit_gain" in t
                  else "cross-fit не посчитан (старый tune)")
            out.append(f"- {CONFIG_LABEL.get(c, c)} s{s}: выбран ×{t['box_scale']} (val {t['val_map']:.4f} против "
                       f"{t['val_map_box_scale_1']:.4f} при ×1.0, выигрыш ≥ 0 по построению); {cf}"
                       + ("; ⚠ выбор на краю сетки" if t.get("at_grid_edge") else ""))
    return out


def gating_epoch_lines(groups: dict[str, dict[int, Run]]) -> list[str]:
    """Epoch-selection gap of the no_gating ablation: best-over-epochs no-gating val mAP − its value at the best epoch."""
    out = []
    for c, seeds in groups.items():
        for s, r in seeds.items():
            h = r.dir / "history.csv"
            if not h.exists():
                continue
            hist = pd.read_csv(h)
            if "val_map_heatmap" not in hist or hist["val_map_heatmap"].isna().all():
                continue
            at = hist.loc[hist["epoch"] == r.meta.get("best_epoch"), "val_map_heatmap"]
            if not len(at):
                continue
            k = int(hist["val_map_heatmap"].idxmax())
            out.append(f"- {CONFIG_LABEL.get(c, c)} s{s}: без гейтинга на лучшей эпохе ({r.meta.get('best_epoch')}) "
                       f"{at.iloc[0]:.4f}, максимум по эпохам {hist.loc[k, 'val_map_heatmap']:.4f} (эпоха "
                       f"{int(hist.loc[k, 'epoch'])}) → зазор {hist.loc[k, 'val_map_heatmap'] - at.iloc[0]:+.4f}")
    return out


def final_test_deltas(groups: dict[str, dict[int, Run]], primary_variant: str | None, n_boot: int,
                      notes: list[str]) -> list[dict]:
    """TEST paired Δ of Full against every other config and against its post-hoc ablations (same checkpoint).

    Reported once at the end and never used for selection (the pre-registered contrast is Full − B); every unit
    uses its VAL threshold / box_scale and needs fresh test tables (rsna.evaluate --split test [--variant])."""
    if REF_CONFIG not in groups:
        return []
    meta = load_meta()
    target = meta.set_index("patientId")["target"]
    test_ids = meta.loc[meta["split"] == "test", "patientId"].tolist()
    gt = load_gt(paths.BOXES, test_ids)

    def ev_test(u: Unit) -> Evaluated | None:
        if has_tables(u.dir, "test") and load_test_metrics(u) is not None:
            return evaluate_unit(u, gt, target, "test")
        notes.append(f"{u.key}: no fresh test tables (run rsna.evaluate --split test"
                     + (f" --variant {u.variant})" if u.dir != u.run.dir else ")"))
        return None

    ev: dict[str, dict[int, Evaluated]] = {}
    for c, seeds in groups.items():
        for s, r in seeds.items():
            e = ev_test(primary_unit(r, primary_variant))
            if e:
                ev.setdefault(c, {})[s] = e
            if c == REF_CONFIG:
                for vu in posthoc_units(r, primary_variant):
                    ve = ev_test(vu)
                    if ve:
                        ev.setdefault(vu.variant, {})[s] = ve
    if REF_CONFIG not in ev:
        return []
    order = [BASE_CONFIG, "b_aug", "b_cls"]
    others = {k: v for k, v in sorted(ev.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 9)
              if k != REF_CONFIG}
    return ablation_rows(ev[REF_CONFIG], others, n_boot, split="test")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, nargs="+", default=[paths.RESULTS],
                    help="results dirs (or single run dirs) to scan; the first occurrence of a run name wins")
    ap.add_argument("--primary-variant", help="post-hoc variant used as each run's main result where it exists")
    ap.add_argument("--with-test", action="store_true", help="also paired TEST Δ Full − B (reads test labels)")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out-md", type=Path, default=paths.RESULTS / "experiments.md")
    ap.add_argument("--fig-dir", type=Path, default=paths.FIGURES)
    ap.add_argument("--mlflow-uri", default=paths.MLFLOW_URI)
    a = ap.parse_args(argv)
    build([p.resolve() for p in a.results], a.primary_variant, a.with_test, a.n_boot, a.out_md, a.fig_dir, a.mlflow_uri)


if __name__ == "__main__":
    main()
