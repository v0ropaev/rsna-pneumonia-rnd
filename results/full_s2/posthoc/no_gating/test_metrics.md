### full_s2:no_gating — test

mAP **0.2130** [0.1761, 0.2541] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4004, scored 1400

| metric | value |
|---|---|
| image_roc_auc | 0.8871 |
| image_pr_auc | 0.7283 |
| sensitivity | 0.7256 |
| specificity | 0.8389 |
| matched_iou | 0.6473 |
| mAP on positives only | 0.3313 |
| FP-image rate on negatives | 0.1611 (500/3104) |
| loss: FP on negatives | 0.3571 |
| loss: missed positives (no box) | 0.1764 |
| loss: localization on positives | 0.2534 |
| oracle gating @run thr | 0.3313 |
| oracle gating @best thr (0.15) | 0.3848 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2420 | [0.192, 0.293] | 0.3616 | 0.306 | 0.799 |
| view | PA | 2177 | 202 | 0.1283 | [0.100, 0.158] | 0.2267 | 0.078 | 0.470 |
| sex | F | 1729 | 374 | 0.2033 | [0.165, 0.247] | 0.3202 | 0.159 | 0.743 |
| sex | M | 2275 | 526 | 0.2200 | [0.162, 0.281] | 0.3392 | 0.163 | 0.713 |
| age_bucket | <20 | 246 | 71 | 0.2093 | [0.160, 0.260] | 0.2947 | 0.166 | 0.690 |
| age_bucket | 20-40 | 949 | 249 | 0.2268 | [0.178, 0.266] | 0.3498 | 0.193 | 0.759 |
| age_bucket | 40-60 | 1767 | 363 | 0.2334 | [0.155, 0.321] | 0.3658 | 0.147 | 0.744 |
| age_bucket | 60+ | 1041 | 217 | 0.1653 | [0.128, 0.202] | 0.2643 | 0.158 | 0.668 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.3313 | [0.285, 0.378] | 0.3313 | – | 0.726 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.277 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.006 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.161 | – |
| n_boxes | 1 | 390 | 390 | 0.2593 | [0.223, 0.293] | 0.2593 | – | 0.608 |
| n_boxes | 2 | 492 | 492 | 0.3973 | [0.318, 0.473] | 0.3973 | – | 0.817 |
| n_boxes | 3+ | 18 | 18 | 0.0883 | [0.042, 0.140] | 0.0883 | – | 0.778 |
