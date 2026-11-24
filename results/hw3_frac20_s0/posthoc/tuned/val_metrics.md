### hw3_frac20_s0:tuned — val

mAP **0.1686** [0.1441, 0.1926] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1182

| metric | value |
|---|---|
| image_roc_auc | 0.8754 |
| image_pr_auc | 0.6851 |
| sensitivity | 0.6011 |
| specificity | 0.9091 |
| matched_iou | 0.6016 |
| mAP on positives only | 0.2214 |
| FP-image rate on negatives | 0.0909 (282/3102) |
| loss: FP on negatives | 0.2386 |
| loss: missed positives (no box) | 0.3037 |
| loss: localization on positives | 0.2891 |
| oracle gating @run thr | 0.2214 |
| oracle gating @best thr (0.05) | 0.2592 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1917 | [0.163, 0.217] | 0.2521 | 0.195 | 0.675 |
| view | PA | 2176 | 202 | 0.0883 | [0.062, 0.114] | 0.1154 | 0.031 | 0.347 |
| sex | F | 1730 | 376 | 0.1727 | [0.125, 0.211] | 0.2305 | 0.093 | 0.625 |
| sex | M | 2272 | 524 | 0.1656 | [0.139, 0.195] | 0.2149 | 0.089 | 0.584 |
| age_bucket | <20 | 337 | 125 | 0.2259 | [0.142, 0.281] | 0.2838 | 0.151 | 0.696 |
| age_bucket | 20-40 | 1087 | 265 | 0.1671 | [0.129, 0.207] | 0.2176 | 0.097 | 0.596 |
| age_bucket | 40-60 | 1598 | 334 | 0.1873 | [0.147, 0.225] | 0.2440 | 0.080 | 0.620 |
| age_bucket | 60+ | 980 | 176 | 0.1006 | [0.071, 0.124] | 0.1401 | 0.086 | 0.506 |
| cls | Lung Opacity | 900 | 900 | 0.2214 | [0.194, 0.251] | 0.2214 | – | 0.601 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.158 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.091 | – |
| n_boxes | 1 | 392 | 392 | 0.1177 | [0.092, 0.141] | 0.1177 | – | 0.421 |
| n_boxes | 2 | 490 | 490 | 0.3075 | [0.271, 0.346] | 0.3075 | – | 0.737 |
| n_boxes | 3+ | 18 | 18 | 0.1381 | [0.069, 0.218] | 0.1381 | – | 0.833 |
