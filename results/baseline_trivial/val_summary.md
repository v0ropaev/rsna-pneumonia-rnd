## Trivial baselines — val (4002 images)

Prior boxes (k-means k=2 on train positives, xywh px): [[213.0, 374.2, 213.5, 314.4], [601.6, 363.4, 224.8, 346.5]]

| variant | thr | mAP | 95% CI | scored | mAP pos | FP-img rate | img AUC | matched IoU | oracle gating |
|---|---|---|---|---|---|---|---|---|---|
| empty | 0.05 | 0.0000 | [0.0000, 0.0000] | 900 | 0.0000 | 0.000 | 0.500 | – | 0.0000 |
| prior_boxes | 0.05 | 0.0217 | [0.0192, 0.0242] | 4002 | 0.0964 | 1.000 | 0.500 | 0.520 | 0.0964 |
| prior_boxes_ap | 0.05 | 0.0347 | [0.0305, 0.0393] | 2028 | 0.0781 | 0.364 | 0.706 | 0.521 | 0.0781 |
