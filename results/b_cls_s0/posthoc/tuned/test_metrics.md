### b_cls_s0:tuned — test

mAP **0.1922** [0.1498, 0.2362] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.20; images 4004, scored 1153

| metric | value |
|---|---|
| image_roc_auc | 0.8764 |
| image_pr_auc | 0.7103 |
| sensitivity | 0.5811 |
| specificity | 0.9185 |
| matched_iou | 0.6364 |
| mAP on positives only | 0.2462 |
| FP-image rate on negatives | 0.0815 (253/3104) |
| loss: FP on negatives | 0.2194 |
| loss: missed positives (no box) | 0.3270 |
| loss: localization on positives | 0.2614 |
| oracle gating @run thr | 0.2462 |
| oracle gating @best thr (0.05) | 0.3037 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2222 | [0.166, 0.277] | 0.2906 | 0.190 | 0.682 |
| view | PA | 2177 | 202 | 0.0780 | [0.048, 0.109] | 0.0927 | 0.019 | 0.233 |
| sex | F | 1729 | 374 | 0.1912 | [0.148, 0.237] | 0.2459 | 0.079 | 0.618 |
| sex | M | 2275 | 526 | 0.1929 | [0.126, 0.263] | 0.2464 | 0.083 | 0.555 |
| age_bucket | <20 | 246 | 71 | 0.1979 | [0.142, 0.268] | 0.2397 | 0.086 | 0.634 |
| age_bucket | 20-40 | 949 | 249 | 0.2125 | [0.151, 0.260] | 0.2791 | 0.111 | 0.651 |
| age_bucket | 40-60 | 1767 | 363 | 0.2132 | [0.122, 0.308] | 0.2725 | 0.072 | 0.584 |
| age_bucket | 60+ | 1041 | 217 | 0.1309 | [0.091, 0.171] | 0.1665 | 0.072 | 0.479 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2462 | [0.197, 0.296] | 0.2462 | – | 0.581 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.141 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.082 | – |
| n_boxes | 1 | 390 | 390 | 0.1115 | [0.087, 0.134] | 0.1115 | – | 0.377 |
| n_boxes | 2 | 492 | 492 | 0.3586 | [0.285, 0.427] | 0.3586 | – | 0.738 |
| n_boxes | 3+ | 18 | 18 | 0.0920 | [0.033, 0.166] | 0.0920 | – | 0.722 |
