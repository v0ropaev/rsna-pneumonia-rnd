### full_s1:tuned — test

mAP **0.2204** [0.1730, 0.2692] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1122

| metric | value |
|---|---|
| image_roc_auc | 0.8846 |
| image_pr_auc | 0.7255 |
| sensitivity | 0.5911 |
| specificity | 0.9285 |
| matched_iou | 0.6439 |
| mAP on positives only | 0.2748 |
| FP-image rate on negatives | 0.0715 (222/3104) |
| loss: FP on negatives | 0.1979 |
| loss: missed positives (no box) | 0.3280 |
| loss: localization on positives | 0.2537 |
| oracle gating @run thr | 0.2748 |
| oracle gating @best thr (0.05) | 0.3130 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2511 | [0.192, 0.315] | 0.3097 | 0.144 | 0.662 |
| view | PA | 2177 | 202 | 0.1195 | [0.084, 0.155] | 0.1543 | 0.030 | 0.347 |
| sex | F | 1729 | 374 | 0.2044 | [0.159, 0.255] | 0.2596 | 0.075 | 0.602 |
| sex | M | 2275 | 526 | 0.2322 | [0.156, 0.305] | 0.2857 | 0.069 | 0.584 |
| age_bucket | <20 | 246 | 71 | 0.2182 | [0.163, 0.279] | 0.2551 | 0.069 | 0.620 |
| age_bucket | 20-40 | 949 | 249 | 0.2402 | [0.174, 0.288] | 0.3039 | 0.094 | 0.655 |
| age_bucket | 40-60 | 1767 | 363 | 0.2480 | [0.149, 0.355] | 0.3027 | 0.057 | 0.587 |
| age_bucket | 60+ | 1041 | 217 | 0.1554 | [0.113, 0.198] | 0.2012 | 0.078 | 0.516 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2748 | [0.220, 0.331] | 0.2748 | – | 0.591 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.125 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.072 | – |
| n_boxes | 1 | 390 | 390 | 0.1620 | [0.130, 0.191] | 0.1620 | – | 0.431 |
| n_boxes | 2 | 492 | 492 | 0.3712 | [0.286, 0.453] | 0.3712 | – | 0.715 |
| n_boxes | 3+ | 18 | 18 | 0.0841 | [0.042, 0.137] | 0.0841 | – | 0.667 |
