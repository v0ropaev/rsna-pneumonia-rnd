### full_s2:no_gating — val

mAP **0.2160** [0.1897, 0.2414] (bootstrap 95% CI, resampling unit: nih_patient) at score thr 0.25; images 4002, scored 1362

| metric | value |
|---|---|
| image_roc_auc | 0.8951 |
| image_pr_auc | 0.7256 |
| sensitivity | 0.7233 |
| specificity | 0.8511 |
| matched_iou | 0.6441 |
| mAP on positives only | 0.3269 |
| FP-image rate on negatives | 0.1489 (462/3102) |
| loss: FP on negatives | 0.3392 |
| loss: missed positives (no box) | 0.1828 |
| loss: localization on positives | 0.2620 |
| oracle gating @run thr | 0.3269 |
| oracle gating @best thr (0.15) | 0.3778 |

| slice | value | n | n_pos | mAP | 95% CI | mAP pos | FP-img rate | sens |
|---|---|---|---|---|---|---|---|---|
| view | AP | 1826 | 698 | 0.2399 | [0.208, 0.268] | 0.3536 | 0.293 | 0.782 |
| view | PA | 2176 | 202 | 0.1423 | [0.113, 0.172] | 0.2345 | 0.066 | 0.520 |
| sex | F | 1730 | 376 | 0.2146 | [0.168, 0.253] | 0.3322 | 0.152 | 0.723 |
| sex | M | 2272 | 524 | 0.2170 | [0.186, 0.253] | 0.3231 | 0.146 | 0.723 |
| age_bucket | <20 | 337 | 125 | 0.3029 | [0.214, 0.369] | 0.3950 | 0.179 | 0.848 |
| age_bucket | 20-40 | 1087 | 265 | 0.2249 | [0.175, 0.269] | 0.3403 | 0.165 | 0.740 |
| age_bucket | 40-60 | 1598 | 334 | 0.2298 | [0.190, 0.274] | 0.3440 | 0.131 | 0.716 |
| age_bucket | 60+ | 980 | 176 | 0.1334 | [0.099, 0.160] | 0.2258 | 0.152 | 0.625 |
| cls | Lung Opacity | 900 | 900 | 0.3269 | [0.296, 0.356] | 0.3269 | – | 0.723 |
| cls | No Lung Opacity / Not Normal | 1771 | 0 | 0.0000 | [0.000, 0.000] | – | 0.256 | – |
| cls | Normal | 1331 | 0 | 0.0000 | [0.000, 0.000] | – | 0.006 | – |
| n_boxes | 0 | 3102 | 0 | 0.0000 | [0.000, 0.000] | – | 0.149 | – |
| n_boxes | 1 | 392 | 392 | 0.2509 | [0.217, 0.285] | 0.2509 | – | 0.592 |
| n_boxes | 2 | 490 | 490 | 0.3924 | [0.343, 0.436] | 0.3924 | – | 0.820 |
| n_boxes | 3+ | 18 | 18 | 0.1962 | [0.106, 0.296] | 0.1962 | – | 0.944 |
