### b_cls_s0 — val

mAP **0.1960** [0.1670, 0.2242] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.20; images 4002, scored 1150

| metric | value |
|---|---|
| image_roc_auc | 0.8836 |
| image_pr_auc | 0.7003 |
| sensitivity | 0.5811 |
| specificity | 0.9194 |
| matched_iou | 0.6319 |
| mAP on positives only | 0.2505 |
| FP-image rate on negatives | 0.0806 (250/3102) |
| loss: FP on negatives | 0.2174 |
| loss: missed positives (no box) | 0.3278 |
| loss: localization on positives | 0.2588 |
| oracle gating @run thr | 0.2505 |
| oracle gating @best thr (0.05) | 0.2939 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2223 | [0.192, 0.253] | 0.2946 | 0.201 | 0.688 |
| view | PA | 2176 | 202 | 0.0878 | [0.056, 0.118] | 0.0978 | 0.012 | 0.213 |
| sex | F | 1730 | 376 | 0.2034 | [0.150, 0.249] | 0.2639 | 0.083 | 0.588 |
| sex | M | 2272 | 524 | 0.1906 | [0.159, 0.224] | 0.2408 | 0.079 | 0.576 |
| age_bucket | <20 | 337 | 125 | 0.2803 | [0.201, 0.334] | 0.3408 | 0.127 | 0.768 |
| age_bucket | 20-40 | 1087 | 265 | 0.1867 | [0.138, 0.233] | 0.2445 | 0.100 | 0.581 |
| age_bucket | 40-60 | 1598 | 334 | 0.2195 | [0.168, 0.267] | 0.2780 | 0.070 | 0.590 |
| age_bucket | 60+ | 980 | 176 | 0.1103 | [0.069, 0.139] | 0.1429 | 0.065 | 0.432 |
| cls | Lung Opacity | 900 | 900 | 0.2505 | [0.216, 0.284] | 0.2505 | – | 0.581 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.140 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.081 | – |
| n_boxes | 1 | 392 | 392 | 0.1275 | [0.102, 0.154] | 0.1275 | – | 0.390 |
| n_boxes | 2 | 490 | 490 | 0.3541 | [0.303, 0.398] | 0.3541 | – | 0.735 |
| n_boxes | 3+ | 18 | 18 | 0.1081 | [0.033, 0.185] | 0.1081 | – | 0.556 |
