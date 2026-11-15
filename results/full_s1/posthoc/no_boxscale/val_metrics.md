### full_s1:no_boxscale — val

mAP **0.2194** [0.1900, 0.2478] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4002, scored 1108

| metric | value |
|---|---|
| image_roc_auc | 0.8937 |
| image_pr_auc | 0.7176 |
| sensitivity | 0.5756 |
| specificity | 0.9329 |
| matched_iou | 0.6449 |
| mAP on positives only | 0.2700 |
| FP-image rate on negatives | 0.0671 (208/3102) |
| loss: FP on negatives | 0.1877 |
| loss: missed positives (no box) | 0.3448 |
| loss: localization on positives | 0.2482 |
| oracle gating @run thr | 0.2700 |
| oracle gating @best thr (0.05) | 0.3186 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2428 | [0.208, 0.276] | 0.2992 | 0.144 | 0.639 |
| view | PA | 2176 | 202 | 0.1380 | [0.102, 0.171] | 0.1695 | 0.023 | 0.356 |
| sex | F | 1730 | 376 | 0.2273 | [0.173, 0.270] | 0.2847 | 0.070 | 0.580 |
| sex | M | 2272 | 524 | 0.2135 | [0.178, 0.252] | 0.2595 | 0.065 | 0.573 |
| age_bucket | <20 | 337 | 125 | 0.3141 | [0.232, 0.370] | 0.3744 | 0.113 | 0.768 |
| age_bucket | 20-40 | 1087 | 265 | 0.2163 | [0.166, 0.267] | 0.2628 | 0.069 | 0.566 |
| age_bucket | 40-60 | 1598 | 334 | 0.2342 | [0.184, 0.287] | 0.2889 | 0.062 | 0.578 |
| age_bucket | 60+ | 980 | 176 | 0.1339 | [0.088, 0.165] | 0.1711 | 0.061 | 0.449 |
| cls | Lung Opacity | 900 | 900 | 0.2700 | [0.236, 0.302] | 0.2700 | – | 0.576 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.116 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.067 | – |
| n_boxes | 1 | 392 | 392 | 0.1608 | [0.133, 0.191] | 0.1608 | – | 0.418 |
| n_boxes | 2 | 490 | 490 | 0.3610 | [0.309, 0.401] | 0.3610 | – | 0.692 |
| n_boxes | 3+ | 18 | 18 | 0.1744 | [0.097, 0.260] | 0.1744 | – | 0.833 |
