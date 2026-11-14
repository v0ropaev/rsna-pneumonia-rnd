# Research notes: RSNA Pneumonia Detection Challenge

Дата сбора: 2026-11-14. Источники пронумерованы как [S#], полный список в конце.
Пометки: **[проверено]** означает, что мы сами проверили по первоисточнику или на локальных данных;
**[не проверено]** означает, что утверждение известно со слов третьих лиц и мы его не воспроизводили.

## 0. Коротко: что из этого следует для протокола HW1/HW2

1. **Метрика.** Официальная страница [S1] и ответы хоста Kaggle [S2, S3] однозначно задают
   пороги IoU `0.40:0.05:0.75`, строгое `>`, формулу `TP/(TP+FP+FN)` на изображение и правило:
   изображения без GT **и** без предсказаний исключаются из среднего, а изображения без GT, но
   с ≥1 предсказанием получают 0 и учитываются. Порядок сопоставления боксов описан
   противоречиво (см. §1.4). На данных RSNA все варианты совпадают при t ≥ 0.5, и на практике
   выбор варианта на скор не влияет.
2. **Утечка по пациентам вполне реальна.** 26 684 train-снимка RSNA принадлежат **11 452**
   NIH-пациентам. У **4 355** пациентов больше одного снимка, и эти пациенты покрывают **19 587
   снимков (73.4 %)**. При случайном сплите 70/15/15 по `patientId` у **67.4 %** val-снимков в
   train окажется снимок того же человека. Поэтому сплит группируем по `nih_patient`
   (`data/external/nih_mapping.csv`, покрытие 100 %).
3. **Сжатие боксов (box shrinking)** дало топ-командам Kaggle больше всего: ×0.875 по w и h,
   +0.03–0.04 mAP на stage-1 LB. Но причина специфична для Kaggle-теста: GT там строился как
   пересечение боксов трёх читателей. Наш hold-out взят из `stage_2_train`, где снимки в
   основном single-read, поэтому большого выигрыша на нём ждать не стоит. Гипотезу для HW2
   стоит проверять честно: подбирать масштаб на val и проверять на test.
4. **Гейтинг классификатором (two-stage)** есть почти у всех топ-решений. Метрика бьёт по любому
   FP на негативном снимке (он даёт 0 в числитель и +1 в знаменатель), поэтому image-level
   классификатор, отсекающий боксы, — наиболее обоснованное улучшение для HW2.
5. **AP/PA — shortcut.** На локальном train доля позитивов 38.3 % на AP против 9.3 % на PA,
   ROC-AUC одного признака `view==AP` равен 0.706 [проверено]. Топ-команды метаданные не
   использовали; 2-е место прямо назвало это пограничной утечкой. Используем view только для
   стратификации и срезов, но не как признак.
6. **Ориентиры по скору.** Private LB (Kaggle-тест, 3000 triple-read снимков): 1-е место
   0.25475, 10-е 0.22497, медиана по 344 командам 0.148. Пустой сабмит и `sample_submission`
   дают 0.0. Наш внутренний test (single-read) с Kaggle-тестом **несопоставим** напрямую:
   разметка другая и превалентность другая (22 % против примерно 35 %).

---

## 1. Метрика соревнования

### 1.1 Официальный текст [S1] [проверено]

Страница Evaluation получена через внутренний API Kaggle (`competitions.PageService/ListPages`,
competitionId 10338). Дословная копия лежит в `data/external/kaggle_evaluation_page.md`. Ключевые
цитаты:

- *"The threshold values range from 0.4 to 0.75 with a step size of 0.05: (0.4, 0.45, 0.5, 0.55,
  0.6, 0.65, 0.7, 0.75). In other words, at a threshold of 0.5, a predicted object is considered a
  "hit" if its intersection over union with a ground truth object is **greater than** 0.5."*
- *"A true positive is counted when a single predicted object matches a ground truth object with
  an IoU **above** the threshold. A false positive indicates a predicted object had no associated
  ground truth object. A false negative indicates a ground truth object had no associated
  predicted object."*
- Точность на пороге: `TP(t) / (TP(t) + FP(t) + FN(t))`; AP изображения равна среднему по 8 порогам.
- *"**Important note:** if there are no ground truth objects at all for a given image, ANY number of
  predictions (false positives) will result in the image receiving a score of zero, and being
  included in the mean average precision."*
- *"Bounding boxes will be evaluated in order of their confidence levels ... boxes with higher
  confidence will be checked first for matches against solutions, which determines what boxes are
  considered true and false positives."* и *"In nearly all cases `confidence` will have **no**
  impact on scoring ... None of these edge cases are known to exist in the data set."*
- *"the score returned by the competition metric is the mean taken over the individual average
  precisions of each image in the test dataset."*
- Формат сабмита: `patientId,PredictionString` с элементами `confidence x y w h` (x, y — левый
  верхний угол, пиксели 1024×1024); пустая строка означает «нет боксов».

### 1.2 Разъяснения хоста (Phil Culliton, Kaggle) [проверено, это цитаты с форума]

- [S2] (discussion/64341, 2018-08-28/30): *"If there are zero ground truth boxes and zero
  predictions, it is omitted from the mean."* и *"If there are zero ground truth boxes and greater
  than zero predictions, a score of zero is added to the mean."*
- [S3] (discussion/64860, 2018-09-05): *"if the sample is a true negative with **no** predictions,
  then it is not counted in the mean. If *any* predictions are made, the whole sample counts as a 0
  and is counted in the mean."*
- [S3] (2018-09-10), про сопоставление: *"IoU is also taken into account. The predicted box with the
  highest IoU would be taken as the match regardless of confidence order. All ground truth boxes are
  scored against all predicted boxes."* и *"The one with the highest IoU will be scored. The rest
  will be marked as false positives."* Официальный код или псевдокод так и не опубликовали.
- Косвенная проверка правила исключения: пустой сабмит дал на LB ровно 0.0 (ZFTurbo, [S3]), а
  Kaggle-аккаунт `Julia Elliott` и ещё около 20 команд со sample submission имеют на private LB
  0.00000 [S14, S19]. Это согласуется с исключением пар «пусто/пусто». Если бы такие изображения
  получали 1.0, пустой сабмит набрал бы около 0.65 (доля негативов в stage-1 test примерно
  0.647 [S12]).

### 1.3 Широко используемая реализация участников (не официальная) [проверено, код прочитан]

Kernel Yicheng Chen *"mean-average-precision-metric"* [S4]. На него ссылаются 1-е и 3-е места;
дословные копии `map_iou` лежат в репозиториях 1-го места (i-pan), 2-го места (pdima,
tatigabru) и других. Логика:

```text
if len(gt)==0 and len(pred)==0: return None          # исключить
pred = pred sorted by score desc
for t in thresholds:
    for each gt box (в исходном порядке):              # внешний цикл по GT!
        первый ещё не занятый pred (по убыванию score) с IoU >= t  -> TP   # ">=", не ">"
        если нет -> FN
    FP = len(pred) - matched
```

### 1.4 Edge cases: сводная таблица и конфликты

| Случай | Официально [S1–S3] | Kernel [S4] | Решение для `metric.py` |
|---|---|---|---|
| Сетка порогов | 0.40…0.75, шаг 0.05 (8 штук) | то же | то же |
| Сравнение IoU с порогом | **строго `>`** ("greater than", "above") | `>=` | `>` по [S1]. **Конфликт** с [S4]; отличается только при IoU ровно равном t |
| GT=∅, pred=∅ | исключается из среднего | `None` (исключается) | `None` |
| GT=∅, pred≥1 | 0, учитывается (число FP неважно) | 0 (TP=0, FP>0) | 0 |
| GT≥1, pred=∅ | 0 (TP=0, FN>0) | 0 | 0 |
| Агрегация | среднее AP по учитываемым изображениям | `nanmean` | среднее по не-`None` |
| Порядок сопоставления | [S1]: боксы проверяются по убыванию confidence; [S3]: «берётся pred с максимальным IoU независимо от confidence» | внешний цикл по GT, первый подходящий pred по confidence | pred по убыванию score, каждый берёт свободный GT с максимальным IoU > t (как в SPEC) |
| Дубликаты (2 pred на 1 GT) | один TP, остальные FP | то же | то же |
| Вырожденные боксы (w·h=0) | не описано | `assert` (падает) | IoU=0, бокс считается FP |

**Почему конфликт по порядку на практике не важен** (наш вывод, математическая выкладка плюс
проверка на данных):

- В train GT-боксы одного снимка практически не пересекаются. Среди 3 398 снимков с ≥2 боксами
  хоть какое-то пересечение есть у 8, максимальный IoU между GT-боксами равен 0.055 [проверено].
- Если IoU(P, A) > 0.5, то |P∩A| > 0.5·|P|. Значит, при t ≥ 0.5 один предсказанный бокс не может
  превысить порог сразу с двумя непересекающимися GT. Тогда у каждого pred не больше одного
  GT-кандидата, конкуренции нет, и любой жадный вариант даёт одинаковые TP/FP/FN
  (TP = число GT, у которых есть хотя бы один кандидат).
- Расхождения возможны только при t ∈ {0.40, 0.45} и только когда один pred накрывает два
  соседних GT-бокса. Это редкий случай, и он влияет на 2 порога из 8.
- `>` против `>=` различаются лишь при IoU, точно равном порогу. Для float-предсказаний это
  практически исключено, а для целочисленных фиксированных боксов (prior-baseline) возможно.

**Рекомендация для `src/rsna/metric.py` и тестов:** основная реализация следует SPEC и [S1]
(`>`, жадно по score, свободный GT с максимальным IoU). В тест добавить kernel [S4] как
независимый эталон. Он должен совпадать со SPEC-вариантом на случайных данных без IoU, точно
равного порогу, и без pred, накрывающих два GT при t < 0.5. Отдельный тест на границу:
IoU ровно 0.5 при t=0.5 даёт FN+FP, а не TP.

### 1.5 Следствия семантики метрики (важно для бейзлайнов и бутстрапа)

- **Негативы могут только навредить** (mlandry, [S3]): верно пустой негатив не входит в
  знаменатель, а любой FP на негативе добавляет 0 в числитель и 1 в знаменатель. Поэтому
  выгоден консервативный порог по score и классификационный гейтинг.
- **Знаменатель зависит от модели.** Число учитываемых изображений определяется
  предсказаниями. Для бутстрапа корректно ресэмплить **весь** оцениваемый набор `image_ids`,
  включая исключённые, и в каждой реплике брать `nanmean`. Ресэмпл только учитываемых
  изображений фиксирует знаменатель и занижает дисперсию. Для `paired_bootstrap_diff` то же
  правило: общий ресэмпл по всем id и `nanmean` для каждой модели в каждой реплике. Это
  естественно обрабатывает изображения, исключённые у одной модели и учтённые у другой.
- Пустая модель даёт 0.0, а не NaN, потому что все позитивы учитываются с AP=0.
- Confidence влияет только на порядок сопоставления. Порог по score — гиперпараметр, его
  подбирают на val (`threshold_sweep`).

---

## 2. Маппинг RSNA → NIH ChestX-ray14

### 2.1 Где нашли и как скачали [проверено]

- Файл: `pneumonia-challenge-dataset-mappings_2018.json` [S16], URL
  `http://s3.amazonaws.com/east1.public.rsna.org/AI/2018/pneumonia-challenge-dataset-mappings_2018.json`.
  Размер 17 587 143 байт, SHA-256
  `803ce79e3bc9c66d3631738e91e62e1175730e98ad1415e8dc4d6292ba10bf27`.
- Через **HTTPS** с этой машины скачать не удалось: `curl: (35) LibreSSL SSL_connect:
  SSL_ERROR_SYSCALL` для `s3.amazonaws.com` и `east1.public.rsna.org.s3.amazonaws.com`.
  Через **HTTP** файл скачался (код 200). Целостность подтверждена содержательно: у всех
  26 684 train-снимков `SOPInstanceUID` и `StudyInstanceUID` из JSON совпали с DICOM-заголовками,
  несовпадений 0.
- Сам факт маппинга упоминается в Shih et al. 2019 [S6] (*"A mapping of the 30 000 examination
  dataset unique identifiers to the original NIH dataset is provided"*). Там же дана ссылка на
  страницу https://rsna.org/challenge-datasets/2018 (мы её не открывали).
- Исходный JSON лежит в `data/external/` и не версионируется (`data/external/*` в `.gitignore`).
  `scripts/download_data.sh` скачивает его, проверяет SHA-256 и пересобирает
  `data/external/nih_mapping.csv`. Сам `nih_mapping.csv` (1.6 MB) закоммичен как исключение в `.gitignore`.

### 2.2 Формат [проверено]

JSON — массив из 30 000 объектов с ключами:

| Поле | Смысл |
|---|---|
| `subset_img_id` | **RSNA `patientId`** (UUID, совпадает с именем `.dcm`) |
| `img_id` | имя файла NIH, например `00012773_000.png`; **NIH patient id = часть до `_`** (`00012773`), суффикс — номер исследования пациента |
| `orig_labels` | исходные NLP-метки NIH (например `["Infiltration","Effusion"]`) |
| `subset_init_label` | страта отбора: 0 = NIH `No Finding` (7 500), 1 = есть `Pneumonia`/`Infiltration`/`Consolidation` (15 000), 2 = прочее (7 500). Совпадает с описанием отбора в [S5, S6] [проверено кросс-табом] |
| `subset_group` | 0/1/2 (18 162 / 5 937 / 5 901), смысл не документирован [не проверено; возможно, группа читателей] |
| `StudyInstanceUID`, `SeriesInstanceUID`, `SOPInstanceUID` | DICOM UID в RSNA-файлах |
| `studyId`, `seriesId`, `instanceId` | ID MD.ai |

Join: `patientId` ↔ `subset_img_id`, затем `nih_patient = img_id.split("_")[0]`.

### 2.3 Покрытие и статистика [проверено на `data/raw/stage_2_train_labels.csv`]

- Train: 26 684 из 26 684 (100 %). Stage-2 test: 3 000 из 3 000. Ещё 316 записей JSON нет ни в
  train, ни в test: 30 000 − 29 684 (видимо, исключены из финального датасета; Shih [S6]
  сообщает о 29 894 снимках в финальной версии, точное расхождение не выясняли).
- По всем 30 000: 12 274 NIH-пациента, максимум 75 снимков на пациента. Это совпадает с [S6],
  то есть файл согласуется со статьёй.
- **По train (26 684 снимка):**
  - уникальных NIH-пациентов: **11 452**;
  - пациентов с >1 снимком: **4 355**; снимков у таких пациентов: **19 587 (73.4 %)**; максимум
    65 снимков на пациента;
  - распределение «снимков на пациента»: 1 → 7 097, 2 → 1 811, 3 → 924, 4 → 447, 5 → 282, …, 64, 65;
  - у 1 726 из 4 355 многоснимковых пациентов есть и позитивные, и негативные снимки; у 107 все
    снимки позитивны;
  - у 2 236 многоснимковых пациентов есть и AP-, и PA-снимки.
- **Симуляция утечки:** при случайном 70/15/15 сплите по `patientId` (seed 42) у 67.4 % val-снимков
  тот же NIH-пациент есть в train.
- **Пересечение train↔Kaggle stage-2 test:** 1 575 из 2 356 NIH-пациентов теста есть в train, это
  2 203 из 3 000 test-снимков. Значит, на Kaggle LB тоже была межпациентная утечка. Для
  сравнения с LB это контекст, на наш протокол это не влияет.

Файл `data/external/nih_mapping.csv`: колонки `patientId,nih_image,nih_patient`, 26 684 строки,
порядок как первое появление `patientId` в `stage_2_train_labels.csv`. `nih_patient` хранится как
строка с ведущими нулями. При чтении pandas нужен `dtype={"nih_patient": str}`, иначе получится
int, что для группировки тоже корректно, но нули потеряются.

### 2.4 Следствия для сплита

- Группировать train/val/test и CV-фолды по `nih_patient` (например
  `StratifiedGroupKFold`/`GroupShuffleSplit` со стратификацией по `cls × min(n_boxes,3)` и view).
  Без этого val/test окажутся оптимистично смещены: модель может «узнавать» пациента по анатомии
  и катетерам.
- `orig_labels` и `subset_init_label` — NIH-метки, сильно коррелирующие с target. Доля позитивов
  при `subset_init_label` = 1/2/0: 32.6 % / 16.5 % / 8.3 % [проверено]. **Как признаки их не
  использовать**: хост прямо запретил внешние метки для теста [S11]. Допустимо разве что
  стратифицировать по ним сплит.

---

## 3. Инсайты из решений и статей

### 3.1 Как размечали данные, и почему train и test различаются [S5, S6] [проверено, это цитаты]

- 30 000 снимков NIH CXR14: 15 000 с pneumonia-like метками (`Pneumonia`, `Infiltration`,
  `Consolidation`), 7 500 `No Finding`, 7 500 прочих.
- Train: 6 радиологов RSNA, каждый снимок читал **один** человек (5 000 на читателя).
  Инструкция: боксы *"as small as possible but to encompass the entire suspicious opacity"* [S6].
- Около 4 500 снимков прочитаны трижды (2 читателя STR + 1 RSNA). Из них 1 500 ушли в train,
  1 000 в stage-1 test и 2 000 в stage-2 test (хост [S5]; позже stage-2 test оказался из 3 000
  снимков, Shih [S6]: *"Three thousand triple-read cases formed the test set"*).
- Объединение боксов в multi-read: *"the intersection was used if there was at least a 50%
  overlap by one of the boxes"*. Изолированные боксы проверял арбитр. Боксы с низкой
  вероятностью удалены. Если на снимке был только low-бокс, он помечен как
  `No Lung Opacity / Not Normal`.
- Limitations у Shih [S6]: *"the use of bounding box intersections rather than a weighted average
  ... made the final test set bounding boxes smaller than those of the training set"*.
- Превалентность: stage-1 train 22.0 % позитивов против **35.3 %** в stage-1 test (Andy Harless,
  [S12]). 1-е место целилось в 35–37 % позитивов на тесте [S7]. На локальном `stage_2_train`
  доля позитивов 22.5 % [проверено].
- Stage-2 `stage_2_train` = stage-1 train + stage-1 test (1 000 triple-read). Около 2 500
  triple-read снимков (1 500 + 1 000) растворены среди примерно 24 000 single-read, и **их ID не
  опубликованы** [S5].
- Inter-reader variability: kappa не публиковали [S6]. Хост: *"Doctor-doctor agreement for this
  problem is not exceedingly high"* [S11]. Внутри одного NIH-пациента цели смешаны у 1 726 из
  4 355 пациентов (это не обязательно шум: исследования сделаны в разные даты).

### 3.2 Сжатие боксов (box shrinking)

- **1-е место** (Ian Pan, Alexandre Cadrin-Chênevert) [S7]: *"We resized the lengths and widths of
  our final predictions by 87.5%"* относительно центра бокса. Эффект на stage-1 public LB:
  0.181→0.209 в начале, 0.218→0.252 позже, 0.222→0.260 на финальном сабмите. Они пробовали
  имитировать пересечение боксов ансамбля, и это работало чуть хуже простого ресайза.
  Объяснение: triple-read GT строился как пересечение, поэтому он систематически меньше
  single-read боксов, на которых училась модель.
- **2-е место** (Dmytro Poplavskiy) [S8]: вместо среднего размера анкеров по фолдам брал 20-й
  перцентиль минус 1.6·(p80 − p20). После соревнования проверил ×0.875: 0.247→0.249 на stage 2.
- **3-е место** (Phillip Cheng) [S9]: −17 % по каждой стороне. Важное наблюдение: на большом
  внутреннем val сжатие **помогало**, то есть боксы модели были просто велики (L1-регрессия плохо
  согласована с IoU-метрикой). На маленьком val оно **вредило**, но на LB всё равно помогало.
- **14-е место** [S10]: late submission с ×0.875 дал бы 0.222→0.236 (на уровне 6-го места).
- **Для нас:** наш test single-read, так что механизм «пересечения читателей» почти не работает.
  Остаётся механизм 3-го места: систематически раздутые боксы из-за loss и аугментаций.
  Гипотеза для HW2: `decode.box_scale` ∈ [0.8, 1.0], подбор на val, проверка на test с парным
  бутстрапом. Ожидаемый эффект небольшой. Это наша оценка, она не проверена.

### 3.3 Классификационный гейтинг и two-stage

- 1-е место [S7]: ансамбль классификаторов (InceptionResNetV2, Xception, DenseNet169;
  разрешения 256–512; 2 или 3 класса; предобучение на NIH CXR14 дало около +1 % AUC; CV AUC
  0.88–0.90, на stage-1 test 0.93). Score бокса умножали на вероятность класса и отсекали боксы
  с итоговым score < 0.225; для RetinaNet ставили пороги на класс и на бокс отдельно.
- 2-е место [S8]: одна RetinaNet с дополнительной головой image-level классификации на 3 класса
  (multi-task). Её выход **не использовался**, но обучение с ней улучшало результат; плюс
  dropout на голове. Абляция есть в статье Gabruseva et al. [S8], рис. 3.
- 3-е место [S9]: без отдельного классификатора; порог по score подбирали по максимуму
  индекса Юдена на уровне изображений, с чувствительностью около 90 %.
- 11-е место (DancingBears) [S18]: DenseNet121-классификатор, затем YOLOv3 только на уверенно
  позитивных снимках.
- 14-е место [S10]: пересечение сегментационной маски и детекций главным образом отсекает FP
  на негативах.
- 1-е место: детекторы, обученные только на позитивах, требуют гейтинга. RetinaNet, обученная
  на склейках «негатив + позитив», балансирует precision/recall и обходится почти без
  классификатора.
- **Для нас:** `model.cls_head` + `decode.score_mode="heatmap_x_cls"` — прямая реализация идеи
  1-го места в лёгкой форме и multi-task 2-го места. Абляции: (a) голова без гейтинга (эффект
  multi-task), (b) гейтинг, (c) выбор порога.

### 3.4 AP vs PA shortcut [S11] [проверено локально]

| view | n | доля позитивов | боксов на позитив |
|---|---|---|---|
| AP | 12 173 | 0.383 | 1.67 |
| PA | 14 511 | 0.093 | 1.31 |

- ROC-AUC признака `view==AP` равен 0.706. В Shih [S6] на всех 30 000: 16 248 PA и 13 752 AP.
- AP-снимки — портативные, у лежачих и тяжёлых пациентов. Хост (Anouk Stein) сослалась на
  разбор John Zech про shortcut learning [S11]. 2-е место: *"I felt the orientation field
  borderlines with being the leak"* [S8]. 1-е и 3-е места пробовали отдельные пороги и ресайзы
  для AP/PA, и это не помогло [S7, S9].
- Сеть может выучить view по пикселям (маркер «PORTABLE», силуэт сердца). Поэтому в отчёте
  нужны срезы метрики по view (они уже есть в SPEC).

### 3.5 Разрешение входа и архитектуры

- 1-е место: детекторы на 224–512 (каждый фолд на своём разрешении; низкие разрешения не хуже,
  на LB даже +0.005–0.008), RetinaNet 384, классификаторы 256–512 [S7].
- 2-е место: 512. *"with 256 resolution I have seen results degradation"* [S8].
- 3-е место: **224**, *"high image resolution was not necessary"* [S9].
- 14-е место: 512 немного лучше 256 для детекции [S10].
- Архитектуры: в основном RetinaNet (ResNet-50/101/152, SE-ResNeXt-101), Deformable R-FCN и
  Relation Networks, Faster/Mask R-CNN, YOLOv3. CenterNet-подобных решений в топе не было;
  CenterNet появился только в 2019 году.
- **Для нас:** 256 для бейзлайна оправдано (3-е место было на 224); переход на 384 — разумная
  гипотеза для HW2 с ожидаемым небольшим плюсом.

### 3.6 Аугментации

- 1-е место (детекция): только hflip; `--random-transform` в keras-retinanet не помогал и делал
  обучение нестабильным. Классификаторы: инверсия цвета 50 %, flip 50 %, контраст/crop/rotation
  50 %; TTA 15× для классификации; для детекции TTA flip и масштабы 0.8/1.2 [S7].
- 2-е место: rotation до 6°, shift, scale, shear, hflip, blur/noise/gamma понемногу. При
  повороте вращали по 2 точки на каждой стороне (на 1/3 и 2/3 длины), а не углы бокса, чтобы
  бокс не раздувался. Абляция на val, best mAP [S8, табл. 3]: без аугментаций 0.246, light
  0.254, heavy 0.250, heavy + custom rotation 0.256, **heavy без rotation 0.261**.
- 3-е место: rotation (не больше примерно 0.05 rad), translation, scale, hflip, случайная
  константа к яркости [S9].
- 14-е место: hflip, небольшие scale и rotation; более сложные аугментации не помогали [S10].
- **Для нас:** hflip + небольшие scale/translate без поворотов — самая обоснованная комбинация.
  Поворот раздувает axis-aligned бокс, и это противоречит выводу о слишком больших боксах.

### 3.7 Прочие приёмы топов

- NMS: 1-е место — подавление вложенных боксов в финале *снижало* скор, SoftNMS не помог [S7].
  3-е место — агрессивный NMS внутри модели, взвешенное усреднение боксов между моделями [S9].
  2-е место — оптимальный порог NMS сильно плавал между эпохами (0.45–1.0) [S8].
- Порог по score подбирали под превалентность теста (около 35–37 %). На тесте все топы
  снижали порог относительно val, потому что в тесте позитивов больше [S7–S9].
- Ансамбли фолдов и чекпоинтов дают стабильность; 1-е место — 50 детекторов, хотя 6 моделей
  уже дали 0.253 [S7].
- Внешние данные: предобучение классификаторов на NIH CXR14 (1-е место) [S7].

### 3.8 Скоры: лидерборд и бейзлайны [проверено через API Kaggle, S14]

- Stage-2 private LB (3 000 снимков, 344 команды в выдаче API): 1) 0.25475 Ian Pan & Alexandre
  Cadrin; 2) 0.24781 Dmytro Poplavskiy; 3) 0.23908 Phillip Cheng; 4) 0.23901; 5) 0.23807; …
  10) 0.22497. Медиана 0.148, квартили 0.123 / 0.173.
- Stage-2 public LB считался по **1 %** теста, то есть по 30 снимкам (`leaderboardPercentage: 1`
  в API; [S13]), и был бесполезен для отбора.
- Stage 1 public LB (1 000 снимков): у 1-го места финал 0.260, у 3-го 0.238 (его stage 2 —
  0.239) [S7, S9].
- Валидация 2-го места на собственном val: mAP около 0.25–0.26 [S8]. Это не тот же тест, что
  LB, поэтому числа прямо не сравнимы.
- Простые ориентиры:
  - пустой сабмит / sample submission: **0.0** [S3, S19];
  - «Simple model 0.353» на раннем LB был бенчмарком Kaggle, его потом убрали. Число совпадает
    с долей позитивов в stage-1 test, участники считали это артефактом или утечкой [S12]
    [не проверено, что это за модель];
  - публичный kernel Mask R-CNN + COCO transfer: около 0.155 на stage-1 public LB
    [не проверено, число взято из названия kernel, на который ссылается S10];
  - сегментационный UNet без детекции: около 0.12 на stage-1 [S10].
- Наши тривиальные бейзлайны (`empty`, `prior_boxes`) считаются в `rsna.baselines`, их числа
  будут в `results/baseline_trivial/`.

---

## 4. Открытые вопросы и непроверенное

- Точный код метрики Kaggle (2018, до появления открытых Kaggle metrics) не опубликован. Порядок
  сопоставления описан противоречиво ([S1] против [S3]), но на этих данных это несущественно
  (§1.4).
- Смысл `subset_group` в JSON маппинга неизвестен.
- Почему в JSON 316 «лишних» ID и почему Shih [S6] пишет о 29 894 снимках: не выяснили.
- Какие из примерно 2 500 triple-read снимков лежат в `stage_2_train`, неизвестно (ID не
  публиковались). Метаданные likelihood для 15K боксов хост выложил в 2020 году [S5, S20], но без
  `patientId`; мы их не скачивали.
- Полный текст статьи Pan, Cadrin-Chênevert, Cheng (AJR 2019) [S15] недоступен (403); прочитана
  только аннотация.

---

## Источники

- [S1] Kaggle, RSNA Pneumonia Detection Challenge, Evaluation:
  https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge/overview/evaluation.
  Локальная копия: `data/external/kaggle_evaluation_page.md`.
- [S2] Phil Culliton (Kaggle), «what about true negatives in evaluation?»:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/64341
- [S3] «How to get official scoring metric?» (ответы хоста о сопоставлении и исключении):
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/64860
- [S4] Yicheng Chen, kernel «Mean Average Precision Metric»:
  https://www.kaggle.com/chenyc15/mean-average-precision-metric. Копии кода:
  https://github.com/pdima/kaggle_RSNA_Pneumonia_Detection/blob/master/metric.py ,
  https://github.com/tatigabru/kaggle-rsna/blob/master/src/metric.py ,
  https://github.com/i-pan/kaggle-rsna18/blob/master/models/RetinaNet/keras_retinanet/utils/evaluate_with_kaggle_metric.py
- [S5] Anouk Stein & George Shih (MD.ai, хост), «Pneumonia Dataset Annotation Methods»:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/64723
- [S6] Shih G, Wu CC, Halabi SS, et al. «Augmenting the National Institutes of Health Chest
  Radiograph Dataset with Expert Annotations of Possible Pneumonia». Radiology: Artificial
  Intelligence 2019;1(1):e180041. doi:10.1148/ryai.2019180041.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8017407/
- [S7] 1st place, Ian Pan & Alexandre Cadrin-Chênevert:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/70421 ; код:
  https://github.com/i-pan/kaggle-rsna18
- [S8] 2nd place, Dmytro Poplavskiy:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/70427 ; Gabruseva T,
  Poplavskiy D, Kalinin AA. «Deep Learning for Automatic Pneumonia Detection». CVPR Workshops 2020,
  https://arxiv.org/abs/2005.13899 ; код: https://github.com/tatigabru/kaggle-rsna
- [S9] 3rd place, Phillip Cheng:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/70632 ; код:
  https://github.com/pmcheng/rsna-pneumonia
- [S10] 14th place, Xin Yi: https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/70464
- [S11] «Data Leak - ViewPosition (AP/PA) correlated with target» (ответы хоста):
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/64620
- [S12] Andy Harless, «I knew the train & test data were different, but...»:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/69678 ; также
  discussion/64894 и /68836 (Simple model 0.353).
- [S13] «Stage-2 public LB - 1% or 30 images»:
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/70216
- [S14] Kaggle leaderboard, внутренний API `competitions.LeaderboardService/GetLeaderboard`
  (competitionId 10338), получено 2026-11-14; UI:
  https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge/leaderboard
- [S15] Pan I, Cadrin-Chênevert A, Cheng PM. «Tackling the Radiological Society of North America
  Pneumonia Detection Challenge». AJR 2019;213(3):568-574. doi:10.2214/AJR.19.21512, PMID 31120793
  (прочитана только аннотация).
- [S16] RSNA mapping JSON:
  http://s3.amazonaws.com/east1.public.rsna.org/AI/2018/pneumonia-challenge-dataset-mappings_2018.json
- [S17] RSNA challenge datasets 2018: https://rsna.org/challenge-datasets/2018 (не открывали)
- [S18] 11th place DancingBears: https://github.com/erniechiew/kaggle_rsna_pneumonia_dancingbears
- [S19] «Submit sample subs - 0 scores»: https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/70217
- [S20] «Pneumonia Boxes Likelihood Data» (хост, 2020):
  https://www.kaggle.com/c/rsna-pneumonia-detection-challenge/discussion/150643
- [S21] DeepRadiology Team, «Pneumonia Detection in Chest Radiographs», https://arxiv.org/abs/1811.08939
  (только аннотация)
