### b_cls_s0:no_boxscale — test

mAP **0.1926** [0.1504, 0.2377] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.20; images 4004, scored 1153

| metric | value |
|---|---|
| image_roc_auc | 0.8764 |
| image_pr_auc | 0.7103 |
| sensitivity | 0.5811 |
| specificity | 0.9185 |
| matched_iou | 0.6337 |
| mAP on positives only | 0.2468 |
| FP-image rate on negatives | 0.0815 (253/3104) |
| loss: FP on negatives | 0.2194 |
| loss: missed positives (no box) | 0.3270 |
| loss: localization on positives | 0.2610 |
| oracle gating @run thr | 0.2468 |
| oracle gating @best thr (0.05) | 0.2993 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2235 | [0.167, 0.279] | 0.2924 | 0.190 | 0.682 |
| view | PA | 2177 | 202 | 0.0751 | [0.046, 0.105] | 0.0893 | 0.019 | 0.233 |
| sex | F | 1729 | 374 | 0.1932 | [0.147, 0.242] | 0.2485 | 0.079 | 0.618 |
| sex | M | 2275 | 526 | 0.1922 | [0.127, 0.262] | 0.2455 | 0.083 | 0.555 |
| age_bucket | <20 | 246 | 71 | 0.1956 | [0.141, 0.261] | 0.2369 | 0.086 | 0.634 |
| age_bucket | 20-40 | 949 | 249 | 0.2113 | [0.150, 0.259] | 0.2775 | 0.111 | 0.651 |
| age_bucket | 40-60 | 1767 | 363 | 0.2140 | [0.120, 0.313] | 0.2736 | 0.072 | 0.584 |
| age_bucket | 60+ | 1041 | 217 | 0.1336 | [0.093, 0.175] | 0.1699 | 0.072 | 0.479 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2468 | [0.197, 0.296] | 0.2468 | – | 0.581 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.141 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.082 | – |
| n_boxes | 1 | 390 | 390 | 0.1145 | [0.090, 0.138] | 0.1145 | – | 0.377 |
| n_boxes | 2 | 492 | 492 | 0.3571 | [0.281, 0.429] | 0.3571 | – | 0.738 |
| n_boxes | 3+ | 18 | 18 | 0.0971 | [0.037, 0.174] | 0.0971 | – | 0.722 |
