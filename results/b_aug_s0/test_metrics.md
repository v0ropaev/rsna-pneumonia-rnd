### b_aug_s0 — test

mAP **0.2162** [0.1741, 0.2621] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4004, scored 1243

| metric | value |
|---|---|
| image_roc_auc | 0.8781 |
| image_pr_auc | 0.7099 |
| sensitivity | 0.6389 |
| specificity | 0.8895 |
| matched_iou | 0.6551 |
| mAP on positives only | 0.2986 |
| FP-image rate on negatives | 0.1105 (343/3104) |
| loss: FP on negatives | 0.2759 |
| loss: missed positives (no box) | 0.2615 |
| loss: localization on positives | 0.2464 |
| oracle gating @run thr | 0.2986 |
| oracle gating @best thr (0.15) | 0.3930 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2436 | [0.185, 0.307] | 0.3281 | 0.214 | 0.713 |
| view | PA | 2177 | 202 | 0.1313 | [0.096, 0.166] | 0.1970 | 0.051 | 0.381 |
| sex | F | 1729 | 374 | 0.2053 | [0.163, 0.255] | 0.2931 | 0.118 | 0.663 |
| sex | M | 2275 | 526 | 0.2245 | [0.157, 0.293] | 0.3026 | 0.105 | 0.622 |
| age_bucket | <20 | 246 | 71 | 0.2319 | [0.179, 0.295] | 0.2906 | 0.103 | 0.662 |
| age_bucket | 20-40 | 949 | 249 | 0.2352 | [0.180, 0.277] | 0.3249 | 0.136 | 0.703 |
| age_bucket | 40-60 | 1767 | 363 | 0.2372 | [0.146, 0.341] | 0.3313 | 0.103 | 0.645 |
| age_bucket | 60+ | 1041 | 217 | 0.1550 | [0.111, 0.200] | 0.2165 | 0.104 | 0.548 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2986 | [0.247, 0.350] | 0.2986 | – | 0.639 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.193 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.111 | – |
| n_boxes | 1 | 390 | 390 | 0.2029 | [0.167, 0.238] | 0.2029 | – | 0.479 |
| n_boxes | 2 | 492 | 492 | 0.3834 | [0.301, 0.465] | 0.3834 | – | 0.766 |
| n_boxes | 3+ | 18 | 18 | 0.0579 | [0.019, 0.108] | 0.0579 | – | 0.611 |
