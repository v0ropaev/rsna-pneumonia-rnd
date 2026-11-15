### b_aug_s1 — test

mAP **0.2156** [0.1685, 0.2642] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4004, scored 1146

| metric | value |
|---|---|
| image_roc_auc | 0.8811 |
| image_pr_auc | 0.7137 |
| sensitivity | 0.5767 |
| specificity | 0.9207 |
| matched_iou | 0.6546 |
| mAP on positives only | 0.2745 |
| FP-image rate on negatives | 0.0793 (246/3104) |
| loss: FP on negatives | 0.2147 |
| loss: missed positives (no box) | 0.3325 |
| loss: localization on positives | 0.2373 |
| oracle gating @run thr | 0.2745 |
| oracle gating @best thr (0.15) | 0.3922 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2422 | [0.181, 0.308] | 0.3046 | 0.159 | 0.649 |
| view | PA | 2177 | 202 | 0.1286 | [0.091, 0.167] | 0.1706 | 0.033 | 0.327 |
| sex | F | 1729 | 374 | 0.2019 | [0.156, 0.254] | 0.2623 | 0.083 | 0.604 |
| sex | M | 2275 | 526 | 0.2257 | [0.147, 0.304] | 0.2832 | 0.077 | 0.557 |
| age_bucket | <20 | 246 | 71 | 0.2215 | [0.164, 0.285] | 0.2620 | 0.074 | 0.634 |
| age_bucket | 20-40 | 949 | 249 | 0.2460 | [0.171, 0.303] | 0.3131 | 0.097 | 0.651 |
| age_bucket | 40-60 | 1767 | 363 | 0.2346 | [0.142, 0.339] | 0.2980 | 0.070 | 0.567 |
| age_bucket | 60+ | 1041 | 217 | 0.1491 | [0.103, 0.197] | 0.1951 | 0.081 | 0.488 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2745 | [0.218, 0.328] | 0.2745 | – | 0.577 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.138 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.079 | – |
| n_boxes | 1 | 390 | 390 | 0.1777 | [0.142, 0.208] | 0.1777 | – | 0.408 |
| n_boxes | 2 | 492 | 492 | 0.3588 | [0.267, 0.440] | 0.3588 | – | 0.707 |
| n_boxes | 3+ | 18 | 18 | 0.0694 | [0.025, 0.130] | 0.0694 | – | 0.667 |
