### full_s0:tuned — val

mAP **0.2200** [0.1916, 0.2465] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1178

| metric | value |
|---|---|
| image_roc_auc | 0.8926 |
| image_pr_auc | 0.7212 |
| sensitivity | 0.6467 |
| specificity | 0.9104 |
| matched_iou | 0.6400 |
| mAP on positives only | 0.2880 |
| FP-image rate on negatives | 0.0896 (278/3102) |
| loss: FP on negatives | 0.2360 |
| loss: missed positives (no box) | 0.2699 |
| loss: localization on positives | 0.2740 |
| oracle gating @run thr | 0.2880 |
| oracle gating @best thr (0.05) | 0.3106 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2422 | [0.212, 0.272] | 0.3189 | 0.196 | 0.719 |
| view | PA | 2176 | 202 | 0.1413 | [0.108, 0.175] | 0.1812 | 0.029 | 0.396 |
| sex | F | 1730 | 376 | 0.2171 | [0.160, 0.259] | 0.2876 | 0.090 | 0.625 |
| sex | M | 2272 | 524 | 0.2221 | [0.192, 0.254] | 0.2882 | 0.089 | 0.662 |
| age_bucket | <20 | 337 | 125 | 0.2922 | [0.213, 0.351] | 0.3670 | 0.151 | 0.784 |
| age_bucket | 20-40 | 1087 | 265 | 0.2155 | [0.165, 0.266] | 0.2797 | 0.096 | 0.642 |
| age_bucket | 40-60 | 1598 | 334 | 0.2421 | [0.197, 0.286] | 0.3124 | 0.077 | 0.668 |
| age_bucket | 60+ | 980 | 176 | 0.1416 | [0.099, 0.176] | 0.1979 | 0.087 | 0.517 |
| cls | Lung Opacity | 900 | 900 | 0.2880 | [0.255, 0.321] | 0.2880 | – | 0.647 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.155 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.090 | – |
| n_boxes | 1 | 392 | 392 | 0.1760 | [0.149, 0.202] | 0.1760 | – | 0.492 |
| n_boxes | 2 | 490 | 490 | 0.3813 | [0.335, 0.422] | 0.3813 | – | 0.761 |
| n_boxes | 3+ | 18 | 18 | 0.1850 | [0.106, 0.273] | 0.1850 | – | 0.889 |
