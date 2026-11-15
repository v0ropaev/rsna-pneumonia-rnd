### b_aug_s0:tuned — val

mAP **0.2153** [0.1860, 0.2439] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4002, scored 1209

| metric | value |
|---|---|
| image_roc_auc | 0.8865 |
| image_pr_auc | 0.7061 |
| sensitivity | 0.6289 |
| specificity | 0.9004 |
| matched_iou | 0.6435 |
| mAP on positives only | 0.2892 |
| FP-image rate on negatives | 0.0996 (309/3102) |
| loss: FP on negatives | 0.2556 |
| loss: missed positives (no box) | 0.2763 |
| loss: localization on positives | 0.2529 |
| oracle gating @run thr | 0.2892 |
| oracle gating @best thr (0.15) | 0.3847 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2443 | [0.213, 0.277] | 0.3259 | 0.207 | 0.703 |
| view | PA | 2176 | 202 | 0.1180 | [0.087, 0.148] | 0.1623 | 0.039 | 0.371 |
| sex | F | 1730 | 376 | 0.2168 | [0.160, 0.262] | 0.2975 | 0.103 | 0.622 |
| sex | M | 2272 | 524 | 0.2141 | [0.177, 0.250] | 0.2832 | 0.097 | 0.634 |
| age_bucket | <20 | 337 | 125 | 0.3078 | [0.219, 0.364] | 0.3842 | 0.146 | 0.800 |
| age_bucket | 20-40 | 1087 | 265 | 0.2224 | [0.167, 0.275] | 0.2946 | 0.105 | 0.623 |
| age_bucket | 40-60 | 1598 | 334 | 0.2277 | [0.179, 0.274] | 0.3068 | 0.092 | 0.644 |
| age_bucket | 60+ | 980 | 176 | 0.1257 | [0.097, 0.152] | 0.1800 | 0.095 | 0.489 |
| cls | Lung Opacity | 900 | 900 | 0.2892 | [0.254, 0.321] | 0.2892 | – | 0.629 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.172 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.100 | – |
| n_boxes | 1 | 392 | 392 | 0.2108 | [0.179, 0.246] | 0.2108 | – | 0.485 |
| n_boxes | 2 | 490 | 490 | 0.3581 | [0.309, 0.403] | 0.3581 | – | 0.741 |
| n_boxes | 3+ | 18 | 18 | 0.1192 | [0.053, 0.195] | 0.1192 | – | 0.722 |
