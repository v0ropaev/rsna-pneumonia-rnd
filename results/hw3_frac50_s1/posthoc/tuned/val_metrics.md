### hw3_frac50_s1:tuned — val

mAP **0.2040** [0.1779, 0.2304] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1239

| metric | value |
|---|---|
| image_roc_auc | 0.8874 |
| image_pr_auc | 0.7112 |
| sensitivity | 0.6644 |
| specificity | 0.8907 |
| matched_iou | 0.6293 |
| mAP on positives only | 0.2808 |
| FP-image rate on negatives | 0.1093 (339/3102) |
| loss: FP on negatives | 0.2736 |
| loss: missed positives (no box) | 0.2437 |
| loss: localization on positives | 0.2787 |
| oracle gating @run thr | 0.2808 |
| oracle gating @best thr (0.05) | 0.3123 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2329 | [0.203, 0.263] | 0.3197 | 0.230 | 0.745 |
| view | PA | 2176 | 202 | 0.1053 | [0.078, 0.132] | 0.1465 | 0.040 | 0.386 |
| sex | F | 1730 | 376 | 0.2046 | [0.155, 0.247] | 0.2862 | 0.111 | 0.652 |
| sex | M | 2272 | 524 | 0.2035 | [0.171, 0.234] | 0.2769 | 0.108 | 0.674 |
| age_bucket | <20 | 337 | 125 | 0.2793 | [0.194, 0.344] | 0.3553 | 0.160 | 0.808 |
| age_bucket | 20-40 | 1087 | 265 | 0.2039 | [0.160, 0.246] | 0.2763 | 0.114 | 0.672 |
| age_bucket | 40-60 | 1598 | 334 | 0.2202 | [0.175, 0.266] | 0.3072 | 0.104 | 0.665 |
| age_bucket | 60+ | 980 | 176 | 0.1274 | [0.094, 0.152] | 0.1846 | 0.098 | 0.551 |
| cls | Lung Opacity | 900 | 900 | 0.2808 | [0.250, 0.315] | 0.2808 | – | 0.664 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.190 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.109 | – |
| n_boxes | 1 | 392 | 392 | 0.1593 | [0.136, 0.185] | 0.1593 | – | 0.500 |
| n_boxes | 2 | 490 | 490 | 0.3821 | [0.337, 0.424] | 0.3821 | – | 0.788 |
| n_boxes | 3+ | 18 | 18 | 0.1700 | [0.091, 0.263] | 0.1700 | – | 0.889 |
