### hw3_frac50_s0:tuned — val

mAP **0.1888** [0.1602, 0.2169] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4002, scored 1083

| metric | value |
|---|---|
| image_roc_auc | 0.8843 |
| image_pr_auc | 0.7040 |
| sensitivity | 0.5511 |
| specificity | 0.9410 |
| matched_iou | 0.6246 |
| mAP on positives only | 0.2272 |
| FP-image rate on negatives | 0.0590 (183/3102) |
| loss: FP on negatives | 0.1690 |
| loss: missed positives (no box) | 0.3730 |
| loss: localization on positives | 0.2691 |
| oracle gating @run thr | 0.2272 |
| oracle gating @best thr (0.05) | 0.2901 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2190 | [0.184, 0.250] | 0.2611 | 0.119 | 0.626 |
| view | PA | 2176 | 202 | 0.0889 | [0.060, 0.112] | 0.1104 | 0.025 | 0.292 |
| sex | F | 1730 | 376 | 0.1916 | [0.141, 0.233] | 0.2343 | 0.062 | 0.556 |
| sex | M | 2272 | 524 | 0.1868 | [0.150, 0.224] | 0.2221 | 0.057 | 0.548 |
| age_bucket | <20 | 337 | 125 | 0.2703 | [0.167, 0.332] | 0.3200 | 0.108 | 0.744 |
| age_bucket | 20-40 | 1087 | 265 | 0.1879 | [0.139, 0.234] | 0.2219 | 0.058 | 0.558 |
| age_bucket | 40-60 | 1598 | 334 | 0.2057 | [0.159, 0.252] | 0.2500 | 0.057 | 0.545 |
| age_bucket | 60+ | 980 | 176 | 0.1028 | [0.069, 0.128] | 0.1261 | 0.050 | 0.415 |
| cls | Lung Opacity | 900 | 900 | 0.2272 | [0.195, 0.258] | 0.2272 | – | 0.551 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.103 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.059 | – |
| n_boxes | 1 | 392 | 392 | 0.1131 | [0.091, 0.139] | 0.1131 | – | 0.372 |
| n_boxes | 2 | 490 | 490 | 0.3221 | [0.279, 0.360] | 0.3221 | – | 0.686 |
| n_boxes | 3+ | 18 | 18 | 0.1302 | [0.063, 0.208] | 0.1302 | – | 0.778 |
