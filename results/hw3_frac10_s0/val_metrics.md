### hw3_frac10_s0 — val

mAP **0.1507** [0.1288, 0.1719] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1240

| metric | value |
|---|---|
| image_roc_auc | 0.8692 |
| image_pr_auc | 0.6750 |
| sensitivity | 0.6278 |
| specificity | 0.8904 |
| matched_iou | 0.5853 |
| mAP on positives only | 0.2076 |
| FP-image rate on negatives | 0.1096 (340/3102) |
| loss: FP on negatives | 0.2742 |
| loss: missed positives (no box) | 0.2702 |
| loss: localization on positives | 0.3049 |
| oracle gating @run thr | 0.2076 |
| oracle gating @best thr (0.05) | 0.2303 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1692 | [0.145, 0.194] | 0.2361 | 0.245 | 0.718 |
| view | PA | 2176 | 202 | 0.0830 | [0.056, 0.110] | 0.1093 | 0.032 | 0.317 |
| sex | F | 1730 | 376 | 0.1586 | [0.124, 0.194] | 0.2244 | 0.115 | 0.646 |
| sex | M | 2272 | 524 | 0.1448 | [0.121, 0.173] | 0.1956 | 0.105 | 0.615 |
| age_bucket | <20 | 337 | 125 | 0.2157 | [0.140, 0.272] | 0.2847 | 0.189 | 0.784 |
| age_bucket | 20-40 | 1087 | 265 | 0.1528 | [0.119, 0.188] | 0.2105 | 0.122 | 0.608 |
| age_bucket | 40-60 | 1598 | 334 | 0.1605 | [0.126, 0.192] | 0.2187 | 0.096 | 0.638 |
| age_bucket | 60+ | 980 | 176 | 0.0882 | [0.059, 0.112] | 0.1277 | 0.098 | 0.528 |
| cls | Lung Opacity | 900 | 900 | 0.2076 | [0.181, 0.234] | 0.2076 | – | 0.628 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.189 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.005 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.110 | – |
| n_boxes | 1 | 392 | 392 | 0.1123 | [0.089, 0.137] | 0.1123 | – | 0.459 |
| n_boxes | 2 | 490 | 490 | 0.2870 | [0.254, 0.321] | 0.2870 | – | 0.759 |
| n_boxes | 3+ | 18 | 18 | 0.1227 | [0.058, 0.195] | 0.1227 | – | 0.722 |
