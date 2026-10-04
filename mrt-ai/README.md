# mrt-ai — локальная ML-система PlaceinRu

**mrt-ai** — собственный локальный ML pipeline. **Миша** — интеллектуальный помощник и его диалоговый/API интерфейс. SBERT и RuBERT — внешние открытые модели, которые подключаются как encoder-компоненты; их pretrained веса не являются собственной обученной моделью mrt-ai. Подробная схема, лицензии и план intent-классификации — [docs/ML_STRUCTURE.md](docs/ML_STRUCTURE.md).

Продуктовый frontend делает другой разработчик. Тестовый интерфейс — минимальный браузерный чат для разработчика, отдельно от продуктового frontend.

Сейчас работают уточнения, параметры поездки, SQLite-сессии, изменения сообщениями/API, подбор Москвы и области. **Ответы в чате продолжает формировать `rules-v1`; полной поездки, реальных услуг и маршрутизации пока нет.** Локальный браузерный dev-чат позволяет параллельно проверять experimental RuBERT intent classifier на своих сообщениях и сравнивать его метки с `rules-v1`; эксперимент не управляет ответом бота.

## Запуск

Одна команда в PowerShell запускает API и автоматически открывает тестовый чат в браузере:

```powershell
cd D:\PlaceinRu\mrt-ai
.\start.cmd
```

Дождитесь строки «Чат готов». Браузер открывается после готовности сервера. Если вкладка не открылась, перейдите по точному адресу, напечатанному в терминале. Порт автоматически выбирается свободным; для постоянного адреса используйте `.\start.cmd 8011` и http://127.0.0.1:8011/ . Если указанный порт занят, запустите без номера или остановите прежний экземпляр в его терминале. В каждой реплике интерфейс показывает ответ `rules-v1`, предсказанные RuBERT intents, порог выбора и вероятности всех классов.

В чате есть история, поле сообщения, отправка по Enter (Shift+Enter — перенос строки), кнопка «Новый диалог» и сворачиваемый JSON состояния. История восстанавливается при перезагрузке страницы. Например: «Из Москвы в Московскую область с 10.07.2027 по 12.07.2027, нас трое, есть дети, интересует природа». Бюджет, темп и транспорт можно сообщить дополнительно, но они не блокируют подбор региона.

В начале поездки требования задаются только структурированной формой по концепту PlaceinRu: дата через календарь, длительность, города, 1–4 путешественника, дети, интересы, гид и бюджет с явным выбором «на группу/человека» и «на поездку/день». «Посмотреть структурированные данные» показывает JSON slots, отправляемые в `PATCH /v1/sessions/{id}/trip`. Свободный ввод выключен до отправки формы; после этого он предназначен только для правок собранной поездки, например «измени даты» или «добавь музеи». Эти правки сейчас обрабатывает `rules-v1`, а RuBERT показывается как экспериментальное сравнение. Форма передаёт нормализованные поля напрямую и не является ML-извлечением текста.

Если открытая вкладка сообщает, что локальный API недоступен, проверьте, что окно терминала с `start.cmd` ещё работает. Если сервер остановлен, снова выполните `.\start.cmd` из папки `mrt-ai` и используйте адрес из строки «Чат готов»; порт может измениться.

Для classifier нужны уже установленные optional зависимости из `requirements-ml.txt` и локальный checkpoint `models/classifiers/misha-intent-rubert-tiny2/`. Если они не обнаружены, чат явно сообщит об ошибке модели, но продолжит диалог через `rules-v1`. Терминал оставляйте открытым — в нём работает сервер. Остановка Ctrl+C. Закрытие вкладки сервер не останавливает. Браузерный чат и endpoint сравнения classifier доступны только через локальный dev-запуск; production API и Docker не экспонируют тестовый endpoint. Стенд не имеет production-авторизации и слушает только 127.0.0.1. Чтобы запустить без автоматического открытия браузера: `venv\Scripts\python.exe -X utf8 -B -m scripts.dev --no-browser`.

Только API для интеграции, без тестовой страницы:

```powershell
.\venv\Scripts\python.exe -B -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010
```

В этом режиме / возвращает 404; документация доступна на /docs. Для общения в браузере используйте start.cmd. После обновления кода перезапустите прежний сервер.

При отсутствии окружения из mrt-ai:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -B -m app.catalog_import
```

## Intent classifier experiment

Код intent pipeline находится в `mrt_ai/nlp/intent/`. Синтетический family-split corpus: `data/datasets/intent-v1.json` (135 сообщений, 9 labels). Внешний бесплатный MIT encoder RuBERT-tiny2 отдельно загружается в `models/encoders/`; дообученный checkpoint принадлежит MRT-AI и сохраняется в `models/classifiers/`. Оба каталога весов исключены из Git.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\venv\Scripts\python.exe -B -m scripts.build_intent_dataset
.\venv\Scripts\python.exe -B -m scripts.download_intent_encoder
.\venv\Scripts\python.exe -B -m scripts.train_intent_classifier --epochs 10
.\venv\Scripts\python.exe -B -m scripts.evaluate_intent_classifier
```

Последний синтетический test: RuBERT macro F1 0.6266 против rules-v1 0.7797. Experimental classifier доступен в локальном dev-чате для проверки произвольных сообщений; основной ответ и обновление поездки по-прежнему принадлежат rules-v1. Пилот не готов к замене parser: нужны реальные размеченные сообщения и независимый holdout.

## Проверка извлечения параметров поездки

Отдельный synthetic benchmark `data/datasets/trip-slots-v1.json` содержит 63 полных и частичных запроса с разметкой origin, destination, дат/длительности, состава группы, детей и интересов. Семейства формулировок разделены между train/validation/test; после анализа исходных ошибок старый test перенесён в validation, а test сформирован заново. Пересобрать набор и измерить качество `rules-v1`:

```powershell
.\venv\Scripts\python.exe -B -m scripts.build_trip_slot_dataset
.\venv\Scripts\python.exe -X utf8 -B -m scripts.evaluate_trip_slot_baseline
```

После каждой реплики dev-чат также показывает нормализованные параметры, выделенные текущим `rules-v1`, включая незаполненные поля. Текущий свежий synthetic holdout: exact match всех восьми полей — 1.0 (15 из 15 запросов), macro slot accuracy — 1.0. Это маленький искусственный regression set, не точность на реальных пользователях и не результат обученной ML-модели. Детали и ограничения приведены в `docs/EVALUATION.md`.

## Подключение коллег

Целевая цепочка: **frontend → Backend → API бота**. Backend отвечает за авторизацию и доступ к поездке. Бот возвращает текст и JSON, frontend отображает карточки и карту. Read-only адаптер к Java trips API реализован; production-соединение не проверено. Папки коллег не изменены.

1. `POST /v1/sessions` с `{"timezone":"Europe/Moscow"}` → сохранить session_id и state_version.
2. `POST /v1/sessions/{session_id}/turns` с телом:

```json
{
  "request_id": "unique-request-0001",
  "expected_state_version": 0,
  "message": "Хочу поездку на неделю, люблю природу"
}
```

Ответ: state, changes, intents, notices, options. Текст бота — последний элемент state.messages; параметры — state.trip; следующий вопрос — state.pending_question. Для календаря даты задаются как ISO `YYYY-MM-DD` в `dates.start_date` и `dates.end_date` через PATCH; длительность рассчитывается включительно. Следующий запрос передаёт возвращённый state.state_version. Новая операция — новый request_id; повтор той же операции сохраняет request_id и тело.

3. `GET /v1/sessions/{id}` восстанавливает состояние. При 409 загрузить актуальную версию и согласовать изменение.
4. `PATCH /v1/sessions/{id}/trip` для ручных изменений через Backend: request_id, expected_state_version, updates с плоскими путями; null очищает поле.

Дополнительно: /v1/parse, /v1/recommend, /v1/catalog/regions, /v1/sessions/{id}/select-region, /v1/candidates/query. Фактический контракт — OpenAPI, `app/contracts.py` и `mrt_ai/contracts/catalog.py`; схемы — `schemas/`. [CONTRACTS.md](docs/CONTRACTS.md) содержит также будущие операции.

options пока содержит регионы, не путешествия. ready_for_search означает, что достаточно данных для первичного подбора региона, а не готовность маршрута. Для группы собираются общее число и наличие детей; точное число/возраст детей остаются null, если не сообщены. Деньги в копейках; неизвестная цена — null. Fixture-кандидаты вымышленные и доступны явно. Локальный API пока без production-авторизации: session_id не заменяет проверку доступа. По умолчанию сервер слушает только 127.0.0.1.

Для следующего этапа поиска и планирования подготовлен fixture-каталог [places.json](data/fixtures/places.json): 17 полностью синтетических объектов для двух пилотных регионов, с тегами, длительностью, ДЕМО-часами работы и фиктивными координатами. Получить их можно только явным запросом `/v1/candidates/query` с `"data_mode":"fixture"`. Координаты не подходят для карты и навигации; цены и доступность неизвестны.

Поиск по объектам выполняется через `POST /v1/search/places`, например `{"region_id":"ru:region:50","query":"спокойная прогулка по лесной тропе","data_mode":"fixture","top_k":5}`. По умолчанию используется BM25 (`ranking_method: "bm25"`), с совпавшими `matched_terms`. Для локального семантического поиска задайте `ranking_method: "embedding"`; score будет преобразованным cosine similarity в диапазоне 0–1, а `matched_terms` останется пустым. Модель не скачивается автоматически при запуске API:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\venv\Scripts\python.exe -B -m scripts.download_embedding_model
```

Embedding runtime работает на CPU, использует закреплённый revision `ai-forever/sbert_large_nlu_ru` и masked mean pooling. Модель открыта по MIT и бесплатна для локального использования; основные затраты — CPU/RAM и 1.7 GB диска. Веса сохраняются в игнорируемой Git-папке `models/embeddings/`; перед использованием загрузчик проверяет SHA-256. Для сравнения обеих стратегий на одном синтетическом наборе:

```powershell
.\venv\Scripts\python.exe -B -m scripts.evaluate_retrieval
.\venv\Scripts\python.exe -B -m scripts.evaluate_retrieval --ranking-method embedding
```

В evaluator для embedding выводятся NDCG@5, Recall@5, MRR и задержка запросов на CPU после загрузки модели с прогретым кэшем векторов объектов. Малый synthetic набор не является метрикой на реальных пользовательских запросах; semantic search всё ещё ранжирует только синтетические карточки и не строит проверенный маршрут. Дневник решений и выполненных этапов: [docs/CHANGELOG.md](docs/CHANGELOG.md).

### Java Backend (только чтение)

В `mrt-ai` добавлен read-only адаптер к существующим Java API личных поездок:

- `GET /v1/backend/trips` → Java `GET /api/v1/trips`
- `GET /v1/backend/trips/{trip_id}` → Java `GET /api/v1/trips/{id}`

Настройте URL сервиса в окружении процесса `mrt-ai`, например `$env:PLACEINRU_BACKEND_URL = "http://127.0.0.1:8080"`. Передавайте JWT текущего пользователя в `Authorization: Bearer <JWT>` каждому запросу к API бота. Адаптер пересылает его в Java Backend, не сохраняет и не пишет в логи. Учетные данные и серверная авторизация остаются ответственностью Backend. Перенаправления отклоняются, запрос ограничен таймаутом 5 секунд.

Пример:

```powershell
$env:PLACEINRU_BACKEND_URL = "http://127.0.0.1:8080"
Invoke-RestMethod http://127.0.0.1:8010/v1/backend/trips -Headers @{ Authorization = "Bearer $accessToken" }
```

Адаптер намеренно не меняет поездки и не считает их каталогом туристических мест. У Java Backend пока нет API каталога регионов/мест; для ranking остаются две импортированные карточки `mrt-ai`. До запуска реального Java сервиса интеграционные тесты используют HTTP mock и не требуют JWT или сетевого доступа.

### Проверка диалогов

Синтетические сценарии с датами, отправлением, направлением/режимом DISCOVER, интересами, группой 1–4 и наличием детей находятся в `data/fixtures/dialogue-smoke.json`. Они прогоняются через настоящий локальный API-сценарий:

```powershell
.\venv\Scripts\python.exe -B -m unittest tests.test_dialogue_dataset tests.test_backend -v
```

Это smoke/regression набор, не обучающая выборка и не подтверждение качества ML-модели. Реализация разбора по-прежнему rules-v1.

## Проверки

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\venv\Scripts\python.exe -B -m scripts.export_schemas
```

После изменения CSV повторить `-m app.catalog_import`. Docker содержит только API и данные; Docker не проверялся. Секреты .env не читаются.

План: [docs/README.md](docs/README.md). Память: [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).
