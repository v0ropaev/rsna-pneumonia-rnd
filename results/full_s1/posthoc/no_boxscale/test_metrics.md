### full_s1:no_boxscale — test

mAP **0.2224** [0.1751, 0.2717] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.15; images 4004, scored 1122

| metric | value |
|---|---|
| image_roc_auc | 0.8846 |
| image_pr_auc | 0.7255 |
| sensitivity | 0.5911 |
| specificity | 0.9285 |
| matched_iou | 0.6477 |
| mAP on positives only | 0.2773 |
| FP-image rate on negatives | 0.0715 (222/3104) |
| loss: FP on negatives | 0.1979 |
| loss: missed positives (no box) | 0.3280 |
| loss: localization on positives | 0.2517 |
| oracle gating @run thr | 0.2773 |
| oracle gating @best thr (0.05) | 0.3159 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1827 | 698 | 0.2526 | [0.193, 0.316] | 0.3116 | 0.144 | 0.662 |
| view | PA | 2177 | 202 | 0.1229 | [0.086, 0.161] | 0.1588 | 0.030 | 0.347 |
| sex | F | 1729 | 374 | 0.2089 | [0.164, 0.258] | 0.2653 | 0.075 | 0.602 |
| sex | M | 2275 | 526 | 0.2324 | [0.155, 0.304] | 0.2859 | 0.069 | 0.584 |
| age_bucket | <20 | 246 | 71 | 0.2220 | [0.165, 0.284] | 0.2595 | 0.069 | 0.620 |
| age_bucket | 20-40 | 949 | 249 | 0.2420 | [0.177, 0.286] | 0.3062 | 0.094 | 0.655 |
| age_bucket | 40-60 | 1767 | 363 | 0.2505 | [0.152, 0.358] | 0.3057 | 0.057 | 0.587 |
| age_bucket | 60+ | 1041 | 217 | 0.1564 | [0.113, 0.200] | 0.2025 | 0.078 | 0.516 |
| age_bucket | invalid | 1 | 0 | – | [–, –] | – | 0.000 | – |
| cls | Lung Opacity | 900 | 900 | 0.2773 | [0.222, 0.334] | 0.2773 | – | 0.591 |
| cls | No Lung Opacity / Not Normal | 1773 | 0 | 0.0000 | [0.000, 0.000] | – | 0.125 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.001 | – |
| n_boxes | 0 | 3104 | 0 | 0.0000 | [0.000, 0.000] | – | 0.072 | – |
| n_boxes | 1 | 390 | 390 | 0.1612 | [0.128, 0.189] | 0.1612 | – | 0.431 |
| n_boxes | 2 | 492 | 492 | 0.3764 | [0.291, 0.459] | 0.3764 | – | 0.715 |
| n_boxes | 3+ | 18 | 18 | 0.0855 | [0.043, 0.138] | 0.0855 | – | 0.667 |
