### hw3_leak_s0:tuned — val

mAP **0.2119** [0.1823, 0.2418] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 3308, scored 860

| metric | value |
|---|---|
| image_roc_auc | 0.8958 |
| image_pr_auc | 0.7129 |
| sensitivity | 0.5965 |
| specificity | 0.9312 |
| matched_iou | 0.6425 |
| mAP on positives only | 0.2684 |
| FP-image rate on negatives | 0.0688 (181/2629) |
| loss: FP on negatives | 0.2105 |
| loss: missed positives (no box) | 0.3186 |
| loss: localization on positives | 0.2590 |
| oracle gating @run thr | 0.2684 |
| oracle gating @best thr (0.05) | 0.3122 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1428 | 516 | 0.2332 | [0.200, 0.269] | 0.3006 | 0.163 | 0.674 |
| view | PA | 1880 | 163 | 0.1393 | [0.102, 0.177] | 0.1666 | 0.019 | 0.350 |
| sex | F | 1447 | 287 | 0.2161 | [0.162, 0.272] | 0.2673 | 0.059 | 0.578 |
| sex | M | 1861 | 392 | 0.2090 | [0.170, 0.246] | 0.2692 | 0.077 | 0.610 |
| age_bucket | <20 | 273 | 87 | 0.2717 | [0.185, 0.330] | 0.3311 | 0.102 | 0.770 |
| age_bucket | 20-40 | 919 | 209 | 0.2061 | [0.149, 0.252] | 0.2682 | 0.089 | 0.603 |
| age_bucket | 40-60 | 1310 | 245 | 0.2501 | [0.196, 0.300] | 0.3103 | 0.055 | 0.612 |
| age_bucket | 60+ | 806 | 138 | 0.1201 | [0.079, 0.149] | 0.1549 | 0.060 | 0.449 |
| cls | Lung Opacity | 679 | 679 | 0.2684 | [0.234, 0.301] | 0.2684 | – | 0.596 |
| cls | No Lung Opacity / Not Normal | 1431 | 0 | 0.0000 | [0.000, 0.000] | – | 0.124 | – |
| cls | Normal | 1198 | 0 | 0.0000 | [0.000, 0.000] | – | 0.003 | – |
| n_boxes | 0 | 2629 | 0 | 0.0000 | [0.000, 0.000] | – | 0.069 | – |
| n_boxes | 1 | 308 | 308 | 0.1624 | [0.129, 0.195] | 0.1624 | – | 0.445 |
| n_boxes | 2 | 357 | 357 | 0.3634 | [0.311, 0.409] | 0.3634 | – | 0.717 |
| n_boxes | 3+ | 14 | 14 | 0.1796 | [0.112, 0.247] | 0.1796 | – | 0.857 |
