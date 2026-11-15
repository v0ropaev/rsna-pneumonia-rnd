### full_s0:no_gating — test

mAP **0.2125** [0.1727, 0.2551] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4004, scored 1354

| metric | value |
|---|---|
| image_roc_auc | 0.8868 |
| image_pr_auc | 0.7290 |
| sensitivity | 0.7067 |
| specificity | 0.8537 |
| matched_iou | 0.6416 |
| mAP on positives only | 0.3197 |
| FP-image rate on negatives | 0.1463 (454/3104) |
| loss: FP on negatives | 0.3353 |
| loss: missed positives (no box) | 0.1950 |
| loss: localization on positives | 0.2572 |
| oracle gating @run thr | 0.3197 |
| oracle gating @best thr (0.15) | 0.3835 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2420 | [0.188, 0.298] | 0.3526 | 0.283 | 0.782 |
| view | PA | 2177 | 202 | 0.1236 | [0.091, 0.160] | 0.2063 | 0.068 | 0.446 |
| sex | F | 1729 | 374 | 0.2045 | [0.162, 0.251] | 0.3068 | 0.138 | 0.719 |
| sex | M | 2275 | 526 | 0.2182 | [0.157, 0.282] | 0.3289 | 0.153 | 0.698 |
| age_bucket | <20 | 246 | 71 | 0.2270 | [0.175, 0.287] | 0.3102 | 0.149 | 0.704 |
| age_bucket | 20-40 | 949 | 249 | 0.2400 | [0.181, 0.282] | 0.3479 | 0.160 | 0.763 |
| age_bucket | 40-60 | 1767 | 363 | 0.2260 | [0.144, 0.320] | 0.3468 | 0.138 | 0.702 |
| age_bucket | 60+ | 1041 | 217 | 0.1570 | [0.117, 0.200] | 0.2453 | 0.148 | 0.650 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.3197 | [0.270, 0.369] | 0.3197 | – | 0.707 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.252 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.005 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.146 | – |
| n_boxes | 1 | 390 | 390 | 0.2433 | [0.205, 0.277] | 0.2433 | – | 0.579 |
| n_boxes | 2 | 492 | 492 | 0.3888 | [0.306, 0.469] | 0.3888 | – | 0.805 |
| n_boxes | 3+ | 18 | 18 | 0.0892 | [0.050, 0.130] | 0.0892 | – | 0.778 |
