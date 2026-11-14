### baseline_s0 — val

mAP **0.1865** [0.1630, 0.2107] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4002, scored 1494

| metric | value |
|---|---|
| image_roc_auc | 0.8781 |
| image_pr_auc | 0.6821 |
| sensitivity | 0.7633 |
| specificity | 0.8085 |
| matched_iou | 0.6270 |
| mAP on positives only | 0.3095 |
| FP-image rate on negatives | 0.1915 (594/3102) |
| loss: FP on negatives | 0.3976 |
| loss: missed positives (no box) | 0.1426 |
| loss: localization on positives | 0.2734 |
| oracle gating @run thr | 0.3095 |
| oracle gating @best thr (0.15) | 0.3506 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2082 | [0.179, 0.236] | 0.3365 | 0.381 | 0.831 |
| view | PA | 2176 | 202 | 0.1194 | [0.094, 0.145] | 0.2164 | 0.083 | 0.530 |
| sex | F | 1730 | 376 | 0.1822 | [0.139, 0.215] | 0.3140 | 0.201 | 0.742 |
| sex | M | 2272 | 524 | 0.1898 | [0.161, 0.219] | 0.3064 | 0.184 | 0.779 |
| age_bucket | <20 | 337 | 125 | 0.2880 | [0.208, 0.350] | 0.3893 | 0.208 | 0.880 |
| age_bucket | 20-40 | 1087 | 265 | 0.1913 | [0.152, 0.234] | 0.3176 | 0.213 | 0.751 |
| age_bucket | 40-60 | 1598 | 334 | 0.1987 | [0.159, 0.240] | 0.3231 | 0.165 | 0.784 |
| age_bucket | 60+ | 980 | 176 | 0.1106 | [0.083, 0.135] | 0.2150 | 0.206 | 0.659 |
| cls | Lung Opacity | 900 | 900 | 0.3095 | [0.279, 0.338] | 0.3095 | – | 0.763 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.318 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.023 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.191 | – |
| n_boxes | 1 | 392 | 392 | 0.2462 | [0.213, 0.278] | 0.2462 | – | 0.643 |
| n_boxes | 2 | 490 | 490 | 0.3650 | [0.320, 0.406] | 0.3650 | – | 0.851 |
| n_boxes | 3+ | 18 | 18 | 0.1795 | [0.102, 0.261] | 0.1795 | – | 1.000 |
