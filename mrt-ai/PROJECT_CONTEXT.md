# mrt-ai / Миша — контекст проекта

Обновлено: 2026-10-06.

## Роли и границы

- **mrt-ai** — собственный локальный ML pipeline: логика поиска, классификатора, обработки данных и тестов.
- **Миша** — интеллектуальный помощник, диалоговый слой и API (`app/`).
- SBERT/RuBERT — внешние предобученные веса, используемые через локальные adapters. MRT-AI владеет обученным intent checkpoint/head, pipeline, taxonomy и inference кодом.
- Изменять можно только `mrt-ai`. `backend-java` и `frontend` — read-only.
- Исходные CSV, документацию, fixtures и сохранённую SQLite-сессию `data/runtime/` не удалять при cleanup.

## Рейтинг `trip-fit-bm25-v3`

Прямое совпадение интереса получает полный вес, тематически близкая карточка — только частичный; широкая связь не попадает в `matched_interests`. Исключённые интересы фильтруются по прямому совпадению. API сообщает `unscored_factors` и предупреждает, когда каталог не покрывает интерес. Holdout из шести вручную размеченных synthetic запросов дал NDCG@5=0.9915, Recall@5=1.0. Эти метрики — только development smoke check. Blind-review sheet находится в игнорируемом `artifacts/trip-fit-review-v1.json`; рецензенту не передавать answer key. OSM import получил HTTP 504/read timeout; OSM snapshot отсутствует, но локальный Wikidata snapshot уже содержит 2 593 места. Статус и ограничения — в `docs/ML_PROJECT_STATUS.md`.

## Рабочий срез маршрута на тестовых данных (2026-10-06)

- Dev-чат после формы по умолчанию явно выбирает режим `fixture` и вызывает существующие `/v1/candidates/query`, `/v1/rank`, `/v1/route/proposal`. Режим `cached` выбирается отдельно; автоматической подмены источника нет.
- Если направление не указано, dev-чат предлагает регионы из рекомендаций; выбор через versioned `/v1/sessions/{id}/select-region`, затем строится маршрут.
- Planner даёт каждому дню уникальную точку, затем распределяет оставшиеся согласно темпу: 1/2/3 точки на день для relaxed/balanced/active. Время начала/окончания всегда null: переезды и реальные часы не проверены. Синтетические отель/транспорт/гид — только ссылки на кандидатов, не бронирование. Стоимость unknown.
- Проверено: 107 unit/API tests PASS; headless Edge: форма → фиктивный рейтинг → маршрут с датами; DISCOVER → выбор области → маршрут. Демо-координаты нельзя использовать для карты/навигации. OSM snapshot отсутствует; локальный Wikidata snapshot добавлен.

## Фактический статус

- Диалог — deterministic `rules-v1`, не ML-классификатор. Подбор регионов ограничен Москвой и Московской областью.
- `/v1/search/places` обслуживается `mrt_ai.retrieval.MrtAiRetrievalPipeline`: BM25 baseline либо embedding retrieval в явно выбранном источнике. Cached provider читает локальный `data/normalized/wikidata-places.json` (2 593 места); OSM snapshot не создан из-за HTTP 504/timeout Overpass. Fixture остаётся отдельным явным synthetic mode без fallback. Общие Candidate/Offer/Search contracts находятся в `mrt_ai/contracts/catalog.py`; API-слой использует их.
- BM25 остаётся default: на 8 synthetic queries NDCG@5=0.9031, Recall@5=0.8958; SBERT=0.8577 и 0.8542. Не считать эти smoke-метрики независимым benchmark.
- SBERT `ai-forever/sbert_large_nlu_ru` — MIT, бесплатен для локального использования. Проверенные веса находятся в игнорируемом `models/embeddings/sbert_large_nlu_ru/`; не коммитить.
- Создан multi-label intent pilot: 9 labels, 135 синтетических размеченных сообщений, family-separated train/validation/test 81/27/27. Fine-tuned RuBERT-tiny2 checkpoint хранится локально; dev-чат параллельно показывает его предсказания и результат rules-v1, но реальный ответ Миши и изменения поездки остаются rules-v1.
- На synthetic test RuBERT macro/micro F1 = 0.6266/0.6885, exact match = 0.2963; rules-v1 = 0.7797/0.7937/0.7037. Результат пилота хуже baseline; до получения более сильных результатов правила остаются в production path.
- Trip-slot benchmark обновлён до 63 synthetic messages, 8 слотов, family-separated train/validation/test 15/33/15. После переноса уже просмотренных первоначальных test семейств в validation, новый held-out test набрал 15/15 exact match rules-v1. Примеры вымышленные и не дают оценку точности на реальных пользователях.
- По первым подтверждённым ошибкам rules-v1 расширен на destination-first формы, письменные даты диапазона, colloquial party size и число взрослых/путешественников; добавлены проверки дат.
- Dev chat после реплики явно отображает извлечённые правилами поля поездки (включая неуказанные), рядом с экспериментальным RuBERT intent analysis.
- Dev chat использует form-first flow по PlaceinRu-концепту: дата, города, интересы, 1–4 человека, дети, гид, бюджет с явным scope; free-text disabled до формы, затем только для правок. Это ручной structured input, не NLP-экстрактор.
- После отправки формы dev-чат по умолчанию явно использует fixture-кандидатов (сохранённый каталог Wikidata выбирается отдельно), ранжирует их через `/v1/rank` (trip-fit-bm25-v3) и показывает score, компоненты, объяснение совпадения и исключения. При выборе cached без snapshot UI показывает явную ошибку. Score 0–100 — относительная оценка только в текущем наборе, не вероятность и не качество/актуальность места; бюджет не учитывается при неизвестных ценах.
- Для выбранного направления с датой `/v1/route/proposal` использует ranking, собирает provisional дни без повторения объектов и явно показывает дни без подходящих мест. Нулевая стоимость не подставляется: итог бюджета неполный и неизвестный.
- После успешного импорта OSM координаты будут исходными, но часы работы/цены/availability неизвестны, переезды не рассчитываются; маршрут нельзя использовать для навигации или бронирования. Fixture-координаты остаются вымышленными.
- Ответ API для уже выбранного направления подтверждает его сохранение; live-услуги и real route engine по-прежнему не подключены.
- Синтетические места не реальный inventory. Нет полноценного маршрутизатора, live-провайдеров и production Backend integration.
- Read-only Java trips adapter есть, но live-интеграция с JWT не проверена. Java catalog мест не обнаружен.

Текущий аудит и ближайшая задача: [docs/ML_PROJECT_STATUS.md](docs/ML_PROJECT_STATUS.md). Этапы и критерии: [docs/ML_DEVELOPMENT_PLAN.md](docs/ML_DEVELOPMENT_PLAN.md). Структура, модельные роли и лицензии: [docs/ML_STRUCTURE.md](docs/ML_STRUCTURE.md). Хронология: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Запуск и проверки

- `.\start.cmd` запускает dev API и браузерный чат Миши.
- API без dev-страницы: `.\venv\Scripts\python.exe -B -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010`
- Полные тесты: `.\venv\Scripts\python.exe -B -m unittest discover -s tests -v`
- BM25 evaluation: `.\venv\Scripts\python.exe -B -m scripts.evaluate_retrieval`
- SBERT evaluation: `.\venv\Scripts\python.exe -B -m scripts.evaluate_retrieval --ranking-method embedding`
- Intent pipeline: `docs/ML_STRUCTURE.md`; воспроизведение обучения и оценки приведено в `docs/EVALUATION.md`.
- Trip-fit relevance evaluation: текущие dev/holdout метрики в `docs/ML_PROJECT_STATUS.md`; blind review worksheet flow — `docs/TRIP_FIT_BLIND_REVIEW.md`.
- Локальный тест intent classifier с пользовательским UI: `.\start.cmd`; endpoint сравнения включён только через `scripts.dev`.
- Trip slots baseline: `.\venv\Scripts\python.exe -X utf8 -B -m scripts.evaluate_trip_slot_baseline`; ошибки test и per-slot метрики выдаются в JSON.
- Все временные, модельные веса и session data должны оставаться внутри `mrt-ai`; не читать `.env`.
- Полная регрессия после добавления Wikidata snapshot: 107 unit/API tests PASS. Проверены provenance импортёра и отсутствие fixture fallback. Через локальный API проверены региональная выдача, поиск и черновик маршрута; браузерная выдача отдельно не проверялась.
## Актуализация датасета мест (2026-10-06)

В `data/normalized/wikidata-places.json` сохранён реальный CC0 snapshot Wikidata через QLever: 2 593 места (Москва — 1 219, Московская область — 1 374). Источник, QID, координаты и хеши сохраняются; открытие cached-режима использует локальный файл. Импорт/обновление: `python -m scripts.import_wikidata_places`; детали и ограничения: `docs/PLACE_DATASETS.md`.

Проверка live-like локальной выдачи прошла: региональный batch → BM25 search → provisional route proposal. Снимок содержит в основном культуру/архитектуру/природу; у мест не подтверждены расписание, стоимость, рейтинг, доступность, транспорт и текущая работа. OSM import всё ещё не получен из-за таймаутов, поэтому обновление Wikidata расширяет каталог, но не заменяет следующую OSM/официальную POI-интеграцию. Не считать bbox точной границей; регион назначается по административной иерархии Wikidata.
