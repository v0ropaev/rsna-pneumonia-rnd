### full_s0 — test

mAP **0.2170** [0.1733, 0.2629] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4004, scored 1193

| metric | value |
|---|---|
| image_roc_auc | 0.8868 |
| image_pr_auc | 0.7290 |
| sensitivity | 0.6411 |
| specificity | 0.9056 |
| matched_iou | 0.6427 |
| mAP on positives only | 0.2877 |
| FP-image rate on negatives | 0.0944 (293/3104) |
| loss: FP on negatives | 0.2456 |
| loss: missed positives (no box) | 0.2707 |
| loss: localization on positives | 0.2666 |
| oracle gating @run thr | 0.2877 |
| oracle gating @best thr (0.05) | 0.3118 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2439 | [0.188, 0.304] | 0.3236 | 0.202 | 0.721 |
| view | PA | 2177 | 202 | 0.1238 | [0.090, 0.160] | 0.1636 | 0.033 | 0.366 |
| sex | F | 1729 | 374 | 0.2092 | [0.163, 0.257] | 0.2797 | 0.093 | 0.660 |
| sex | M | 2275 | 526 | 0.2227 | [0.153, 0.292] | 0.2934 | 0.095 | 0.627 |
| age_bucket | <20 | 246 | 71 | 0.2288 | [0.169, 0.310] | 0.2739 | 0.080 | 0.662 |
| age_bucket | 20-40 | 949 | 249 | 0.2411 | [0.183, 0.284] | 0.3157 | 0.110 | 0.703 |
| age_bucket | 40-60 | 1767 | 363 | 0.2402 | [0.147, 0.343] | 0.3203 | 0.086 | 0.645 |
| age_bucket | 60+ | 1041 | 217 | 0.1496 | [0.106, 0.193] | 0.2054 | 0.098 | 0.558 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2877 | [0.235, 0.340] | 0.2877 | – | 0.641 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.165 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.094 | – |
| n_boxes | 1 | 390 | 390 | 0.1734 | [0.143, 0.203] | 0.1734 | – | 0.503 |
| n_boxes | 2 | 492 | 492 | 0.3841 | [0.303, 0.467] | 0.3841 | – | 0.748 |
| n_boxes | 3+ | 18 | 18 | 0.1271 | [0.071, 0.191] | 0.1271 | – | 0.722 |
