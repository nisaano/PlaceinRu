# mrt-ai / Миша — контекст проекта

Обновлено: 2026-10-04.

## Роли и границы

- **mrt-ai** — собственный локальный ML pipeline: логика поиска, классификатора, обработки данных и тестов.
- **Миша** — интеллектуальный помощник, диалоговый слой и API (`app/`).
- SBERT/RuBERT — внешние предобученные веса, используемые через локальные adapters. MRT-AI владеет обученным intent checkpoint/head, pipeline, taxonomy и inference кодом.
- Изменять можно только `mrt-ai`. `backend-java` и `frontend` — read-only.
- Исходные CSV, документацию, fixtures и сохранённую SQLite-сессию `data/runtime/` не удалять при cleanup.

## Фактический статус

- Диалог — deterministic `rules-v1`, не ML-классификатор. Подбор регионов ограничен Москвой и Московской областью.
- `/v1/search/places` обслуживается `mrt_ai.retrieval.MrtAiRetrievalPipeline`: BM25 baseline либо embedding retrieval, только явный synthetic fixture mode. Общие Candidate/Offer/Search contracts находятся в `mrt_ai/contracts/catalog.py`; API-слой использует их.
- BM25 остаётся default: на 8 synthetic queries NDCG@5=0.9031, Recall@5=0.8958; SBERT=0.8577 и 0.8542. Не считать эти smoke-метрики независимым benchmark.
- SBERT `ai-forever/sbert_large_nlu_ru` — MIT, бесплатен для локального использования. Проверенные веса находятся в игнорируемом `models/embeddings/sbert_large_nlu_ru/`; не коммитить.
- Создан multi-label intent pilot: 9 labels, 135 синтетических размеченных сообщений, family-separated train/validation/test 81/27/27. Fine-tuned RuBERT-tiny2 checkpoint хранится локально; dev-чат параллельно показывает его предсказания и результат rules-v1, но реальный ответ Миши и изменения поездки остаются rules-v1.
- На synthetic test RuBERT macro/micro F1 = 0.6266/0.6885, exact match = 0.2963; rules-v1 = 0.7797/0.7937/0.7037. Результат пилота хуже baseline; до получения более сильных результатов правила остаются в production path.
- Trip-slot benchmark обновлён до 63 synthetic messages, 8 слотов, family-separated train/validation/test 15/33/15. После переноса уже просмотренных первоначальных test семейств в validation, новый held-out test набрал 15/15 exact match rules-v1. Примеры вымышленные и не дают оценку точности на реальных пользователях.
- По первым подтверждённым ошибкам rules-v1 расширен на destination-first формы, письменные даты диапазона, colloquial party size и число взрослых/путешественников; добавлены проверки дат.
- Dev chat после реплики явно отображает извлечённые правилами поля поездки (включая неуказанные), рядом с экспериментальным RuBERT intent analysis.
- Dev chat использует form-first flow по PlaceinRu-концепту: дата, города, интересы, 1–4 человека, дети, гид, бюджет с явным scope; free-text disabled до формы, затем только для правок. Это ручной structured input, не NLP-экстрактор.
- Синтетические места не реальный inventory. Нет полноценного маршрутизатора, live-провайдеров и production Backend integration.
- Read-only Java trips adapter есть, но live-интеграция с JWT не проверена. Java catalog мест не обнаружен.

Подробная структура, модельные роли и лицензионные источники: [docs/ML_STRUCTURE.md](docs/ML_STRUCTURE.md). Хронология: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Запуск и проверки

- `.\start.cmd` запускает dev API и браузерный чат Миши.
- API без dev-страницы: `.\venv\Scripts\python.exe -B -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010`
- Полные тесты: `.\venv\Scripts\python.exe -B -m unittest discover -s tests -v`
- BM25 evaluation: `.\venv\Scripts\python.exe -B -m scripts.evaluate_retrieval`
- SBERT evaluation: `.\venv\Scripts\python.exe -B -m scripts.evaluate_retrieval --ranking-method embedding`
- Intent pipeline: `docs/ML_STRUCTURE.md`; воспроизведение обучения и оценки приведено в `docs/EVALUATION.md`.
- Локальный тест intent classifier с пользовательским UI: `.\start.cmd`; endpoint сравнения включён только через `scripts.dev`.
- Trip slots baseline: `.\venv\Scripts\python.exe -X utf8 -B -m scripts.evaluate_trip_slot_baseline`; ошибки test и per-slot метрики выдаются в JSON.
- Все временные, модельные веса и session data должны оставаться внутри `mrt-ai`; не читать `.env`.
- Последняя проверка: 91 unit/API tests PASS после parser updates; dataset baseline test exact match 15/15 на синтетическом v2 holdout.
