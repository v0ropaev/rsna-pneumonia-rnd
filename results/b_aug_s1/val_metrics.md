### b_aug_s1 — val

mAP **0.2093** [0.1796, 0.2395] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4002, scored 1119

| metric | value |
|---|---|
| image_roc_auc | 0.8869 |
| image_pr_auc | 0.7083 |
| sensitivity | 0.5667 |
| specificity | 0.9294 |
| matched_iou | 0.6504 |
| mAP on positives only | 0.2603 |
| FP-image rate on negatives | 0.0706 (219/3102) |
| loss: FP on negatives | 0.1957 |
| loss: missed positives (no box) | 0.3485 |
| loss: localization on positives | 0.2464 |
| oracle gating @run thr | 0.2603 |
| oracle gating @best thr (0.15) | 0.3821 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2333 | [0.197, 0.269] | 0.2901 | 0.151 | 0.626 |
| view | PA | 2176 | 202 | 0.1266 | [0.095, 0.158] | 0.1573 | 0.025 | 0.361 |
| sex | F | 1730 | 376 | 0.2255 | [0.167, 0.268] | 0.2824 | 0.070 | 0.569 |
| sex | M | 2272 | 524 | 0.1976 | [0.160, 0.239] | 0.2444 | 0.071 | 0.565 |
| age_bucket | <20 | 337 | 125 | 0.2957 | [0.213, 0.354] | 0.3572 | 0.123 | 0.800 |
| age_bucket | 20-40 | 1087 | 265 | 0.2199 | [0.165, 0.272] | 0.2673 | 0.069 | 0.551 |
| age_bucket | 40-60 | 1598 | 334 | 0.2208 | [0.167, 0.275] | 0.2750 | 0.065 | 0.584 |
| age_bucket | 60+ | 980 | 176 | 0.1171 | [0.076, 0.151] | 0.1531 | 0.067 | 0.392 |
| cls | Lung Opacity | 900 | 900 | 0.2603 | [0.227, 0.293] | 0.2603 | – | 0.567 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.124 | – |
| cls | Normal | 1331 | 0 | – | [–, –] | – | 0.000 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.071 | – |
| n_boxes | 1 | 392 | 392 | 0.1842 | [0.149, 0.220] | 0.1842 | – | 0.434 |
| n_boxes | 2 | 490 | 490 | 0.3260 | [0.275, 0.371] | 0.3260 | – | 0.665 |
| n_boxes | 3+ | 18 | 18 | 0.1302 | [0.055, 0.206] | 0.1302 | – | 0.778 |
