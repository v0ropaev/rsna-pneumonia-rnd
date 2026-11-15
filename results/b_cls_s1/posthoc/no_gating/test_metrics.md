### b_cls_s1:no_gating — test

mAP **0.1964** [0.1621, 0.2324] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4004, scored 1455

| metric | value |
|---|---|
| image_roc_auc | 0.8761 |
| image_pr_auc | 0.7097 |
| sensitivity | 0.7522 |
| specificity | 0.8212 |
| matched_iou | 0.6404 |
| mAP on positives only | 0.3175 |
| FP-image rate on negatives | 0.1788 (555/3104) |
| loss: FP on negatives | 0.3814 |
| loss: missed positives (no box) | 0.1533 |
| loss: localization on positives | 0.2689 |
| oracle gating @run thr | 0.3175 |
| oracle gating @best thr (0.15) | 0.3572 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2250 | [0.179, 0.271] | 0.3526 | 0.351 | 0.831 |
| view | PA | 2177 | 202 | 0.1097 | [0.084, 0.136] | 0.1961 | 0.081 | 0.480 |
| sex | F | 1729 | 374 | 0.1987 | [0.164, 0.238] | 0.3278 | 0.179 | 0.781 |
| sex | M | 2275 | 526 | 0.1946 | [0.141, 0.252] | 0.3101 | 0.178 | 0.732 |
| age_bucket | <20 | 246 | 71 | 0.1871 | [0.136, 0.244] | 0.2688 | 0.177 | 0.718 |
| age_bucket | 20-40 | 949 | 249 | 0.2155 | [0.163, 0.257] | 0.3376 | 0.201 | 0.775 |
| age_bucket | 40-60 | 1767 | 363 | 0.2084 | [0.141, 0.285] | 0.3445 | 0.169 | 0.771 |
| age_bucket | 60+ | 1041 | 217 | 0.1585 | [0.123, 0.195] | 0.2651 | 0.177 | 0.705 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.3175 | [0.272, 0.361] | 0.3175 | – | 0.752 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.305 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.011 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.179 | – |
| n_boxes | 1 | 390 | 390 | 0.2155 | [0.186, 0.242] | 0.2155 | – | 0.605 |
| n_boxes | 2 | 492 | 492 | 0.4058 | [0.340, 0.465] | 0.4058 | – | 0.864 |
| n_boxes | 3+ | 18 | 18 | 0.1117 | [0.051, 0.193] | 0.1117 | – | 0.889 |
