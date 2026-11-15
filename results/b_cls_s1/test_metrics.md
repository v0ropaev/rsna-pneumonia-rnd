### b_cls_s1 — test

mAP **0.2006** [0.1597, 0.2434] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1168

| metric | value |
|---|---|
| image_roc_auc | 0.8761 |
| image_pr_auc | 0.7097 |
| sensitivity | 0.5822 |
| specificity | 0.9137 |
| matched_iou | 0.6465 |
| mAP on positives only | 0.2603 |
| FP-image rate on negatives | 0.0863 (268/3104) |
| loss: FP on negatives | 0.2295 |
| loss: missed positives (no box) | 0.3219 |
| loss: localization on positives | 0.2480 |
| oracle gating @run thr | 0.2603 |
| oracle gating @best thr (0.05) | 0.2967 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2272 | [0.170, 0.284] | 0.2975 | 0.191 | 0.668 |
| view | PA | 2177 | 202 | 0.1049 | [0.074, 0.139] | 0.1319 | 0.026 | 0.287 |
| sex | F | 1729 | 374 | 0.2012 | [0.159, 0.248] | 0.2652 | 0.088 | 0.602 |
| sex | M | 2275 | 526 | 0.2002 | [0.134, 0.268] | 0.2569 | 0.085 | 0.568 |
| age_bucket | <20 | 246 | 71 | 0.2001 | [0.146, 0.267] | 0.2424 | 0.086 | 0.620 |
| age_bucket | 20-40 | 949 | 249 | 0.2057 | [0.140, 0.255] | 0.2701 | 0.111 | 0.606 |
| age_bucket | 40-60 | 1767 | 363 | 0.2361 | [0.147, 0.324] | 0.3005 | 0.071 | 0.601 |
| age_bucket | 60+ | 1041 | 217 | 0.1391 | [0.101, 0.178] | 0.1878 | 0.092 | 0.512 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2603 | [0.211, 0.309] | 0.2603 | – | 0.582 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.151 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.086 | – |
| n_boxes | 1 | 390 | 390 | 0.1270 | [0.102, 0.153] | 0.1270 | – | 0.379 |
| n_boxes | 2 | 492 | 492 | 0.3721 | [0.296, 0.441] | 0.3721 | – | 0.740 |
| n_boxes | 3+ | 18 | 18 | 0.0937 | [0.034, 0.178] | 0.0937 | – | 0.667 |
