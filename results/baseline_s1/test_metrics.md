### baseline_s1 — test

mAP **0.1845** [0.1530, 0.2182] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4004, scored 1479

| metric | value |
|---|---|
| image_roc_auc | 0.8711 |
| image_pr_auc | 0.6869 |
| sensitivity | 0.7544 |
| specificity | 0.8135 |
| matched_iou | 0.6320 |
| mAP on positives only | 0.3031 |
| FP-image rate on negatives | 0.1865 (579/3104) |
| loss: FP on negatives | 0.3915 |
| loss: missed positives (no box) | 0.1494 |
| loss: localization on positives | 0.2746 |
| oracle gating @run thr | 0.3031 |
| oracle gating @best thr (0.20) | 0.3434 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2053 | [0.163, 0.247] | 0.3291 | 0.373 | 0.828 |
| view | PA | 2177 | 202 | 0.1198 | [0.090, 0.146] | 0.2136 | 0.080 | 0.500 |
| sex | F | 1729 | 374 | 0.1844 | [0.154, 0.222] | 0.3072 | 0.184 | 0.775 |
| sex | M | 2275 | 526 | 0.1845 | [0.135, 0.239] | 0.3003 | 0.189 | 0.740 |
| age_bucket | <20 | 246 | 71 | 0.1788 | [0.136, 0.230] | 0.2619 | 0.189 | 0.732 |
| age_bucket | 20-40 | 949 | 249 | 0.2047 | [0.151, 0.252] | 0.3207 | 0.201 | 0.759 |
| age_bucket | 40-60 | 1767 | 363 | 0.1994 | [0.137, 0.271] | 0.3350 | 0.176 | 0.777 |
| age_bucket | 60+ | 1041 | 217 | 0.1407 | [0.106, 0.180] | 0.2432 | 0.192 | 0.719 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.3031 | [0.261, 0.343] | 0.3031 | – | 0.754 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.316 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.014 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.187 | – |
| n_boxes | 1 | 390 | 390 | 0.2061 | [0.174, 0.236] | 0.2061 | – | 0.605 |
| n_boxes | 2 | 492 | 492 | 0.3876 | [0.327, 0.441] | 0.3876 | – | 0.872 |
| n_boxes | 3+ | 18 | 18 | 0.0990 | [0.040, 0.169] | 0.0990 | – | 0.778 |
