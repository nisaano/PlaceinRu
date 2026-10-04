# Данные, измерение качества и приёмка

Пороговые значения ниже — предлагаемые критерии. Есть только синтетический пилот intent-классификатора; полный benchmark на реальных/независимо размеченных данных и полное тестирование маршрутов ещё не выполнены.

## Датасеты

Фактический начальный smoke-набор `data/fixtures/dialogue-smoke.json` содержит синтетические пользовательские сообщения и многошаговое уточнение. Он покрывает даты, отправление, выбор/автоподбор направления, интересы, группу от 1 до 4, наличие детей и выбор региона из текущего пилотного каталога. Эти примеры проверяются API-регрессией, но не заменяют целевой benchmark и не подтверждают качество обученной модели.

Для retrieval создан отдельный `data/fixtures/search-relevance.json`: 8 синтетических запросов с ручными graded judgments по synthetic object IDs. `python -m scripts.evaluate_retrieval` измеряет BM25 baseline, а `python -m scripts.evaluate_retrieval --ranking-method embedding` — локальный `ai-forever/sbert_large_nlu_ru` на том же наборе; оба используют NDCG@5, Recall@5 и MRR. Embedding evaluator дополнительно сообщает CPU-задержки запросов после первичной загрузки модели и прогрева векторов кандидатов. Модель закреплена на revision `89deeaa197d9d146e5763ac1f5fe32bf66817126`, работает через mean pooling. Для API её файлы нужно отдельно загрузить командой `python -m scripts.download_embedding_model`; рантайм не скачивает модель сам и не подменяет ошибку загрузки лексическим поиском.

Intent pilot: `data/datasets/intent-v1.json`, 135 synthetic manually curated messages over the multi-label API taxonomy. Train/validation/test have 81/27/27 examples and disjoint `family_id`s. `scripts.evaluate_intent_classifier` compares multi-label RuBERT metrics to `rules-v1`. RuBERT-tiny2 is fine-tuned locally; the head and checkpoint belong to MRT-AI. The local developer chat (`.\start.cmd`) also compares both systems on manually entered messages. The pilot is only a pipeline smoke test, not a representative corpus; the classifier does not control Misha's response or trip state.

The developer chat starts in structured-form mode matching the current PlaceinRu concept: calendar start date, optional duration, origin, optional destination/discovery, party count (1–4), children, interests, guide, and budget with explicit group/person basis and trip/day period. Free-text input is disabled until form submission; after that it is presented only as an edit channel for the assembled trip. Edits still run through `rules-v1`, with the intent model shown as a separate experiment. The form submits normalized `TripRequest` slot updates directly and shows the JSON payload. This validates the interface/API contract; it does not evaluate NLP extraction or give the intent classifier structured-trip understanding.

Trip-slot extraction baseline: `data/datasets/trip-slots-v1.json` contains 63 synthetic single-message examples with expected normalized values for origin, destination, dates/duration, party size, child presence, and interests. Wording families are assigned wholly to train, validation, or test; paraphrases stay in the same split. After inspecting the first holdout errors, those previously inspected families were moved into validation, and five new phrase families were reserved for the current test split. Counts are 15 train / 33 validation / 15 test examples. This is a manually authored capability-gap probe, not real traffic or an ML training corpus. The local chat also displays the normalized parameters currently collected by `rules-v1` after each user message. Rebuild and evaluate:

```powershell
.\venv\Scripts\python.exe -B -m scripts.build_trip_slot_dataset
.\venv\Scripts\python.exe -X utf8 -B -m scripts.evaluate_trip_slot_baseline
```

On the refreshed synthetic test (15 examples), rules-v1 exact match across all eight slots is 1.0000; every individual slot also scores 1.0000. The inspected old test families score 0.7576 exact match in validation. The parser now recognizes destination-first forms (`Москва из Казани`, `Карелия из Санкт-Петербурга`), common group expressions (`вчетвером`, `парой`, numbered adults/travellers), and written date ranges (`1 и 2 июля 2028 года`), while validating calendar dates. The 15-example synthetic test is too small and too curated to estimate real-user accuracy; it is only a regression check. No learned slot extraction model has been trained in this stage.

Reproduce the local experiment after installing optional ML requirements and downloading the pinned encoder:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\venv\Scripts\python.exe -B -m scripts.build_intent_dataset
.\venv\Scripts\python.exe -B -m scripts.download_intent_encoder
.\venv\Scripts\python.exe -B -m scripts.train_intent_classifier --epochs 10
.\venv\Scripts\python.exe -B -m scripts.evaluate_intent_classifier
```

Latest synthetic test split: RuBERT experiment macro F1 0.6266, micro F1 0.6885, exact match 0.2963; `rules-v1` macro F1 0.7797, micro F1 0.7937, exact match 0.7037. The 27 test utterances are too few to generalize, but the result is enough to reject deploying this classifier now. Keep rules-v1 as Misha's only dialogue parser until a larger independently labeled dataset supports a better model.

Набор мал, создан по тем же объектам и похожим формулировкам, что и каталог, не является независимым holdout и не должен использоваться для заявлений о production качестве. Сравнение — только технический smoke/regression эксперимент; положительный результат не делает synthetic candidates реальными местами и не подтверждает качество пользовательского semantic search.

Последний smoke-прогон на закреплённой SBERT модели: NDCG@5 0.8577, Recall@5 0.8542, MRR 1.0000; BM25 на том же наборе: 0.9031, 0.8958, 1.0000. Следовательно, пока BM25 остаётся рекомендуемым default. В отдельном CPU-прогоне после рефакторинга средняя latency SBERT запроса составила 62.0 ms (p50 61.5 ms, p95 69.9 ms); полный warmup — 7.05 s. Время зависит от CPU-нагрузки и состояния cache. Всего 8 запросов недостаточно для оценки качества или стабильной оценки performance.

| Набор | Единица разметки |
|---|---|
| intent | message + preceding state → один/несколько intent |
| entities | message + reference time/timezone → spans и нормализованные значения |
| dialogue | последовательность сообщений/ручных действий → состояния, уточнения, changes |
| relevance | предпочтения + объект → grade 0..3 с причиной |
| route | TripRequest + фиксированные candidates/matrix → допустимость и качество предложения |
| provider contracts | разрешённые обезличенные snapshots → ожидаемая нормализация; отдельно от синтетики |

Начальный целевой объём: 400–600 отдельных запросов, не менее 15 примеров каждого обязательного intent, 40 многошаговых диалогов, 1000 relevance-пар и 40 routing-сценариев. Это стартовый benchmark, не достаточное основание для обучения большой модели. Дообучение расширять по анализу ошибок и наличию прав на данные.

Train/dev/test делить по целым диалогам и семействам перефразировок, а не случайным соседним репликам. Не допускать одного шаблона с заменённым городом одновременно в train и test. Зафиксировать test до подбора порогов; отдельно holdout регионов/объектов. Сохранять происхождение, права использования, версию аннотации и решения по спорным примерам. Синтетические запросы помечать и проверять вручную; реальные — обезличивать и собирать с надлежащим основанием.

## Метрики и предварительные пороги

| Область | Измерение | Предлагаемая приёмка первого MVP |
|---|---|---|
| Intent | macro F1, per-class F1, multi-label exact match | macro F1 ≥ 0.85, отчёт по каждому intent |
| Entities | span P/R/F1 и exact match нормализованных денег/дат/группы | F1 ≥ 0.90; все критичные сценарии ниже проходят |
| Dialogue | завершение сценария, лишние повторные вопросы, потеря слотов | 100% фиксированных регрессионных сценариев, ноль потерянных подтверждённых слотов |
| Ranking | Precision@3, Recall@K при полном размеченном пуле, NDCG@5 | NDCG@5 не ниже лексического baseline, анализ причин; numeric target после baseline |
| Constraints | нарушения бюджета/запретов/времени у validated | 0 на приёмочном наборе; unknown не засчитывать как validated |
| Grounding | факты/ID/ссылки вне snapshot | 0 в проверяемых структурированных результатах |
| Editing | корректность targets, атомарность, version conflicts | все сценарии корректны, нет потерянных ручных правок |
| Performance | p50/p95 отдельно NLP/retrieval/routing/provider | измерить на указанном CPU/GPU; SLO установить после baseline |

Предварительные пороги — проектные цели и могут уточняться по сложности набора; результаты не подгонять изменением test. Высокий средний F1 не оправдывает ошибки денежных единиц или самовольное применение изменений. Online CTR/saves не смешивать с offline Precision@K.

## Обязательные сценарии

1. «Подбери регион на пять дней, люблю природу» — DISCOVER, нет обязательного вопроса destination.
2. Пользователь ответил городом на вопрос отправления — ANSWER_QUESTION, остальные слоты сохраняются.
3. `500 рублей`, `60 тысяч`, `60к`, `60 000`, `80 тыс. на двоих`, `10 тысяч в сутки` — разные нормализованные суммы и scopes; неоднозначность уточняется.
4. `в следующую пятницу`, `в июле`, даты без года, конец раньше начала, прошлые даты — расчёт по reference time или вопрос, без случайной текущей даты сервера.
5. «Двое взрослых и ребёнок» — возраст неизвестен; разные timezone вылета/прилёта и ночной поезд не теряют день.
6. «Без самолётов», «не хочу музеи», «любой транспорт», «без гида» — отрицания/явный выбор сохраняются.
7. Смена дат инвалидирует тариф отеля и рейса; cached цена не становится live.
8. Нет цены отеля/есть ресторан без чека — full budget unknown, не ноль и не «уложились».
9. Цена за ночь/номер/человека, налоги/сборы, roundtrip и ночи — правильные количества, нет двойного счёта.
10. Недоступный гид, гостиница вне бюджета, закрытая достопримечательность — исключение/partial с объяснением.
11. Окна работы, выходной/праздничное исключение, переезд, буфер аэропорта, заселение — конфликты обнаруживаются.
12. «Убери экскурсию второго дня, добавь прогулку и не увеличивай стоимость» — пакет операций с проверкой, при невозможности rollback.
13. «Замени его» при двух возможных целях — уточнение; target из UI разрешает неоднозначность.
14. Ручное закрепление, затем REBUILD_ROUTE — закреплённая точка остаётся или конфликт объясняется.
15. Два параллельных изменения и повтор POST — версия/идемпотентность, нет дубликатов и потери правок.
16. Неверный object_id, вредоносная инструкция в описании кандидата, ссылка неизвестного домена — не превращаются в исполняемые действия или факты.
17. Таймаут, 429, отсутствие ключа, пустой каталог, повреждённый snapshot — понятный статус; нет бесконечных повторов.
18. На карте перепутанные lat/lon выявляются проверкой; missing geometry даёт схему, не дорожный маршрут; выбор дня синхронизирован со списком.
19. Разные сессии не видят чужие state/поездки; dev mode явно отделён от production-авторизации.
20. SAVE_TRIP при недоступном Backend не отвечает «сохранено»; локальный draft называется локальным.

## Feedback

События из ТЗ: recommendation_shown, clicked, saved, removed, hotel_selected, hotel_rejected, attraction_selected, attraction_rejected, restaurant_selected, guide_selected, route_edited, route_rebuilt, like, dislike.

Envelope: event_id, event_type, occurred_at, pseudonymous_session_id, trip_id/version, request_id, option_id, object_id/offer_id, position, model_version, ranking_version, experiment_id, data_mode. Backend — поставщик production-событий; dev gateway — только событий стенда. Дедупликация по event_id; fixtures исключаются из продуктовых метрик.

CTR считать как клики по действительно показанным рекомендациям с одинаковой единицей измерения и окном атрибуции. Сохранение и отказ учитывать отдельно; не считать отсутствие клика негативной меткой автоматически. Для обучения учитывать смещение позиции/показа. Сырые сообщения и персональные данные не логировать по умолчанию; retention/consent определить перед production-сбором.

## Проверка выпуска

Без сети: unit/contract/regression на фиксированных snapshots, деньгах, датах, изменениях и ограничениях. С сетью: отдельный opt-in smoke для разрешённых провайдеров, без покупки и отправки заявок. UI: один полный сценарий создания, сравнения, ручной правки, чат-правки, карты, ссылки и сохранения; дополнительно empty/error/partial.

Отчёт содержит commit/версию кода, версии данных/моделей, параметры, оборудование, результаты, ошибки и ограничения. Повторять проверки после значимых изменений. Первая задача — сформировать этот набор и baseline, не утверждать качество по восьми удачным примерам текущего проекта.
