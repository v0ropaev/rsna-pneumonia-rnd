### hw3_frac20_s0 — val

mAP **0.1630** [0.1397, 0.1869] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1182

| metric | value |
|---|---|
| image_roc_auc | 0.8754 |
| image_pr_auc | 0.6851 |
| sensitivity | 0.6011 |
| specificity | 0.9091 |
| matched_iou | 0.5906 |
| mAP on positives only | 0.2140 |
| FP-image rate on negatives | 0.0909 (282/3102) |
| loss: FP on negatives | 0.2386 |
| loss: missed positives (no box) | 0.3037 |
| loss: localization on positives | 0.2947 |
| oracle gating @run thr | 0.2140 |
| oracle gating @best thr (0.05) | 0.2493 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1855 | [0.158, 0.211] | 0.2440 | 0.195 | 0.675 |
| view | PA | 2176 | 202 | 0.0846 | [0.059, 0.109] | 0.1106 | 0.031 | 0.347 |
| sex | F | 1730 | 376 | 0.1668 | [0.120, 0.206] | 0.2227 | 0.093 | 0.625 |
| sex | M | 2272 | 524 | 0.1601 | [0.134, 0.191] | 0.2078 | 0.089 | 0.584 |
| age_bucket | <20 | 337 | 125 | 0.2169 | [0.135, 0.272] | 0.2725 | 0.151 | 0.696 |
| age_bucket | 20-40 | 1087 | 265 | 0.1656 | [0.129, 0.207] | 0.2156 | 0.097 | 0.596 |
| age_bucket | 40-60 | 1598 | 334 | 0.1799 | [0.140, 0.215] | 0.2343 | 0.080 | 0.620 |
| age_bucket | 60+ | 980 | 176 | 0.0947 | [0.067, 0.116] | 0.1318 | 0.086 | 0.506 |
| cls | Lung Opacity | 900 | 900 | 0.2140 | [0.186, 0.243] | 0.2140 | – | 0.601 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.158 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.091 | – |
| n_boxes | 1 | 392 | 392 | 0.1191 | [0.095, 0.143] | 0.1191 | – | 0.421 |
| n_boxes | 2 | 490 | 490 | 0.2919 | [0.257, 0.329] | 0.2919 | – | 0.737 |
| n_boxes | 3+ | 18 | 18 | 0.1623 | [0.090, 0.242] | 0.1623 | – | 0.833 |
