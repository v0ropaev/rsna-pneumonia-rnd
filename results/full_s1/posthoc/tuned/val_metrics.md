### full_s1:tuned — val

mAP **0.2196** [0.1900, 0.2490] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4002, scored 1108

| metric | value |
|---|---|
| image_roc_auc | 0.8937 |
| image_pr_auc | 0.7176 |
| sensitivity | 0.5756 |
| specificity | 0.9329 |
| matched_iou | 0.6416 |
| mAP on positives only | 0.2704 |
| FP-image rate on negatives | 0.0671 (208/3102) |
| loss: FP on negatives | 0.1877 |
| loss: missed positives (no box) | 0.3448 |
| loss: localization on positives | 0.2479 |
| oracle gating @run thr | 0.2704 |
| oracle gating @best thr (0.05) | 0.3183 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2436 | [0.208, 0.277] | 0.3001 | 0.144 | 0.639 |
| view | PA | 2176 | 202 | 0.1367 | [0.101, 0.170] | 0.1678 | 0.023 | 0.356 |
| sex | F | 1730 | 376 | 0.2270 | [0.171, 0.271] | 0.2844 | 0.070 | 0.580 |
| sex | M | 2272 | 524 | 0.2142 | [0.178, 0.252] | 0.2603 | 0.065 | 0.573 |
| age_bucket | <20 | 337 | 125 | 0.3125 | [0.230, 0.369] | 0.3725 | 0.113 | 0.768 |
| age_bucket | 20-40 | 1087 | 265 | 0.2168 | [0.166, 0.268] | 0.2634 | 0.069 | 0.566 |
| age_bucket | 40-60 | 1598 | 334 | 0.2346 | [0.183, 0.289] | 0.2894 | 0.062 | 0.578 |
| age_bucket | 60+ | 980 | 176 | 0.1347 | [0.088, 0.166] | 0.1722 | 0.061 | 0.449 |
| cls | Lung Opacity | 900 | 900 | 0.2704 | [0.235, 0.303] | 0.2704 | – | 0.576 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.116 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.067 | – |
| n_boxes | 1 | 392 | 392 | 0.1611 | [0.133, 0.192] | 0.1611 | – | 0.418 |
| n_boxes | 2 | 490 | 490 | 0.3609 | [0.309, 0.403] | 0.3609 | – | 0.692 |
| n_boxes | 3+ | 18 | 18 | 0.1868 | [0.109, 0.280] | 0.1868 | – | 0.833 |
