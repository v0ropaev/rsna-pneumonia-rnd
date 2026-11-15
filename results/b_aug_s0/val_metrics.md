### b_aug_s0 — val

mAP **0.2129** [0.1847, 0.2407] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4002, scored 1209

| metric | value |
|---|---|
| image_roc_auc | 0.8865 |
| image_pr_auc | 0.7061 |
| sensitivity | 0.6289 |
| specificity | 0.9004 |
| matched_iou | 0.6475 |
| mAP on positives only | 0.2859 |
| FP-image rate on negatives | 0.0996 (309/3102) |
| loss: FP on negatives | 0.2556 |
| loss: missed positives (no box) | 0.2763 |
| loss: localization on positives | 0.2553 |
| oracle gating @run thr | 0.2859 |
| oracle gating @best thr (0.15) | 0.3842 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2408 | [0.210, 0.271] | 0.3212 | 0.207 | 0.703 |
| view | PA | 2176 | 202 | 0.1192 | [0.088, 0.149] | 0.1640 | 0.039 | 0.371 |
| sex | F | 1730 | 376 | 0.2168 | [0.161, 0.259] | 0.2975 | 0.103 | 0.622 |
| sex | M | 2272 | 524 | 0.2099 | [0.173, 0.246] | 0.2777 | 0.097 | 0.634 |
| age_bucket | <20 | 337 | 125 | 0.3015 | [0.218, 0.358] | 0.3763 | 0.146 | 0.800 |
| age_bucket | 20-40 | 1087 | 265 | 0.2205 | [0.166, 0.271] | 0.2920 | 0.105 | 0.623 |
| age_bucket | 40-60 | 1598 | 334 | 0.2255 | [0.178, 0.271] | 0.3038 | 0.092 | 0.644 |
| age_bucket | 60+ | 980 | 176 | 0.1248 | [0.095, 0.152] | 0.1787 | 0.095 | 0.489 |
| cls | Lung Opacity | 900 | 900 | 0.2859 | [0.252, 0.316] | 0.2859 | – | 0.629 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.172 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.100 | – |
| n_boxes | 1 | 392 | 392 | 0.2057 | [0.174, 0.240] | 0.2057 | – | 0.485 |
| n_boxes | 2 | 490 | 490 | 0.3570 | [0.312, 0.401] | 0.3570 | – | 0.741 |
| n_boxes | 3+ | 18 | 18 | 0.1001 | [0.043, 0.170] | 0.1001 | – | 0.722 |
