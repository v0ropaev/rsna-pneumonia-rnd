### hw3_frac20_s1 — val

mAP **0.1706** [0.1464, 0.1950] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1263

| metric | value |
|---|---|
| image_roc_auc | 0.8761 |
| image_pr_auc | 0.6905 |
| sensitivity | 0.6744 |
| specificity | 0.8830 |
| matched_iou | 0.5974 |
| mAP on positives only | 0.2395 |
| FP-image rate on negatives | 0.1170 (363/3102) |
| loss: FP on negatives | 0.2874 |
| loss: missed positives (no box) | 0.2320 |
| loss: localization on positives | 0.3100 |
| oracle gating @run thr | 0.2395 |
| oracle gating @best thr (0.05) | 0.2646 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1946 | [0.167, 0.223] | 0.2771 | 0.262 | 0.772 |
| view | PA | 2176 | 202 | 0.0821 | [0.055, 0.105] | 0.1093 | 0.034 | 0.337 |
| sex | F | 1730 | 376 | 0.1808 | [0.137, 0.220] | 0.2577 | 0.118 | 0.684 |
| sex | M | 2272 | 524 | 0.1631 | [0.134, 0.194] | 0.2263 | 0.116 | 0.668 |
| age_bucket | <20 | 337 | 125 | 0.2471 | [0.160, 0.312] | 0.3282 | 0.193 | 0.840 |
| age_bucket | 20-40 | 1087 | 265 | 0.1706 | [0.129, 0.213] | 0.2388 | 0.129 | 0.668 |
| age_bucket | 40-60 | 1598 | 334 | 0.1839 | [0.145, 0.223] | 0.2539 | 0.100 | 0.656 |
| age_bucket | 60+ | 980 | 176 | 0.0997 | [0.076, 0.120] | 0.1501 | 0.111 | 0.602 |
| cls | Lung Opacity | 900 | 900 | 0.2395 | [0.210, 0.268] | 0.2395 | – | 0.674 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.203 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.117 | – |
| n_boxes | 1 | 392 | 392 | 0.1188 | [0.099, 0.141] | 0.1188 | – | 0.485 |
| n_boxes | 2 | 490 | 490 | 0.3391 | [0.301, 0.376] | 0.3391 | – | 0.818 |
| n_boxes | 3+ | 18 | 18 | 0.1553 | [0.090, 0.225] | 0.1553 | – | 0.889 |
