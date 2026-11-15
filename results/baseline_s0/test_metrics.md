### baseline_s0 — test

mAP **0.1846** [0.1512, 0.2215] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4004, scored 1531

| metric | value |
|---|---|
| image_roc_auc | 0.8664 |
| image_pr_auc | 0.6726 |
| sensitivity | 0.7656 |
| specificity | 0.7967 |
| matched_iou | 0.6330 |
| mAP on positives only | 0.3141 |
| FP-image rate on negatives | 0.2033 (631/3104) |
| loss: FP on negatives | 0.4121 |
| loss: missed positives (no box) | 0.1378 |
| loss: localization on positives | 0.2654 |
| oracle gating @run thr | 0.3141 |
| oracle gating @best thr (0.15) | 0.3593 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2061 | [0.161, 0.254] | 0.3357 | 0.389 | 0.835 |
| view | PA | 2177 | 202 | 0.1226 | [0.094, 0.150] | 0.2392 | 0.097 | 0.525 |
| sex | F | 1729 | 374 | 0.1781 | [0.143, 0.220] | 0.3067 | 0.199 | 0.807 |
| sex | M | 2275 | 526 | 0.1894 | [0.138, 0.245] | 0.3193 | 0.206 | 0.736 |
| age_bucket | <20 | 246 | 71 | 0.1865 | [0.138, 0.247] | 0.2915 | 0.229 | 0.789 |
| age_bucket | 20-40 | 949 | 249 | 0.2062 | [0.157, 0.246] | 0.3378 | 0.227 | 0.807 |
| age_bucket | 40-60 | 1767 | 363 | 0.1981 | [0.129, 0.279] | 0.3460 | 0.193 | 0.777 |
| age_bucket | 60+ | 1041 | 217 | 0.1383 | [0.103, 0.178] | 0.2408 | 0.195 | 0.691 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.3141 | [0.271, 0.359] | 0.3141 | – | 0.766 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.342 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.019 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.203 | – |
| n_boxes | 1 | 390 | 390 | 0.2355 | [0.207, 0.268] | 0.2355 | – | 0.631 |
| n_boxes | 2 | 492 | 492 | 0.3847 | [0.313, 0.454] | 0.3847 | – | 0.868 |
| n_boxes | 3+ | 18 | 18 | 0.0867 | [0.046, 0.139] | 0.0867 | – | 0.889 |
