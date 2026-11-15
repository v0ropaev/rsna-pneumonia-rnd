### b_aug_s0:tuned — test

mAP **0.2166** [0.1742, 0.2616] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4004, scored 1243

| metric | value |
|---|---|
| image_roc_auc | 0.8781 |
| image_pr_auc | 0.7099 |
| sensitivity | 0.6389 |
| specificity | 0.8895 |
| matched_iou | 0.6482 |
| mAP on positives only | 0.2991 |
| FP-image rate on negatives | 0.1105 (343/3104) |
| loss: FP on negatives | 0.2759 |
| loss: missed positives (no box) | 0.2615 |
| loss: localization on positives | 0.2460 |
| oracle gating @run thr | 0.2991 |
| oracle gating @best thr (0.15) | 0.3892 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2450 | [0.187, 0.308] | 0.3299 | 0.214 | 0.713 |
| view | PA | 2177 | 202 | 0.1284 | [0.096, 0.161] | 0.1926 | 0.051 | 0.381 |
| sex | F | 1729 | 374 | 0.2041 | [0.161, 0.254] | 0.2914 | 0.118 | 0.663 |
| sex | M | 2275 | 526 | 0.2259 | [0.156, 0.296] | 0.3046 | 0.105 | 0.622 |
| age_bucket | <20 | 246 | 71 | 0.2293 | [0.176, 0.293] | 0.2874 | 0.103 | 0.662 |
| age_bucket | 20-40 | 949 | 249 | 0.2377 | [0.182, 0.281] | 0.3284 | 0.136 | 0.703 |
| age_bucket | 40-60 | 1767 | 363 | 0.2333 | [0.144, 0.336] | 0.3258 | 0.103 | 0.645 |
| age_bucket | 60+ | 1041 | 217 | 0.1608 | [0.115, 0.209] | 0.2245 | 0.104 | 0.548 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2991 | [0.248, 0.352] | 0.2991 | – | 0.639 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.193 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.111 | – |
| n_boxes | 1 | 390 | 390 | 0.2074 | [0.171, 0.240] | 0.2074 | – | 0.479 |
| n_boxes | 2 | 492 | 492 | 0.3807 | [0.299, 0.463] | 0.3807 | – | 0.766 |
| n_boxes | 3+ | 18 | 18 | 0.0544 | [0.021, 0.101] | 0.0544 | – | 0.611 |
