### b_aug_s1:tuned — val

mAP **0.2099** [0.1796, 0.2403] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.30; images 4002, scored 1119

| metric | value |
|---|---|
| image_roc_auc | 0.8869 |
| image_pr_auc | 0.7083 |
| sensitivity | 0.5667 |
| specificity | 0.9294 |
| matched_iou | 0.6460 |
| mAP on positives only | 0.2610 |
| FP-image rate on negatives | 0.0706 (219/3102) |
| loss: FP on negatives | 0.1957 |
| loss: missed positives (no box) | 0.3485 |
| loss: localization on positives | 0.2459 |
| oracle gating @run thr | 0.2610 |
| oracle gating @best thr (0.15) | 0.3795 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2335 | [0.198, 0.269] | 0.2904 | 0.151 | 0.626 |
| view | PA | 2176 | 202 | 0.1282 | [0.096, 0.159] | 0.1592 | 0.025 | 0.361 |
| sex | F | 1730 | 376 | 0.2240 | [0.166, 0.266] | 0.2806 | 0.070 | 0.569 |
| sex | M | 2272 | 524 | 0.1996 | [0.163, 0.242] | 0.2468 | 0.071 | 0.565 |
| age_bucket | <20 | 337 | 125 | 0.2908 | [0.210, 0.349] | 0.3513 | 0.123 | 0.800 |
| age_bucket | 20-40 | 1087 | 265 | 0.2238 | [0.169, 0.277] | 0.2719 | 0.069 | 0.551 |
| age_bucket | 40-60 | 1598 | 334 | 0.2220 | [0.168, 0.274] | 0.2764 | 0.065 | 0.584 |
| age_bucket | 60+ | 980 | 176 | 0.1155 | [0.075, 0.147] | 0.1509 | 0.067 | 0.392 |
| cls | Lung Opacity | 900 | 900 | 0.2610 | [0.227, 0.294] | 0.2610 | – | 0.567 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.124 | – |
| cls | Normal | 1331 | 0 | – | [–, –] | – | 0.000 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.071 | – |
| n_boxes | 1 | 392 | 392 | 0.1861 | [0.151, 0.221] | 0.1861 | – | 0.434 |
| n_boxes | 2 | 490 | 490 | 0.3256 | [0.273, 0.370] | 0.3256 | – | 0.665 |
| n_boxes | 3+ | 18 | 18 | 0.1325 | [0.057, 0.211] | 0.1325 | – | 0.778 |
