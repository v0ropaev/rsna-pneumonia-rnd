### hw3_frac50_s0 — val

mAP **0.1885** [0.1592, 0.2175] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4002, scored 1083

| metric | value |
|---|---|
| image_roc_auc | 0.8843 |
| image_pr_auc | 0.7040 |
| sensitivity | 0.5511 |
| specificity | 0.9410 |
| matched_iou | 0.6221 |
| mAP on positives only | 0.2268 |
| FP-image rate on negatives | 0.0590 (183/3102) |
| loss: FP on negatives | 0.1690 |
| loss: missed positives (no box) | 0.3730 |
| loss: localization on positives | 0.2695 |
| oracle gating @run thr | 0.2268 |
| oracle gating @best thr (0.05) | 0.2888 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2192 | [0.183, 0.252] | 0.2613 | 0.119 | 0.626 |
| view | PA | 2176 | 202 | 0.0866 | [0.058, 0.111] | 0.1076 | 0.025 | 0.292 |
| sex | F | 1730 | 376 | 0.1920 | [0.139, 0.234] | 0.2349 | 0.062 | 0.556 |
| sex | M | 2272 | 524 | 0.1859 | [0.149, 0.224] | 0.2210 | 0.057 | 0.548 |
| age_bucket | <20 | 337 | 125 | 0.2698 | [0.166, 0.331] | 0.3195 | 0.108 | 0.744 |
| age_bucket | 20-40 | 1087 | 265 | 0.1910 | [0.141, 0.239] | 0.2256 | 0.058 | 0.558 |
| age_bucket | 40-60 | 1598 | 334 | 0.2052 | [0.157, 0.252] | 0.2494 | 0.057 | 0.545 |
| age_bucket | 60+ | 980 | 176 | 0.0978 | [0.065, 0.121] | 0.1200 | 0.050 | 0.415 |
| cls | Lung Opacity | 900 | 900 | 0.2268 | [0.194, 0.257] | 0.2268 | – | 0.551 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.103 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.059 | – |
| n_boxes | 1 | 392 | 392 | 0.1119 | [0.089, 0.139] | 0.1119 | – | 0.372 |
| n_boxes | 2 | 490 | 490 | 0.3220 | [0.277, 0.361] | 0.3220 | – | 0.686 |
| n_boxes | 3+ | 18 | 18 | 0.1397 | [0.072, 0.224] | 0.1397 | – | 0.778 |
