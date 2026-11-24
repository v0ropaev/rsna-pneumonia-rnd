### hw3_resplit2_s0 — val

mAP **0.2137** [0.1858, 0.2424] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1157

| metric | value |
|---|---|
| image_roc_auc | 0.8934 |
| image_pr_auc | 0.7230 |
| sensitivity | 0.6026 |
| specificity | 0.9190 |
| matched_iou | 0.6437 |
| mAP on positives only | 0.2729 |
| FP-image rate on negatives | 0.0810 (251/3098) |
| loss: FP on negatives | 0.2169 |
| loss: missed positives (no box) | 0.3111 |
| loss: localization on positives | 0.2582 |
| oracle gating @run thr | 0.2729 |
| oracle gating @best thr (0.05) | 0.3237 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1829 | 703 | 0.2396 | [0.212, 0.274] | 0.3081 | 0.179 | 0.680 |
| view | PA | 2175 | 203 | 0.1213 | [0.086, 0.154] | 0.1512 | 0.025 | 0.335 |
| sex | F | 1724 | 376 | 0.2091 | [0.160, 0.253] | 0.2752 | 0.088 | 0.593 |
| sex | M | 2280 | 530 | 0.2172 | [0.179, 0.249] | 0.2713 | 0.075 | 0.609 |
| age_bucket | <20 | 241 | 78 | 0.3152 | [0.198, 0.412] | 0.3678 | 0.080 | 0.718 |
| age_bucket | 20-40 | 1120 | 261 | 0.2179 | [0.172, 0.263] | 0.2763 | 0.081 | 0.625 |
| age_bucket | 40-60 | 1711 | 400 | 0.2185 | [0.172, 0.262] | 0.2825 | 0.089 | 0.620 |
| age_bucket | 60+ | 932 | 167 | 0.1536 | [0.112, 0.195] | 0.2005 | 0.067 | 0.473 |
| cls | Lung Opacity | 906 | 906 | 0.2729 | [0.243, 0.304] | 0.2729 | – | 0.603 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.142 | – |
| cls | Normal | 1325 | 0 | – | [–, –] | – | 0.000 | – |
| n_boxes | 0 | 3098 | 0 | 0.0000 | [0.000, 0.000] | – | 0.081 | – |
| n_boxes | 1 | 393 | 393 | 0.1755 | [0.148, 0.206] | 0.1755 | – | 0.468 |
| n_boxes | 2 | 491 | 491 | 0.3567 | [0.312, 0.400] | 0.3567 | – | 0.707 |
| n_boxes | 3+ | 22 | 22 | 0.1443 | [0.082, 0.233] | 0.1443 | – | 0.682 |
