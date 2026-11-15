### full_s1:no_gating — test

mAP **0.2176** [0.1722, 0.2648] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4004, scored 1159

| metric | value |
|---|---|
| image_roc_auc | 0.8846 |
| image_pr_auc | 0.7255 |
| sensitivity | 0.5844 |
| specificity | 0.9166 |
| matched_iou | 0.6479 |
| mAP on positives only | 0.2802 |
| FP-image rate on negatives | 0.0834 (259/3104) |
| loss: FP on negatives | 0.2235 |
| loss: missed positives (no box) | 0.3227 |
| loss: localization on positives | 0.2363 |
| oracle gating @run thr | 0.2802 |
| oracle gating @best thr (0.15) | 0.3757 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2484 | [0.189, 0.311] | 0.3135 | 0.162 | 0.656 |
| view | PA | 2177 | 202 | 0.1200 | [0.083, 0.155] | 0.1651 | 0.038 | 0.337 |
| sex | F | 1729 | 374 | 0.2019 | [0.154, 0.257] | 0.2650 | 0.086 | 0.602 |
| sex | M | 2275 | 526 | 0.2291 | [0.155, 0.300] | 0.2910 | 0.081 | 0.572 |
| age_bucket | <20 | 246 | 71 | 0.2204 | [0.166, 0.281] | 0.2607 | 0.074 | 0.634 |
| age_bucket | 20-40 | 949 | 249 | 0.2437 | [0.177, 0.298] | 0.3151 | 0.104 | 0.655 |
| age_bucket | 40-60 | 1767 | 363 | 0.2351 | [0.143, 0.336] | 0.3018 | 0.073 | 0.581 |
| age_bucket | 60+ | 1041 | 217 | 0.1591 | [0.112, 0.210] | 0.2104 | 0.085 | 0.493 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2802 | [0.226, 0.335] | 0.2802 | – | 0.584 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.146 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.083 | – |
| n_boxes | 1 | 390 | 390 | 0.1990 | [0.158, 0.230] | 0.1990 | – | 0.421 |
| n_boxes | 2 | 492 | 492 | 0.3522 | [0.263, 0.436] | 0.3522 | – | 0.709 |
| n_boxes | 3+ | 18 | 18 | 0.0694 | [0.032, 0.107] | 0.0694 | – | 0.722 |
