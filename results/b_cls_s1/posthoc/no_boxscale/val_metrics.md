### b_cls_s1:no_boxscale — val

mAP **0.1957** [0.1666, 0.2233] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4002, scored 1131

| metric | value |
|---|---|
| image_roc_auc | 0.8868 |
| image_pr_auc | 0.7086 |
| sensitivity | 0.5856 |
| specificity | 0.9255 |
| matched_iou | 0.6346 |
| mAP on positives only | 0.2459 |
| FP-image rate on negatives | 0.0745 (231/3102) |
| loss: FP on negatives | 0.2042 |
| loss: missed positives (no box) | 0.3298 |
| loss: localization on positives | 0.2702 |
| oracle gating @run thr | 0.2459 |
| oracle gating @best thr (0.05) | 0.2885 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2221 | [0.191, 0.254] | 0.2848 | 0.175 | 0.679 |
| view | PA | 2176 | 202 | 0.0956 | [0.065, 0.123] | 0.1117 | 0.017 | 0.262 |
| sex | F | 1730 | 376 | 0.1941 | [0.139, 0.240] | 0.2458 | 0.074 | 0.590 |
| sex | M | 2272 | 524 | 0.1969 | [0.162, 0.229] | 0.2461 | 0.075 | 0.582 |
| age_bucket | <20 | 337 | 125 | 0.2926 | [0.210, 0.347] | 0.3488 | 0.113 | 0.752 |
| age_bucket | 20-40 | 1087 | 265 | 0.1962 | [0.153, 0.242] | 0.2465 | 0.083 | 0.589 |
| age_bucket | 40-60 | 1598 | 334 | 0.2108 | [0.160, 0.261] | 0.2619 | 0.064 | 0.569 |
| age_bucket | 60+ | 980 | 176 | 0.1066 | [0.075, 0.133] | 0.1418 | 0.072 | 0.494 |
| cls | Lung Opacity | 900 | 900 | 0.2459 | [0.214, 0.277] | 0.2459 | – | 0.586 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.129 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.074 | – |
| n_boxes | 1 | 392 | 392 | 0.1233 | [0.098, 0.152] | 0.1233 | – | 0.406 |
| n_boxes | 2 | 490 | 490 | 0.3490 | [0.303, 0.392] | 0.3490 | – | 0.727 |
| n_boxes | 3+ | 18 | 18 | 0.1105 | [0.057, 0.189] | 0.1105 | – | 0.667 |
