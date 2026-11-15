### b_cls_s0:tuned — val

mAP **0.1961** [0.1671, 0.2241] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.20; images 4002, scored 1150

| metric | value |
|---|---|
| image_roc_auc | 0.8836 |
| image_pr_auc | 0.7003 |
| sensitivity | 0.5811 |
| specificity | 0.9194 |
| matched_iou | 0.6358 |
| mAP on positives only | 0.2505 |
| FP-image rate on negatives | 0.0806 (250/3102) |
| loss: FP on negatives | 0.2174 |
| loss: missed positives (no box) | 0.3278 |
| loss: localization on positives | 0.2587 |
| oracle gating @run thr | 0.2505 |
| oracle gating @best thr (0.05) | 0.2966 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2222 | [0.192, 0.252] | 0.2945 | 0.201 | 0.688 |
| view | PA | 2176 | 202 | 0.0886 | [0.055, 0.119] | 0.0987 | 0.012 | 0.213 |
| sex | F | 1730 | 376 | 0.2017 | [0.150, 0.246] | 0.2617 | 0.083 | 0.588 |
| sex | M | 2272 | 524 | 0.1919 | [0.159, 0.225] | 0.2425 | 0.079 | 0.576 |
| age_bucket | <20 | 337 | 125 | 0.2822 | [0.205, 0.337] | 0.3432 | 0.127 | 0.768 |
| age_bucket | 20-40 | 1087 | 265 | 0.1862 | [0.140, 0.230] | 0.2438 | 0.100 | 0.581 |
| age_bucket | 40-60 | 1598 | 334 | 0.2196 | [0.169, 0.265] | 0.2781 | 0.070 | 0.590 |
| age_bucket | 60+ | 980 | 176 | 0.1100 | [0.067, 0.141] | 0.1425 | 0.065 | 0.432 |
| cls | Lung Opacity | 900 | 900 | 0.2505 | [0.217, 0.283] | 0.2505 | – | 0.581 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.140 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.081 | – |
| n_boxes | 1 | 392 | 392 | 0.1235 | [0.098, 0.151] | 0.1235 | – | 0.390 |
| n_boxes | 2 | 490 | 490 | 0.3576 | [0.309, 0.401] | 0.3576 | – | 0.735 |
| n_boxes | 3+ | 18 | 18 | 0.1041 | [0.029, 0.181] | 0.1041 | – | 0.556 |
