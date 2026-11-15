### full_s2 — val

mAP **0.2183** [0.1874, 0.2486] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4002, scored 1089

| metric | value |
|---|---|
| image_roc_auc | 0.8951 |
| image_pr_auc | 0.7256 |
| sensitivity | 0.5700 |
| specificity | 0.9391 |
| matched_iou | 0.6470 |
| mAP on positives only | 0.2641 |
| FP-image rate on negatives | 0.0609 (189/3102) |
| loss: FP on negatives | 0.1736 |
| loss: missed positives (no box) | 0.3554 |
| loss: localization on positives | 0.2528 |
| oracle gating @run thr | 0.2641 |
| oracle gating @best thr (0.05) | 0.3212 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2452 | [0.207, 0.277] | 0.2979 | 0.133 | 0.649 |
| view | PA | 2176 | 202 | 0.1234 | [0.087, 0.161] | 0.1473 | 0.020 | 0.297 |
| sex | F | 1730 | 376 | 0.2277 | [0.174, 0.273] | 0.2792 | 0.063 | 0.577 |
| sex | M | 2272 | 524 | 0.2114 | [0.175, 0.250] | 0.2533 | 0.059 | 0.565 |
| age_bucket | <20 | 337 | 125 | 0.3059 | [0.207, 0.384] | 0.3647 | 0.113 | 0.760 |
| age_bucket | 20-40 | 1087 | 265 | 0.2194 | [0.168, 0.271] | 0.2657 | 0.068 | 0.562 |
| age_bucket | 40-60 | 1598 | 334 | 0.2352 | [0.188, 0.287] | 0.2823 | 0.053 | 0.584 |
| age_bucket | 60+ | 980 | 176 | 0.1258 | [0.081, 0.157] | 0.1558 | 0.052 | 0.420 |
| cls | Lung Opacity | 900 | 900 | 0.2641 | [0.230, 0.299] | 0.2641 | – | 0.570 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.106 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.061 | – |
| n_boxes | 1 | 392 | 392 | 0.1591 | [0.133, 0.188] | 0.1591 | – | 0.421 |
| n_boxes | 2 | 490 | 490 | 0.3517 | [0.300, 0.400] | 0.3517 | – | 0.682 |
| n_boxes | 3+ | 18 | 18 | 0.1664 | [0.085, 0.256] | 0.1664 | – | 0.778 |
