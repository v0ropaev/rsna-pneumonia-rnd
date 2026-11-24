### hw3_frac50_s1 — val

mAP **0.2032** [0.1769, 0.2297] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1239

| metric | value |
|---|---|
| image_roc_auc | 0.8874 |
| image_pr_auc | 0.7112 |
| sensitivity | 0.6644 |
| specificity | 0.8907 |
| matched_iou | 0.6272 |
| mAP on positives only | 0.2797 |
| FP-image rate on negatives | 0.1093 (339/3102) |
| loss: FP on negatives | 0.2736 |
| loss: missed positives (no box) | 0.2437 |
| loss: localization on positives | 0.2794 |
| oracle gating @run thr | 0.2797 |
| oracle gating @best thr (0.05) | 0.3108 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2324 | [0.203, 0.263] | 0.3189 | 0.230 | 0.745 |
| view | PA | 2176 | 202 | 0.1038 | [0.076, 0.131] | 0.1444 | 0.040 | 0.386 |
| sex | F | 1730 | 376 | 0.2041 | [0.154, 0.249] | 0.2856 | 0.111 | 0.652 |
| sex | M | 2272 | 524 | 0.2025 | [0.170, 0.233] | 0.2756 | 0.108 | 0.674 |
| age_bucket | <20 | 337 | 125 | 0.2792 | [0.195, 0.342] | 0.3551 | 0.160 | 0.808 |
| age_bucket | 20-40 | 1087 | 265 | 0.2040 | [0.161, 0.246] | 0.2763 | 0.114 | 0.672 |
| age_bucket | 40-60 | 1598 | 334 | 0.2201 | [0.173, 0.269] | 0.3071 | 0.104 | 0.665 |
| age_bucket | 60+ | 980 | 176 | 0.1238 | [0.091, 0.148] | 0.1793 | 0.098 | 0.551 |
| cls | Lung Opacity | 900 | 900 | 0.2797 | [0.249, 0.313] | 0.2797 | – | 0.664 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.190 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.002 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.109 | – |
| n_boxes | 1 | 392 | 392 | 0.1588 | [0.136, 0.185] | 0.1588 | – | 0.500 |
| n_boxes | 2 | 490 | 490 | 0.3802 | [0.336, 0.424] | 0.3802 | – | 0.788 |
| n_boxes | 3+ | 18 | 18 | 0.1793 | [0.098, 0.272] | 0.1793 | – | 0.889 |
