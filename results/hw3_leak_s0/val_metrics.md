### hw3_leak_s0 — val

mAP **0.2119** [0.1813, 0.2416] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 3308, scored 860

| metric | value |
|---|---|
| image_roc_auc | 0.8958 |
| image_pr_auc | 0.7129 |
| sensitivity | 0.5965 |
| specificity | 0.9312 |
| matched_iou | 0.6477 |
| mAP on positives only | 0.2684 |
| FP-image rate on negatives | 0.0688 (181/2629) |
| loss: FP on negatives | 0.2105 |
| loss: missed positives (no box) | 0.3186 |
| loss: localization on positives | 0.2590 |
| oracle gating @run thr | 0.2684 |
| oracle gating @best thr (0.05) | 0.3147 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1428 | 516 | 0.2325 | [0.199, 0.267] | 0.2997 | 0.163 | 0.674 |
| view | PA | 1880 | 163 | 0.1415 | [0.104, 0.179] | 0.1692 | 0.019 | 0.350 |
| sex | F | 1447 | 287 | 0.2183 | [0.165, 0.274] | 0.2700 | 0.059 | 0.578 |
| sex | M | 1861 | 392 | 0.2074 | [0.169, 0.245] | 0.2672 | 0.077 | 0.610 |
| age_bucket | <20 | 273 | 87 | 0.2763 | [0.192, 0.335] | 0.3367 | 0.102 | 0.770 |
| age_bucket | 20-40 | 919 | 209 | 0.2038 | [0.148, 0.251] | 0.2652 | 0.089 | 0.603 |
| age_bucket | 40-60 | 1310 | 245 | 0.2493 | [0.195, 0.300] | 0.3094 | 0.055 | 0.612 |
| age_bucket | 60+ | 806 | 138 | 0.1220 | [0.078, 0.152] | 0.1573 | 0.060 | 0.449 |
| cls | Lung Opacity | 679 | 679 | 0.2684 | [0.234, 0.300] | 0.2684 | – | 0.596 |
| cls | No Lung Opacity / Not Normal | 1431 | 0 | 0.0000 | [0.000, 0.000] | – | 0.124 | – |
| cls | Normal | 1198 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 2629 | 0 | 0.0000 | [0.000, 0.000] | – | 0.069 | – |
| n_boxes | 1 | 308 | 308 | 0.1572 | [0.123, 0.190] | 0.1572 | – | 0.445 |
| n_boxes | 2 | 357 | 357 | 0.3689 | [0.316, 0.417] | 0.3689 | – | 0.717 |
| n_boxes | 3+ | 14 | 14 | 0.1496 | [0.090, 0.214] | 0.1496 | – | 0.857 |
