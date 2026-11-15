### full_s2:tuned — test

mAP **0.2228** [0.1762, 0.2714] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1103

| metric | value |
|---|---|
| image_roc_auc | 0.8871 |
| image_pr_auc | 0.7283 |
| sensitivity | 0.5722 |
| specificity | 0.9346 |
| matched_iou | 0.6547 |
| mAP on positives only | 0.2730 |
| FP-image rate on negatives | 0.0654 (203/3104) |
| loss: FP on negatives | 0.1840 |
| loss: missed positives (no box) | 0.3490 |
| loss: localization on positives | 0.2441 |
| oracle gating @run thr | 0.2730 |
| oracle gating @best thr (0.05) | 0.3139 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2494 | [0.189, 0.314] | 0.3044 | 0.136 | 0.643 |
| view | PA | 2177 | 202 | 0.1324 | [0.097, 0.172] | 0.1646 | 0.025 | 0.327 |
| sex | F | 1729 | 374 | 0.2131 | [0.166, 0.264] | 0.2638 | 0.066 | 0.586 |
| sex | M | 2275 | 526 | 0.2297 | [0.152, 0.305] | 0.2795 | 0.065 | 0.563 |
| age_bucket | <20 | 246 | 71 | 0.2230 | [0.169, 0.281] | 0.2607 | 0.069 | 0.620 |
| age_bucket | 20-40 | 949 | 249 | 0.2264 | [0.163, 0.275] | 0.2883 | 0.097 | 0.622 |
| age_bucket | 40-60 | 1767 | 363 | 0.2592 | [0.155, 0.365] | 0.3106 | 0.051 | 0.576 |
| age_bucket | 60+ | 1041 | 217 | 0.1592 | [0.111, 0.206] | 0.1966 | 0.062 | 0.493 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2730 | [0.219, 0.327] | 0.2730 | – | 0.572 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.114 | – |
| cls | Normal | 1331 | 0 | – | [–, –] | – | 0.000 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.065 | – |
| n_boxes | 1 | 390 | 390 | 0.1606 | [0.129, 0.189] | 0.1606 | – | 0.408 |
| n_boxes | 2 | 492 | 492 | 0.3689 | [0.284, 0.454] | 0.3689 | – | 0.699 |
| n_boxes | 3+ | 18 | 18 | 0.0872 | [0.035, 0.154] | 0.0872 | – | 0.667 |
