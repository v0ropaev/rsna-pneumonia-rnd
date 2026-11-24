### hw3_leak_s1:tuned — val

mAP **0.2121** [0.1813, 0.2418] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 3308, scored 824

| metric | value |
|---|---|
| image_roc_auc | 0.8933 |
| image_pr_auc | 0.7095 |
| sensitivity | 0.5596 |
| specificity | 0.9448 |
| matched_iou | 0.6472 |
| mAP on positives only | 0.2573 |
| FP-image rate on negatives | 0.0552 (145/2629) |
| loss: FP on negatives | 0.1760 |
| loss: missed positives (no box) | 0.3629 |
| loss: localization on positives | 0.2491 |
| oracle gating @run thr | 0.2573 |
| oracle gating @best thr (0.05) | 0.3084 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1428 | 516 | 0.2403 | [0.207, 0.277] | 0.2938 | 0.126 | 0.641 |
| view | PA | 1880 | 163 | 0.1198 | [0.087, 0.155] | 0.1418 | 0.017 | 0.301 |
| sex | F | 1447 | 287 | 0.2171 | [0.163, 0.270] | 0.2587 | 0.047 | 0.551 |
| sex | M | 1861 | 392 | 0.2085 | [0.169, 0.246] | 0.2563 | 0.061 | 0.566 |
| age_bucket | <20 | 273 | 87 | 0.2842 | [0.200, 0.336] | 0.3430 | 0.097 | 0.782 |
| age_bucket | 20-40 | 919 | 209 | 0.2144 | [0.161, 0.261] | 0.2606 | 0.063 | 0.574 |
| age_bucket | 40-60 | 1310 | 245 | 0.2449 | [0.187, 0.297] | 0.2939 | 0.046 | 0.567 |
| age_bucket | 60+ | 806 | 138 | 0.1078 | [0.064, 0.141] | 0.1335 | 0.049 | 0.384 |
| cls | Lung Opacity | 679 | 679 | 0.2573 | [0.222, 0.291] | 0.2573 | – | 0.560 |
| cls | No Lung Opacity / Not Normal | 1431 | 0 | 0.0000 | [0.000, 0.000] | – | 0.100 | – |
| cls | Normal | 1198 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 2629 | 0 | 0.0000 | [0.000, 0.000] | – | 0.055 | – |
| n_boxes | 1 | 308 | 308 | 0.1466 | [0.112, 0.179] | 0.1466 | – | 0.393 |
| n_boxes | 2 | 357 | 357 | 0.3580 | [0.306, 0.405] | 0.3580 | – | 0.697 |
| n_boxes | 3+ | 14 | 14 | 0.1244 | [0.060, 0.197] | 0.1244 | – | 0.714 |
