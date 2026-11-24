### hw3_resplit3_s0:tuned — val

mAP **0.2190** [0.1914, 0.2464] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1184

| metric | value |
|---|---|
| image_roc_auc | 0.8890 |
| image_pr_auc | 0.7089 |
| sensitivity | 0.6144 |
| specificity | 0.9100 |
| matched_iou | 0.6612 |
| mAP on positives only | 0.2865 |
| FP-image rate on negatives | 0.0900 (279/3099) |
| loss: FP on negatives | 0.2356 |
| loss: missed positives (no box) | 0.2948 |
| loss: localization on positives | 0.2506 |
| oracle gating @run thr | 0.2865 |
| oracle gating @best thr (0.05) | 0.3251 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1828 | 703 | 0.2382 | [0.204, 0.268] | 0.3114 | 0.192 | 0.683 |
| view | PA | 2176 | 202 | 0.1524 | [0.116, 0.194] | 0.1999 | 0.032 | 0.376 |
| sex | F | 1728 | 378 | 0.2324 | [0.182, 0.272] | 0.3043 | 0.087 | 0.611 |
| sex | M | 2276 | 527 | 0.2094 | [0.174, 0.242] | 0.2738 | 0.093 | 0.617 |
| age_bucket | <20 | 256 | 87 | 0.2823 | [0.126, 0.375] | 0.3245 | 0.077 | 0.724 |
| age_bucket | 20-40 | 1106 | 255 | 0.2216 | [0.178, 0.266] | 0.2868 | 0.088 | 0.624 |
| age_bucket | 40-60 | 1769 | 391 | 0.2200 | [0.175, 0.265] | 0.2988 | 0.102 | 0.632 |
| age_bucket | 60+ | 872 | 172 | 0.1843 | [0.139, 0.236] | 0.2390 | 0.073 | 0.506 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 905 | 905 | 0.2865 | [0.255, 0.319] | 0.2865 | – | 0.614 |
| cls | No Lung Opacity / Not Normal | 1774 | 0 | 0.0000 | [0.000, 0.000] | – | 0.155 | – |
| cls | Normal | 1325 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 3099 | 0 | 0.0000 | [0.000, 0.000] | – | 0.090 | – |
| n_boxes | 1 | 393 | 393 | 0.1797 | [0.144, 0.208] | 0.1797 | – | 0.473 |
| n_boxes | 2 | 490 | 490 | 0.3794 | [0.328, 0.422] | 0.3794 | – | 0.729 |
| n_boxes | 3+ | 22 | 22 | 0.1276 | [0.061, 0.203] | 0.1276 | – | 0.591 |
