### baseline_s1 — val

mAP **0.1829** [0.1600, 0.2049] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4002, scored 1471

| metric | value |
|---|---|
| image_roc_auc | 0.8809 |
| image_pr_auc | 0.6967 |
| sensitivity | 0.7544 |
| specificity | 0.8159 |
| matched_iou | 0.6305 |
| mAP on positives only | 0.2989 |
| FP-image rate on negatives | 0.1841 (571/3102) |
| loss: FP on negatives | 0.3882 |
| loss: missed positives (no box) | 0.1502 |
| loss: localization on positives | 0.2787 |
| oracle gating @run thr | 0.2989 |
| oracle gating @best thr (0.15) | 0.3377 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2025 | [0.180, 0.230] | 0.3284 | 0.385 | 0.825 |
| view | PA | 2176 | 202 | 0.1172 | [0.091, 0.145] | 0.1967 | 0.069 | 0.510 |
| sex | F | 1730 | 376 | 0.1826 | [0.143, 0.216] | 0.3026 | 0.182 | 0.761 |
| sex | M | 2272 | 524 | 0.1830 | [0.157, 0.211] | 0.2962 | 0.185 | 0.750 |
| age_bucket | <20 | 337 | 125 | 0.2754 | [0.206, 0.326] | 0.3746 | 0.212 | 0.896 |
| age_bucket | 20-40 | 1087 | 265 | 0.1797 | [0.142, 0.218] | 0.2957 | 0.208 | 0.747 |
| age_bucket | 40-60 | 1598 | 334 | 0.1937 | [0.156, 0.228] | 0.3144 | 0.165 | 0.737 |
| age_bucket | 60+ | 980 | 176 | 0.1201 | [0.094, 0.145] | 0.2203 | 0.183 | 0.699 |
| cls | Lung Opacity | 900 | 900 | 0.2989 | [0.271, 0.324] | 0.2989 | – | 0.754 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.314 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.011 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.184 | – |
| n_boxes | 1 | 392 | 392 | 0.2144 | [0.182, 0.245] | 0.2144 | – | 0.622 |
| n_boxes | 2 | 490 | 490 | 0.3720 | [0.335, 0.407] | 0.3720 | – | 0.853 |
| n_boxes | 3+ | 18 | 18 | 0.1487 | [0.082, 0.221] | 0.1487 | – | 0.944 |
