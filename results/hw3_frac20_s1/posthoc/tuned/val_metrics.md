### hw3_frac20_s1:tuned — val

mAP **0.1721** [0.1482, 0.1959] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1263

| metric | value |
|---|---|
| image_roc_auc | 0.8761 |
| image_pr_auc | 0.6905 |
| sensitivity | 0.6744 |
| specificity | 0.8830 |
| matched_iou | 0.6003 |
| mAP on positives only | 0.2416 |
| FP-image rate on negatives | 0.1170 (363/3102) |
| loss: FP on negatives | 0.2874 |
| loss: missed positives (no box) | 0.2320 |
| loss: localization on positives | 0.3085 |
| oracle gating @run thr | 0.2416 |
| oracle gating @best thr (0.05) | 0.2683 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1962 | [0.169, 0.224] | 0.2794 | 0.262 | 0.772 |
| view | PA | 2176 | 202 | 0.0832 | [0.056, 0.106] | 0.1107 | 0.034 | 0.337 |
| sex | F | 1730 | 376 | 0.1813 | [0.139, 0.220] | 0.2585 | 0.118 | 0.684 |
| sex | M | 2272 | 524 | 0.1654 | [0.136, 0.196] | 0.2294 | 0.116 | 0.668 |
| age_bucket | <20 | 337 | 125 | 0.2484 | [0.161, 0.314] | 0.3299 | 0.193 | 0.840 |
| age_bucket | 20-40 | 1087 | 265 | 0.1722 | [0.131, 0.214] | 0.2411 | 0.129 | 0.668 |
| age_bucket | 40-60 | 1598 | 334 | 0.1864 | [0.148, 0.224] | 0.2572 | 0.100 | 0.656 |
| age_bucket | 60+ | 980 | 176 | 0.0995 | [0.075, 0.121] | 0.1499 | 0.111 | 0.602 |
| cls | Lung Opacity | 900 | 900 | 0.2416 | [0.213, 0.271] | 0.2416 | – | 0.674 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.203 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.117 | – |
| n_boxes | 1 | 392 | 392 | 0.1192 | [0.099, 0.142] | 0.1192 | – | 0.485 |
| n_boxes | 2 | 490 | 490 | 0.3428 | [0.304, 0.379] | 0.3428 | – | 0.818 |
| n_boxes | 3+ | 18 | 18 | 0.1531 | [0.086, 0.225] | 0.1531 | – | 0.889 |
