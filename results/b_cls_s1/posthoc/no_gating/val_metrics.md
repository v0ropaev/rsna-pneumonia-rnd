### b_cls_s1:no_gating — val

mAP **0.1921** [0.1672, 0.2167] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4002, scored 1431

| metric | value |
|---|---|
| image_roc_auc | 0.8868 |
| image_pr_auc | 0.7086 |
| sensitivity | 0.7411 |
| specificity | 0.8288 |
| matched_iou | 0.6326 |
| mAP on positives only | 0.3054 |
| FP-image rate on negatives | 0.1712 (531/3102) |
| loss: FP on negatives | 0.3711 |
| loss: missed positives (no box) | 0.1628 |
| loss: localization on positives | 0.2741 |
| oracle gating @run thr | 0.3054 |
| oracle gating @best thr (0.15) | 0.3460 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2154 | [0.188, 0.245] | 0.3395 | 0.356 | 0.821 |
| view | PA | 2176 | 202 | 0.1143 | [0.087, 0.142] | 0.1873 | 0.065 | 0.465 |
| sex | F | 1730 | 376 | 0.1886 | [0.141, 0.228] | 0.3096 | 0.178 | 0.737 |
| sex | M | 2272 | 524 | 0.1946 | [0.164, 0.227] | 0.3023 | 0.166 | 0.744 |
| age_bucket | <20 | 337 | 125 | 0.2920 | [0.218, 0.345] | 0.3878 | 0.193 | 0.888 |
| age_bucket | 20-40 | 1087 | 265 | 0.1938 | [0.152, 0.234] | 0.3086 | 0.191 | 0.728 |
| age_bucket | 40-60 | 1598 | 334 | 0.2057 | [0.162, 0.250] | 0.3270 | 0.156 | 0.734 |
| age_bucket | 60+ | 980 | 176 | 0.1133 | [0.091, 0.138] | 0.2009 | 0.169 | 0.670 |
| cls | Lung Opacity | 900 | 900 | 0.3054 | [0.276, 0.335] | 0.3054 | – | 0.741 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.293 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.009 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.171 | – |
| n_boxes | 1 | 392 | 392 | 0.2215 | [0.187, 0.258] | 0.2215 | – | 0.605 |
| n_boxes | 2 | 490 | 490 | 0.3780 | [0.335, 0.418] | 0.3780 | – | 0.845 |
| n_boxes | 3+ | 18 | 18 | 0.1541 | [0.084, 0.228] | 0.1541 | – | 0.889 |
