### baseline_s2 — val

mAP **0.1956** [0.1690, 0.2212] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4002, scored 1303

| metric | value |
|---|---|
| image_roc_auc | 0.8841 |
| image_pr_auc | 0.7019 |
| sensitivity | 0.6778 |
| specificity | 0.8701 |
| matched_iou | 0.6333 |
| mAP on positives only | 0.2832 |
| FP-image rate on negatives | 0.1299 (403/3102) |
| loss: FP on negatives | 0.3093 |
| loss: missed positives (no box) | 0.2226 |
| loss: localization on positives | 0.2725 |
| oracle gating @run thr | 0.2832 |
| oracle gating @best thr (0.15) | 0.3538 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2216 | [0.191, 0.254] | 0.3127 | 0.254 | 0.751 |
| view | PA | 2176 | 202 | 0.1150 | [0.085, 0.144] | 0.1811 | 0.059 | 0.426 |
| sex | F | 1730 | 376 | 0.1972 | [0.154, 0.236] | 0.2952 | 0.138 | 0.678 |
| sex | M | 2272 | 524 | 0.1944 | [0.161, 0.229] | 0.2746 | 0.124 | 0.677 |
| age_bucket | <20 | 337 | 125 | 0.2787 | [0.196, 0.338] | 0.3500 | 0.151 | 0.808 |
| age_bucket | 20-40 | 1087 | 265 | 0.1990 | [0.155, 0.240] | 0.2875 | 0.144 | 0.660 |
| age_bucket | 40-60 | 1598 | 334 | 0.2155 | [0.173, 0.259] | 0.3110 | 0.117 | 0.704 |
| age_bucket | 60+ | 980 | 176 | 0.1105 | [0.084, 0.144] | 0.1764 | 0.131 | 0.562 |
| cls | Lung Opacity | 900 | 900 | 0.2832 | [0.251, 0.311] | 0.2832 | – | 0.678 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.225 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.004 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.130 | – |
| n_boxes | 1 | 392 | 392 | 0.2258 | [0.191, 0.259] | 0.2258 | – | 0.541 |
| n_boxes | 2 | 490 | 490 | 0.3352 | [0.288, 0.378] | 0.3352 | – | 0.780 |
| n_boxes | 3+ | 18 | 18 | 0.1157 | [0.059, 0.184] | 0.1157 | – | 0.889 |
