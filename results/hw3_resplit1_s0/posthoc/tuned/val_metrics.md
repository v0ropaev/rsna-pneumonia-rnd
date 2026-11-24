### hw3_resplit1_s0:tuned — val

mAP **0.2051** [0.1759, 0.2341] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4003, scored 1155

| metric | value |
|---|---|
| image_roc_auc | 0.8856 |
| image_pr_auc | 0.7106 |
| sensitivity | 0.5767 |
| specificity | 0.9178 |
| matched_iou | 0.6552 |
| mAP on positives only | 0.2632 |
| FP-image rate on negatives | 0.0822 (255/3103) |
| loss: FP on negatives | 0.2208 |
| loss: missed positives (no box) | 0.3299 |
| loss: localization on positives | 0.2442 |
| oracle gating @run thr | 0.2632 |
| oracle gating @best thr (0.05) | 0.3207 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 699 | 0.2268 | [0.194, 0.261] | 0.2933 | 0.182 | 0.648 |
| view | PA | 2177 | 201 | 0.1271 | [0.096, 0.167] | 0.1587 | 0.025 | 0.328 |
| sex | F | 1729 | 375 | 0.2173 | [0.172, 0.259] | 0.2787 | 0.078 | 0.589 |
| sex | M | 2274 | 525 | 0.1964 | [0.165, 0.231] | 0.2521 | 0.085 | 0.568 |
| age_bucket | <20 | 258 | 80 | 0.2909 | [0.161, 0.392] | 0.3418 | 0.079 | 0.738 |
| age_bucket | 20-40 | 1088 | 255 | 0.1733 | [0.128, 0.221] | 0.2230 | 0.088 | 0.514 |
| age_bucket | 40-60 | 1692 | 385 | 0.2290 | [0.176, 0.281] | 0.2986 | 0.090 | 0.629 |
| age_bucket | 60+ | 964 | 180 | 0.1633 | [0.123, 0.198] | 0.2095 | 0.065 | 0.483 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2632 | [0.230, 0.297] | 0.2632 | – | 0.577 |
| cls | No Lung Opacity / Not Normal | 1774 | 0 | 0.0000 | [0.000, 0.000] | – | 0.143 | – |
| cls | Normal | 1329 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3103 | 0 | 0.0000 | [0.000, 0.000] | – | 0.082 | – |
| n_boxes | 1 | 390 | 390 | 0.1646 | [0.135, 0.190] | 0.1646 | – | 0.436 |
| n_boxes | 2 | 489 | 489 | 0.3470 | [0.297, 0.393] | 0.3470 | – | 0.681 |
| n_boxes | 3+ | 21 | 21 | 0.1433 | [0.079, 0.232] | 0.1433 | – | 0.762 |
