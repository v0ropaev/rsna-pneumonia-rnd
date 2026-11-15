### baseline_s2 — test

mAP **0.2034** [0.1640, 0.2456] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4004, scored 1338

| metric | value |
|---|---|
| image_roc_auc | 0.8743 |
| image_pr_auc | 0.6902 |
| sensitivity | 0.6822 |
| specificity | 0.8589 |
| matched_iou | 0.6410 |
| mAP on positives only | 0.3024 |
| FP-image rate on negatives | 0.1411 (438/3104) |
| loss: FP on negatives | 0.3274 |
| loss: missed positives (no box) | 0.2138 |
| loss: localization on positives | 0.2555 |
| oracle gating @run thr | 0.3024 |
| oracle gating @best thr (0.15) | 0.3686 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2296 | [0.177, 0.287] | 0.3270 | 0.262 | 0.746 |
| view | PA | 2177 | 202 | 0.1276 | [0.095, 0.161] | 0.2173 | 0.072 | 0.460 |
| sex | F | 1729 | 374 | 0.1971 | [0.154, 0.242] | 0.2983 | 0.142 | 0.709 |
| sex | M | 2275 | 526 | 0.2080 | [0.145, 0.273] | 0.3053 | 0.141 | 0.663 |
| age_bucket | <20 | 246 | 71 | 0.1976 | [0.148, 0.255] | 0.2672 | 0.143 | 0.648 |
| age_bucket | 20-40 | 949 | 249 | 0.2305 | [0.173, 0.275] | 0.3352 | 0.161 | 0.747 |
| age_bucket | 40-60 | 1767 | 363 | 0.2187 | [0.137, 0.311] | 0.3301 | 0.132 | 0.700 |
| age_bucket | 60+ | 1041 | 217 | 0.1503 | [0.105, 0.200] | 0.2299 | 0.140 | 0.590 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.3024 | [0.251, 0.352] | 0.3024 | – | 0.682 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.244 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.004 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.141 | – |
| n_boxes | 1 | 390 | 390 | 0.2168 | [0.181, 0.249] | 0.2168 | – | 0.541 |
| n_boxes | 2 | 492 | 492 | 0.3778 | [0.294, 0.454] | 0.3778 | – | 0.791 |
| n_boxes | 3+ | 18 | 18 | 0.0948 | [0.043, 0.160] | 0.0948 | – | 0.778 |
