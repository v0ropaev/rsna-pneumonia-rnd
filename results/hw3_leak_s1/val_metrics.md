### hw3_leak_s1 — val

mAP **0.2108** [0.1797, 0.2407] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 3308, scored 824

| metric | value |
|---|---|
| image_roc_auc | 0.8933 |
| image_pr_auc | 0.7095 |
| sensitivity | 0.5596 |
| specificity | 0.9448 |
| matched_iou | 0.6465 |
| mAP on positives only | 0.2558 |
| FP-image rate on negatives | 0.0552 (145/2629) |
| loss: FP on negatives | 0.1760 |
| loss: missed positives (no box) | 0.3629 |
| loss: localization on positives | 0.2504 |
| oracle gating @run thr | 0.2558 |
| oracle gating @best thr (0.05) | 0.3074 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1428 | 516 | 0.2389 | [0.205, 0.275] | 0.2922 | 0.126 | 0.641 |
| view | PA | 1880 | 163 | 0.1188 | [0.086, 0.152] | 0.1407 | 0.017 | 0.301 |
| sex | F | 1447 | 287 | 0.2155 | [0.160, 0.268] | 0.2568 | 0.047 | 0.551 |
| sex | M | 1861 | 392 | 0.2074 | [0.169, 0.244] | 0.2551 | 0.061 | 0.566 |
| age_bucket | <20 | 273 | 87 | 0.2873 | [0.204, 0.338] | 0.3467 | 0.097 | 0.782 |
| age_bucket | 20-40 | 919 | 209 | 0.2137 | [0.160, 0.261] | 0.2598 | 0.063 | 0.574 |
| age_bucket | 40-60 | 1310 | 245 | 0.2426 | [0.184, 0.293] | 0.2911 | 0.046 | 0.567 |
| age_bucket | 60+ | 806 | 138 | 0.1048 | [0.061, 0.136] | 0.1298 | 0.049 | 0.384 |
| cls | Lung Opacity | 679 | 679 | 0.2558 | [0.219, 0.288] | 0.2558 | – | 0.560 |
| cls | No Lung Opacity / Not Normal | 1431 | 0 | 0.0000 | [0.000, 0.000] | – | 0.100 | – |
| cls | Normal | 1198 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 2629 | 0 | 0.0000 | [0.000, 0.000] | – | 0.055 | – |
| n_boxes | 1 | 308 | 308 | 0.1446 | [0.111, 0.176] | 0.1446 | – | 0.393 |
| n_boxes | 2 | 357 | 357 | 0.3570 | [0.305, 0.405] | 0.3570 | – | 0.697 |
| n_boxes | 3+ | 14 | 14 | 0.1222 | [0.059, 0.195] | 0.1222 | – | 0.714 |
