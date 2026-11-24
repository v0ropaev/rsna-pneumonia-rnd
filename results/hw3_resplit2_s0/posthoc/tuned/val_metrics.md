### hw3_resplit2_s0:tuned — val

mAP **0.2166** [0.1881, 0.2457] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1157

| metric | value |
|---|---|
| image_roc_auc | 0.8934 |
| image_pr_auc | 0.7230 |
| sensitivity | 0.6026 |
| specificity | 0.9190 |
| matched_iou | 0.6473 |
| mAP on positives only | 0.2766 |
| FP-image rate on negatives | 0.0810 (251/3098) |
| loss: FP on negatives | 0.2169 |
| loss: missed positives (no box) | 0.3111 |
| loss: localization on positives | 0.2553 |
| oracle gating @run thr | 0.2766 |
| oracle gating @best thr (0.05) | 0.3278 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1829 | 703 | 0.2432 | [0.216, 0.278] | 0.3127 | 0.179 | 0.680 |
| view | PA | 2175 | 203 | 0.1217 | [0.085, 0.155] | 0.1517 | 0.025 | 0.335 |
| sex | F | 1724 | 376 | 0.2123 | [0.162, 0.257] | 0.2795 | 0.088 | 0.593 |
| sex | M | 2280 | 530 | 0.2199 | [0.181, 0.252] | 0.2746 | 0.075 | 0.609 |
| age_bucket | <20 | 241 | 78 | 0.3219 | [0.202, 0.423] | 0.3755 | 0.080 | 0.718 |
| age_bucket | 20-40 | 1120 | 261 | 0.2202 | [0.175, 0.266] | 0.2792 | 0.081 | 0.625 |
| age_bucket | 40-60 | 1711 | 400 | 0.2214 | [0.174, 0.267] | 0.2862 | 0.089 | 0.620 |
| age_bucket | 60+ | 932 | 167 | 0.1560 | [0.114, 0.199] | 0.2036 | 0.067 | 0.473 |
| cls | Lung Opacity | 906 | 906 | 0.2766 | [0.246, 0.309] | 0.2766 | – | 0.603 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.142 | – |
| cls | Normal | 1325 | 0 | – | [–, –] | – | 0.000 | – |
| n_boxes | 0 | 3098 | 0 | 0.0000 | [0.000, 0.000] | – | 0.081 | – |
| n_boxes | 1 | 393 | 393 | 0.1741 | [0.147, 0.205] | 0.1741 | – | 0.468 |
| n_boxes | 2 | 491 | 491 | 0.3647 | [0.320, 0.409] | 0.3647 | – | 0.707 |
| n_boxes | 3+ | 22 | 22 | 0.1441 | [0.084, 0.238] | 0.1441 | – | 0.682 |
