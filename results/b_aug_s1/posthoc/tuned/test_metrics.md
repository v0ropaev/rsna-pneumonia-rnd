### b_aug_s1:tuned — test

mAP **0.2149** [0.1671, 0.2628] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4004, scored 1146

| metric | value |
|---|---|
| image_roc_auc | 0.8811 |
| image_pr_auc | 0.7137 |
| sensitivity | 0.5767 |
| specificity | 0.9207 |
| matched_iou | 0.6515 |
| mAP on positives only | 0.2737 |
| FP-image rate on negatives | 0.0793 (246/3104) |
| loss: FP on negatives | 0.2147 |
| loss: missed positives (no box) | 0.3325 |
| loss: localization on positives | 0.2379 |
| oracle gating @run thr | 0.2737 |
| oracle gating @best thr (0.15) | 0.3887 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2425 | [0.181, 0.307] | 0.3050 | 0.159 | 0.649 |
| view | PA | 2177 | 202 | 0.1248 | [0.087, 0.162] | 0.1655 | 0.033 | 0.327 |
| sex | F | 1729 | 374 | 0.2017 | [0.155, 0.254] | 0.2621 | 0.083 | 0.604 |
| sex | M | 2275 | 526 | 0.2247 | [0.145, 0.303] | 0.2819 | 0.077 | 0.557 |
| age_bucket | <20 | 246 | 71 | 0.2274 | [0.168, 0.290] | 0.2691 | 0.074 | 0.634 |
| age_bucket | 20-40 | 949 | 249 | 0.2462 | [0.171, 0.305] | 0.3134 | 0.097 | 0.651 |
| age_bucket | 40-60 | 1767 | 363 | 0.2309 | [0.139, 0.334] | 0.2932 | 0.070 | 0.567 |
| age_bucket | 60+ | 1041 | 217 | 0.1505 | [0.103, 0.201] | 0.1969 | 0.081 | 0.488 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2737 | [0.217, 0.327] | 0.2737 | – | 0.577 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.138 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.079 | – |
| n_boxes | 1 | 390 | 390 | 0.1787 | [0.143, 0.208] | 0.1787 | – | 0.408 |
| n_boxes | 2 | 492 | 492 | 0.3566 | [0.263, 0.436] | 0.3566 | – | 0.707 |
| n_boxes | 3+ | 18 | 18 | 0.0666 | [0.023, 0.125] | 0.0666 | – | 0.667 |
