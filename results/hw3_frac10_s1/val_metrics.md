### hw3_frac10_s1 — val

mAP **0.1516** [0.1306, 0.1719] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1308

| metric | value |
|---|---|
| image_roc_auc | 0.8682 |
| image_pr_auc | 0.6742 |
| sensitivity | 0.6633 |
| specificity | 0.8685 |
| matched_iou | 0.5900 |
| mAP on positives only | 0.2203 |
| FP-image rate on negatives | 0.1315 (408/3102) |
| loss: FP on negatives | 0.3119 |
| loss: missed positives (no box) | 0.2317 |
| loss: localization on positives | 0.3049 |
| oracle gating @run thr | 0.2203 |
| oracle gating @best thr (0.05) | 0.2426 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1703 | [0.148, 0.193] | 0.2500 | 0.290 | 0.748 |
| view | PA | 2176 | 202 | 0.0838 | [0.055, 0.113] | 0.1174 | 0.041 | 0.371 |
| sex | F | 1730 | 376 | 0.1606 | [0.125, 0.192] | 0.2379 | 0.134 | 0.668 |
| sex | M | 2272 | 524 | 0.1448 | [0.121, 0.170] | 0.2076 | 0.130 | 0.660 |
| age_bucket | <20 | 337 | 125 | 0.2259 | [0.145, 0.276] | 0.2873 | 0.160 | 0.768 |
| age_bucket | 20-40 | 1087 | 265 | 0.1585 | [0.124, 0.192] | 0.2243 | 0.134 | 0.638 |
| age_bucket | 40-60 | 1598 | 334 | 0.1545 | [0.122, 0.188] | 0.2261 | 0.123 | 0.677 |
| age_bucket | 60+ | 980 | 176 | 0.0960 | [0.070, 0.118] | 0.1555 | 0.136 | 0.602 |
| cls | Lung Opacity | 900 | 900 | 0.2203 | [0.194, 0.246] | 0.2203 | – | 0.663 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.225 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.007 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.132 | – |
| n_boxes | 1 | 392 | 392 | 0.1146 | [0.095, 0.136] | 0.1146 | – | 0.487 |
| n_boxes | 2 | 490 | 490 | 0.3081 | [0.274, 0.341] | 0.3081 | – | 0.798 |
| n_boxes | 3+ | 18 | 18 | 0.1297 | [0.058, 0.210] | 0.1297 | – | 0.833 |
