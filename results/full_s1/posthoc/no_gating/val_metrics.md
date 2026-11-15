### full_s1:no_gating — val

mAP **0.2115** [0.1814, 0.2405] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4002, scored 1135

| metric | value |
|---|---|
| image_roc_auc | 0.8937 |
| image_pr_auc | 0.7176 |
| sensitivity | 0.5633 |
| specificity | 0.9242 |
| matched_iou | 0.6452 |
| mAP on positives only | 0.2667 |
| FP-image rate on negatives | 0.0758 (235/3102) |
| loss: FP on negatives | 0.2070 |
| loss: missed positives (no box) | 0.3463 |
| loss: localization on positives | 0.2352 |
| oracle gating @run thr | 0.2667 |
| oracle gating @best thr (0.15) | 0.3719 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2360 | [0.201, 0.270] | 0.2958 | 0.157 | 0.623 |
| view | PA | 2176 | 202 | 0.1292 | [0.099, 0.161] | 0.1663 | 0.029 | 0.356 |
| sex | F | 1730 | 376 | 0.2158 | [0.163, 0.260] | 0.2772 | 0.079 | 0.553 |
| sex | M | 2272 | 524 | 0.2083 | [0.175, 0.247] | 0.2592 | 0.073 | 0.571 |
| age_bucket | <20 | 337 | 125 | 0.2915 | [0.208, 0.347] | 0.3568 | 0.132 | 0.784 |
| age_bucket | 20-40 | 1087 | 265 | 0.2178 | [0.164, 0.267] | 0.2671 | 0.073 | 0.532 |
| age_bucket | 40-60 | 1598 | 334 | 0.2269 | [0.177, 0.280] | 0.2894 | 0.073 | 0.593 |
| age_bucket | 60+ | 980 | 176 | 0.1213 | [0.082, 0.154] | 0.1592 | 0.068 | 0.398 |
| cls | Lung Opacity | 900 | 900 | 0.2667 | [0.232, 0.299] | 0.2667 | – | 0.563 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.132 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.076 | – |
| n_boxes | 1 | 392 | 392 | 0.1958 | [0.157, 0.236] | 0.1958 | – | 0.418 |
| n_boxes | 2 | 490 | 490 | 0.3282 | [0.274, 0.374] | 0.3282 | – | 0.671 |
| n_boxes | 3+ | 18 | 18 | 0.1395 | [0.071, 0.219] | 0.1395 | – | 0.778 |
