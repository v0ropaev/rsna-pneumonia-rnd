### hw3_frac10_s0:tuned — val

mAP **0.1527** [0.1310, 0.1726] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.10; images 4002, scored 1240

| metric | value |
|---|---|
| image_roc_auc | 0.8692 |
| image_pr_auc | 0.6750 |
| sensitivity | 0.6278 |
| specificity | 0.8904 |
| matched_iou | 0.5909 |
| mAP on positives only | 0.2103 |
| FP-image rate on negatives | 0.1096 (340/3102) |
| loss: FP on negatives | 0.2742 |
| loss: missed positives (no box) | 0.2702 |
| loss: localization on positives | 0.3030 |
| oracle gating @run thr | 0.2103 |
| oracle gating @best thr (0.05) | 0.2341 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.1729 | [0.149, 0.198] | 0.2412 | 0.245 | 0.718 |
| view | PA | 2176 | 202 | 0.0787 | [0.053, 0.107] | 0.1036 | 0.032 | 0.317 |
| sex | F | 1730 | 376 | 0.1569 | [0.121, 0.188] | 0.2221 | 0.115 | 0.646 |
| sex | M | 2272 | 524 | 0.1495 | [0.126, 0.178] | 0.2019 | 0.105 | 0.615 |
| age_bucket | <20 | 337 | 125 | 0.2190 | [0.146, 0.277] | 0.2890 | 0.189 | 0.784 |
| age_bucket | 20-40 | 1087 | 265 | 0.1507 | [0.116, 0.187] | 0.2075 | 0.122 | 0.608 |
| age_bucket | 40-60 | 1598 | 334 | 0.1615 | [0.128, 0.193] | 0.2200 | 0.096 | 0.638 |
| age_bucket | 60+ | 980 | 176 | 0.0969 | [0.066, 0.122] | 0.1404 | 0.098 | 0.528 |
| cls | Lung Opacity | 900 | 900 | 0.2103 | [0.184, 0.236] | 0.2103 | – | 0.628 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.189 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.005 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.110 | – |
| n_boxes | 1 | 392 | 392 | 0.1025 | [0.080, 0.125] | 0.1025 | – | 0.459 |
| n_boxes | 2 | 490 | 490 | 0.3008 | [0.266, 0.333] | 0.3008 | – | 0.759 |
| n_boxes | 3+ | 18 | 18 | 0.0959 | [0.044, 0.159] | 0.0959 | – | 0.722 |
