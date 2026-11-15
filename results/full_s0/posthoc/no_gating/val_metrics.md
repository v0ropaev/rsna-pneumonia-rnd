### full_s0:no_gating — val

mAP **0.2117** [0.1860, 0.2370] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4002, scored 1340

| metric | value |
|---|---|
| image_roc_auc | 0.8926 |
| image_pr_auc | 0.7212 |
| sensitivity | 0.7122 |
| specificity | 0.8582 |
| matched_iou | 0.6405 |
| mAP on positives only | 0.3152 |
| FP-image rate on negatives | 0.1418 (440/3102) |
| loss: FP on negatives | 0.3284 |
| loss: missed positives (no box) | 0.1933 |
| loss: localization on positives | 0.2666 |
| oracle gating @run thr | 0.3152 |
| oracle gating @best thr (0.15) | 0.3733 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2356 | [0.206, 0.265] | 0.3413 | 0.277 | 0.778 |
| view | PA | 2176 | 202 | 0.1383 | [0.107, 0.165] | 0.2253 | 0.064 | 0.485 |
| sex | F | 1730 | 376 | 0.2097 | [0.159, 0.250] | 0.3168 | 0.142 | 0.697 |
| sex | M | 2272 | 524 | 0.2132 | [0.183, 0.246] | 0.3142 | 0.142 | 0.723 |
| age_bucket | <20 | 337 | 125 | 0.2928 | [0.209, 0.349] | 0.3817 | 0.179 | 0.832 |
| age_bucket | 20-40 | 1087 | 265 | 0.2170 | [0.169, 0.263] | 0.3185 | 0.151 | 0.694 |
| age_bucket | 40-60 | 1598 | 334 | 0.2256 | [0.184, 0.268] | 0.3371 | 0.131 | 0.740 |
| age_bucket | 60+ | 980 | 176 | 0.1351 | [0.102, 0.161] | 0.2218 | 0.141 | 0.602 |
| cls | Lung Opacity | 900 | 900 | 0.3152 | [0.284, 0.344] | 0.3152 | – | 0.712 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.243 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.007 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.142 | – |
| n_boxes | 1 | 392 | 392 | 0.2453 | [0.211, 0.279] | 0.2453 | – | 0.589 |
| n_boxes | 2 | 490 | 490 | 0.3769 | [0.331, 0.419] | 0.3769 | – | 0.806 |
| n_boxes | 3+ | 18 | 18 | 0.1605 | [0.094, 0.237] | 0.1605 | – | 0.833 |
