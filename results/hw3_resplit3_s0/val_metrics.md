### hw3_resplit3_s0 — val

mAP **0.2189** [0.1910, 0.2464] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1184

| metric | value |
|---|---|
| image_roc_auc | 0.8890 |
| image_pr_auc | 0.7089 |
| sensitivity | 0.6144 |
| specificity | 0.9100 |
| matched_iou | 0.6565 |
| mAP on positives only | 0.2864 |
| FP-image rate on negatives | 0.0900 (279/3099) |
| loss: FP on negatives | 0.2356 |
| loss: missed positives (no box) | 0.2948 |
| loss: localization on positives | 0.2507 |
| oracle gating @run thr | 0.2864 |
| oracle gating @best thr (0.05) | 0.3232 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1828 | 703 | 0.2378 | [0.204, 0.268] | 0.3109 | 0.192 | 0.683 |
| view | PA | 2176 | 202 | 0.1532 | [0.117, 0.194] | 0.2010 | 0.032 | 0.376 |
| sex | F | 1728 | 378 | 0.2314 | [0.181, 0.273] | 0.3030 | 0.087 | 0.611 |
| sex | M | 2276 | 527 | 0.2099 | [0.174, 0.243] | 0.2744 | 0.093 | 0.617 |
| age_bucket | <20 | 256 | 87 | 0.2840 | [0.128, 0.374] | 0.3264 | 0.077 | 0.724 |
| age_bucket | 20-40 | 1106 | 255 | 0.2234 | [0.178, 0.269] | 0.2891 | 0.088 | 0.624 |
| age_bucket | 40-60 | 1769 | 391 | 0.2193 | [0.174, 0.265] | 0.2978 | 0.102 | 0.632 |
| age_bucket | 60+ | 872 | 172 | 0.1821 | [0.138, 0.232] | 0.2361 | 0.073 | 0.506 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 905 | 905 | 0.2864 | [0.255, 0.319] | 0.2864 | – | 0.614 |
| cls | No Lung Opacity / Not Normal | 1774 | 0 | 0.0000 | [0.000, 0.000] | – | 0.155 | – |
| cls | Normal | 1325 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 3099 | 0 | 0.0000 | [0.000, 0.000] | – | 0.090 | – |
| n_boxes | 1 | 393 | 393 | 0.1836 | [0.148, 0.211] | 0.1836 | – | 0.473 |
| n_boxes | 2 | 490 | 490 | 0.3756 | [0.322, 0.418] | 0.3756 | – | 0.729 |
| n_boxes | 3+ | 22 | 22 | 0.1328 | [0.065, 0.209] | 0.1328 | – | 0.591 |
