# Предлагаемый контракт v1

Тестовый интерфейс разработчика — минимальный браузерный чат Миши. `start.cmd` поднимает локальный API и открывает страницу; `scripts/dev.py` добавляет `/` только в dev-режиме. Обычный API и Docker не включают UI. Продуктовый frontend и карта остаются задачей коллег.

Уточнение пользователя 2026-10-04: в mrt-ai разрабатываем бота и HTTP API, без продуктового frontend. Фото — концепт поведения. Экраны и карта принадлежат frontend коллег. Тестовый интерфейс — минимальный браузерный чат scripts/developer-chat.html. Возвращаем текст и JSON.

Статус: целевой проект контракта для обсуждения с Backend. На 2026-10-04 реализованы диалоговое подмножество и начальные Candidate/Offer/Price, CandidateQuery/Batch, Catalog/RegionRecommendations в `app/contracts.py`, `mrt_ai/contracts/catalog.py` и `schemas/`. Фактические endpoints описаны в `../README.md`, `CATALOG.md` и OpenAPI сервиса. Имена мест пока строки, выбранный регион дополнен destination_region_id. Chat turn расположен в `/v1/sessions/{id}/turns`, правки параметров — PATCH trip с nullable paths. Route, полный ChangeSet и остальные операции ниже пока проектные. Java DTO не изменены. Этот документ задаёт целевую семантику, не заменяет машинную проверку.

Read-only integration slice в `app/backend.py`: `GET /v1/backend/trips` проксирует личный список на Java `GET /api/v1/trips`, а `GET /v1/backend/trips/{id}` — на Java `GET /api/v1/trips/{id}`. Адрес задаётся переменной окружения `PLACEINRU_BACKEND_URL`; JWT пользователя поступает только в заголовке `Authorization` каждого вызова и передаётся Backend без сохранения. Эти endpoints читают существующие поездки, но не добавляют их к региональному каталогу и не создают/изменяют поездки. Java-контроллеры и DTO в этой интеграции не менялись. Клиент ограничивает timeout и не следует redirects; backend ошибки возвращаются явными кодами.

## Общие правила

- Каждый envelope: `schema_version`, `request_id`, `session_id`, `reference_datetime`, `timezone`. Версия схемы — `1.0`; несовместимые изменения требуют новой major-версии.
- Время события — ISO 8601 с offset плюс IANA timezone объекта. Даты поездки — `YYYY-MM-DD`. Дни считаются включительно, ночи отдельно; авиаприбытие может быть в другой календарный день.
- Деньги — целые minor units и валюта, например `8000000 RUB` = 80 000 рублей. При передаче в Java BigDecimal делить на 100 точно, без binary float. Обменный курс не выдумывать.
- ID — непрозрачные строки, идентификаторы провайдера namespaced. ID региона, объекта, предложения, пункта поездки и Java entity не взаимозаменяемы.
- `null` = неизвестно. В patch отсутствие поля означает «не менять»; очистка — отдельная операция. Пустой список может означать явное отсутствие, если поле помечено confirmed.
- API возвращает status/code/details для ошибок, не только текст. Неподдержанная версия/невалидный ввод — 422, конфликт версии — 409, отсутствующий объект — 404; временная техническая недоступность — 503. `needs_clarification`, `no_candidates`, `partial` — штатные результаты.

## TripRequest и SessionState

| Поле | Тип / смысл |
|---|---|
| `mode` | DISCOVER или PLAN |
| `origin` | `{place_id, name, timezone}`; timezone может быть unknown до геокодирования |
| `destination` | `{region_id, place_id, name}` или null в DISCOVER |
| `dates` | `{start_date, end_date, duration_days, flexibility_days}`; согласованность проверяется |
| `budget` | `{amount_minor, currency, basis, period, hard_limit, includes[]}`; basis group/person, period trip/day |
| `party` | `{adults, children_count, children_ages[]}`; ages неизвестны до уточнения, а не пусты при наличии детей |
| `interests` | нормализованные теги и исходные формулировки |
| `format` | `{tourism_types[], pace, comfort, accessibility_requirements[]}` |
| `transport` | `{allowed_modes[], outbound_time_window, return_required, max_transfers, baggage}` |
| `guide` | `{required, languages[], specializations[], budget_minor}` |
| `constraints` | `{excluded_object_ids[], pinned_item_ids[], excluded_regions[], other[]}` |

SessionState: `state_version`, TripRequest, `slot_metadata`, `pending_question`, `selected_option_id`, `trip_id`, `trip_version`. Для каждого слота: source=user/derived, confidence, confirmed, message_id. История сообщений сама по себе не заменяет состояние.

Критичные слоты для live-поездки: отправление, точные даты/вычислимая длительность, бюджет с областью действия, группа, предпочтения/формат, разрешённый транспорт. Destination обязателен в PLAN и при сохранении в Java. Для DISCOVER известным считается разрешение подобрать направление. Пробелы хранятся как список путей, например `party.adults`. Недостающий возраст спрашивать только если требуется запросу конкретного тарифа.

Reducer не перезаписывает известное значение на null из очередного сообщения. Взаимоисключающие ограничения требуют уточнения. При изменении дат/группы/транспорта зависимые quotes и проверки становятся stale.

## IntentResult

`intents[]`: CREATE_TRIP, ANSWER_QUESTION, CHANGE_TRIP, CHANGE_DATE, CHANGE_TRANSPORT, CHANGE_HOTEL, CHANGE_ATTRACTION, CHANGE_RESTAURANT, ADD_ATTRACTION, REMOVE_ATTRACTION, ADD_GUIDE, REMOVE_GUIDE, CHANGE_BUDGET, REBUILD_ROUTE, SAVE_TRIP, ASK_ABOUT_TRIP. Для unsupported/no-confidence — `UNKNOWN`; это служебное дополнение к ТЗ.

Несколько intent допустимы в одном сообщении. `primary_intent` служит аналитике, но не отменяет остальные действия. Каждая операция содержит confidence и привязку к span исходного сообщения. «Вылет вечером» меняет окно транспорта; CHANGE_DATE добавляется только если изменена календарная дата.

Возвращать `entities`, `slot_updates`, `missing_parameters`, `clarification`, `proposed_changes`. Неоднозначное «замени его» без выбранного UI item_id не применяется к случайной точке.

## Candidate и Offer

Candidate описывает объект, Offer — предложение на даты/группу. Один отель имеет несколько тарифов; один рейс — несколько предложений. Их нельзя сливать только по названию.

Candidate: `object_id`, `kind` (REGION/HOTEL/TRANSPORT/ATTRACTION/RESTAURANT/ACTIVITY/GUIDE), `name`, `region_id`, `coordinates`, `description`, `tags`, `seasonality`, `opening_hours`, `visit_duration_minutes`, `accessibility`, `popularity`, `provenance`.

Provenance: `provider`, `provider_object_id`, `source_url`, `fetched_at`, `valid_until`, `data_mode` (fixture/live/cached/manual), `license_reference`, `attribution`. Неизвестные часы/координаты/рейтинг остаются null. Хранение ограничено условиями конкретного источника.

Offer: `offer_id`, `object_id`, `query_fingerprint`, `availability` (available/unavailable/unknown/on_request), `price`, `booking_url`, `booking_link_type` (offer/search/inquiry), `checked_at`, `expires_at`, `data_mode`.

Price: `amount_minor`, `currency`, `basis` (person/group/room_night/stay/leg), `quantity`, `taxes_included`, `fees_included`, `price_status` (quoted/estimated/unknown), `scope`. Неизвестная price=null; бесплатный объект имеет явный подтверждённый 0. `query_fingerprint` связывает тариф с датами, группой, возрастами, номерами и транспортными параметрами.

Transport details: mode, origin/destination station IDs, departure/arrival с timezone, transfers, baggage, duration и номера сегментов от источника. Hotel details: check-in/out, rooms, occupancy, meal plan, cancellation. Guide details: специализация, язык, регион, слот времени и ссылка заявки. Отсутствие подтверждённой доступности не маскировать ссылкой.

## RouteProposal и BudgetSummary

RouteProposal: `proposal_id`, `trip_version`, `candidate_snapshot_id`, `status`, `region`, `transport_offer_ids[]`, `hotel_offer_ids[]`, `guide_offer_ids[]`, `days[]`, `budget_summary`, `validation`, `explanations[]`.

Каждый day: `day_id`, `date`, `timezone`, `items[]`. Item: `item_id`, `object_id`, `offer_id?`, `kind`, `start_at`, `end_at`, `visit_duration_minutes`, `order`, `coordinates`, `pinned`, `cost_line_ids[]`. Accommodation и транспорт нельзя повторно суммировать из каждого дня.

BudgetSummary: `known_total_minor`, `estimated_total_minor?`, `currency`, `line_items[]`, `unknown_categories[]`, `budget_limit_minor`, `budget_scope`, `complete`, `within_budget` (true/false/null), `calculated_by`, `calculated_at`. Каждая строка стоимости имеет уникальный ID, scope, источник, basis и quantity. `complete=false` не допускает обещания соблюдения полного бюджета. Оценки показываются отдельно от подтверждённых сумм. Production total поступает от Backend.

Validation: `status` (provisional/validated/invalid), `validator`, `checked_at`, `input_version`, `issues[]`. Issue: code, severity, item_ids, explanation, suggested_actions. Проверяются время, часы работы, перемещения, доступность, бюджет, закреплённые ограничения. `validated` требует проверенных обязательных входов; это проверка на момент расчёта, не гарантия будущей покупки.

## Геометрия карты

MapResult: GeoJSON FeatureCollection, `route_version`, `attributions[]`, `legs[]`. Координаты GeoJSON строго `[longitude, latitude]` в WGS84. Точка и сегмент содержат item IDs и day ID.

Leg: `from_item_id`, `to_item_id`, `mode`, `geometry`, `geometry_kind` (routed/schematic/unavailable), `distance_meters`, `duration_seconds`, `provider`, `checked_at`. Нет фактического маршрута — нет routed; прямую линию маркировать schematic, неизвестные duration/distance не заполнять оценками модели. Геометрия может отсутствовать, список дней остаётся доступным.

## ChangeSet: общий путь для чата и ручных изменений

ChangeSet: `change_id`, `idempotency_key`, `base_trip_version`, `source` (chat/manual), `operations[]`, `constraints`, `status` (proposed/validated/applied/rejected).

Операции: `set_trip_field`, `clear_trip_field`, `add_item`, `remove_item`, `replace_item`, `move_item`, `pin_item`, `unpin_item`, `add_guide`, `remove_guide`. Разрешённые field paths задаются схемой; произвольный JSON Patch к внутренним данным запрещён. replace использует `item_id` текущей поездки и ID кандидата/предложения, add — ID известного кандидата, move — целевой день/порядок. Для set есть типизированное value.

Последовательность: resolve targets → preview изменений → пересчитать зависимости → проверить → атомарно применить к ожидаемой версии. При конфликте версии вернуть 409 и свежую версию; не затирать ручные правки. Повторная отправка idempotency key не дублирует точку. Неудачный пакет REMOVE+ADD не должен оставить применённой только половину. Undo создаёт новую версию, а не удаляет историю. Все ключи идемпотентности ограничены сессией/поездкой.

`не увеличивай бюджет` означает верхний предел, привязанный к известному полному итогу текущей версии либо явно заданному лимиту после уточнения; при неизвестной стоимости бот не обещает сохранение суммы.

## Предлагаемые операции API

| Endpoint | Вход | Результат |
|---|---|---|
| `POST /v1/parse` | message + state + reference time | IntentResult + proposed state |
| `POST /v1/classify-intent` | message + контекст | intents и confidence |
| `POST /v1/recommend` | TripRequest + candidates snapshot | ранжированные варианты направлений/наборов |
| `POST /v1/rank` | TripRequest + candidates | IDs, score components, reasons, exclusions |
| `POST /v1/optimize-route` | request + ranked candidates + travel matrix | RouteProposal, unresolved inputs |
| `POST /v1/recommend-guide` | request + реальные гиды | ранжированные гиды |
| `POST /v1/chat/turn` | message, expected_state_version, UI context | orchestration: state, question, options, proposed changes |
| `POST /v1/trips/{id}/changes/preview` | ChangeSet | diff, budget impact, validation |
| `POST /v1/trips/{id}/changes/apply` | validated change + expected version | новая версия либо конфликт |
| `POST /v1/feedback` | event envelope | подтверждение принятия |

Последние chat/trip endpoints живут в dev gateway на стенде; production-владелец — договорённость с Backend. ML-core endpoints stateless: контекст явно передаётся. Gateway хранит сессии и изолирует их; production identity получает от Backend, не доверяет user_id из сообщения. Ключи API никогда не отправляются в браузер. Для долгих внешних запросов предусмотреть job_id и polling/SSE с финальным структурированным ответом, отменой и ограничением времени.

## Пример разбора (синтетический, без реальных предложений)

```json
{
  "schema_version": "1.0",
  "request_id": "demo-turn-1",
  "session_id": "demo-session",
  "reference_datetime": "2026-10-03T12:00:00+03:00",
  "timezone": "Europe/Moscow",
  "status": "needs_clarification",
  "intents": ["CREATE_TRIP"],
  "slot_updates": {
    "mode": "DISCOVER",
    "dates": {"start_date": "2027-07-10", "duration_days": 5},
    "budget": {"amount_minor": 8000000, "currency": "RUB"},
    "interests": ["природа", "музеи"]
  },
  "missing_parameters": ["origin", "party", "budget.basis", "budget.period", "transport.allowed_modes"],
  "clarification": {"text": "Откуда отправляетесь и сколько человек поедет?", "fields": ["origin", "party"]},
  "options": [],
  "proposed_changes": []
}
```

slot_updates — частичный результат, не готовый TripRequest. Метаданные confidence добавляет реализация; пример показывает содержательную часть.

## Сопоставление с Java, без изменения Java

| Новый контракт | Существующий DTO | Ограничение |
|---|---|---|
| origin/destination.name | origin/destination | Канонические ID пока не предусмотрены |
| dates.start_date/end_date | startDate/endDate | Неизвестное направление нельзя сохранить как готовую поездку |
| нормализованный лимит группы/поездки | budget, currency | Перевод minor units → BigDecimal |
| adults/children_count | adults/children | Возраста детей отдельным полем пока отсутствуют |
| format.tourism_types | tourismType | Список нельзя терять в одиночной строке; нужен согласованный mapping |
| transport.allowed_modes | transportType | Несколько видов транспорта не помещаются напрямую |
| guide | guideRequired/guideId | ID партнёра не равен Java guideId |
| item object_id, kind, order, coords | RouteItemCreateRequest | ACTIVITY и taxonomy требуют согласования |
| item start_at/end_at | LocalTime + dayId | Offset/ночной переезд нельзя молча отбросить |
| оценка строки item | estimatedCost | Не заменяет проверенный общий total |
| offer/source/version/map | полей нет | Хранить в ML-черновике до согласования расширения |

Текущие Java-операции создания/редактирования поездки не дают атомарного versioned ChangeSet. Автономный протокол сначала проверяется на dev repository; production-подключение требует реализации коллегами либо согласованного адаптера. Не объявлять эту интеграцию завершённой только из-за сходства названий полей.
