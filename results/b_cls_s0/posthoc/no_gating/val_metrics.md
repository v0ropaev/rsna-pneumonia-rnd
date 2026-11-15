### b_cls_s0:no_gating — val

mAP **0.1912** [0.1648, 0.2167] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4002, scored 1348

| metric | value |
|---|---|
| image_roc_auc | 0.8836 |
| image_pr_auc | 0.7003 |
| sensitivity | 0.6878 |
| specificity | 0.8556 |
| matched_iou | 0.6319 |
| mAP on positives only | 0.2864 |
| FP-image rate on negatives | 0.1444 (448/3102) |
| loss: FP on negatives | 0.3323 |
| loss: missed positives (no box) | 0.2085 |
| loss: localization on positives | 0.2680 |
| oracle gating @run thr | 0.2864 |
| oracle gating @best thr (0.20) | 0.3415 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2121 | [0.183, 0.242] | 0.3148 | 0.300 | 0.762 |
| view | PA | 2176 | 202 | 0.1217 | [0.093, 0.152] | 0.1880 | 0.056 | 0.431 |
| sex | F | 1730 | 376 | 0.1943 | [0.150, 0.233] | 0.3043 | 0.157 | 0.697 |
| sex | M | 2272 | 524 | 0.1888 | [0.161, 0.222] | 0.2735 | 0.134 | 0.681 |
| age_bucket | <20 | 337 | 125 | 0.2780 | [0.207, 0.335] | 0.3513 | 0.156 | 0.824 |
| age_bucket | 20-40 | 1087 | 265 | 0.1943 | [0.150, 0.236] | 0.2962 | 0.169 | 0.679 |
| age_bucket | 40-60 | 1598 | 334 | 0.2062 | [0.158, 0.249] | 0.3038 | 0.125 | 0.689 |
| age_bucket | 60+ | 980 | 176 | 0.1152 | [0.083, 0.140] | 0.1925 | 0.147 | 0.602 |
| cls | Lung Opacity | 900 | 900 | 0.2864 | [0.255, 0.318] | 0.2864 | – | 0.688 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.243 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.014 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.144 | – |
| n_boxes | 1 | 392 | 392 | 0.2062 | [0.173, 0.239] | 0.2062 | – | 0.533 |
| n_boxes | 2 | 490 | 490 | 0.3550 | [0.308, 0.397] | 0.3550 | – | 0.806 |
| n_boxes | 3+ | 18 | 18 | 0.1646 | [0.087, 0.240] | 0.1646 | – | 0.833 |
