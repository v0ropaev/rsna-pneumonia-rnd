### b_cls_s0:no_gating — test

mAP **0.1843** [0.1473, 0.2241] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4004, scored 1352

| metric | value |
|---|---|
| image_roc_auc | 0.8764 |
| image_pr_auc | 0.7103 |
| sensitivity | 0.6700 |
| specificity | 0.8544 |
| matched_iou | 0.6326 |
| mAP on positives only | 0.2768 |
| FP-image rate on negatives | 0.1456 (452/3104) |
| loss: FP on negatives | 0.3343 |
| loss: missed positives (no box) | 0.2197 |
| loss: localization on positives | 0.2617 |
| oracle gating @run thr | 0.2768 |
| oracle gating @best thr (0.20) | 0.3452 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2078 | [0.158, 0.256] | 0.3093 | 0.302 | 0.744 |
| view | PA | 2177 | 202 | 0.1062 | [0.076, 0.136] | 0.1645 | 0.056 | 0.416 |
| sex | F | 1729 | 374 | 0.1783 | [0.137, 0.224] | 0.2771 | 0.153 | 0.717 |
| sex | M | 2275 | 526 | 0.1887 | [0.132, 0.253] | 0.2766 | 0.140 | 0.637 |
| age_bucket | <20 | 246 | 71 | 0.1636 | [0.115, 0.220] | 0.2234 | 0.149 | 0.634 |
| age_bucket | 20-40 | 949 | 249 | 0.2126 | [0.154, 0.256] | 0.3193 | 0.179 | 0.735 |
| age_bucket | 40-60 | 1767 | 363 | 0.1948 | [0.118, 0.281] | 0.2963 | 0.135 | 0.675 |
| age_bucket | 60+ | 1041 | 217 | 0.1405 | [0.103, 0.185] | 0.2130 | 0.136 | 0.599 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2768 | [0.230, 0.322] | 0.2768 | – | 0.670 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.249 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.008 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.146 | – |
| n_boxes | 1 | 390 | 390 | 0.1764 | [0.147, 0.203] | 0.1764 | – | 0.508 |
| n_boxes | 2 | 492 | 492 | 0.3634 | [0.287, 0.433] | 0.3634 | – | 0.793 |
| n_boxes | 3+ | 18 | 18 | 0.0832 | [0.035, 0.146] | 0.0832 | – | 0.833 |
