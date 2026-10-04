# Структура ML-системы mrt-ai

**mrt-ai** — имя локальной ML-системы и принадлежащего проекту pipeline. **Миша** — диалоговый помощник и API-фасад над этим pipeline. SBERT и RuBERT — внешние предобученные модели: их веса не являются собственной моделью mrt-ai.

## Карта проекта

```text
mrt-ai/
  app/                         # API Миши, диалог, Backend adapter и хранилище
  mrt_ai/                      # собственная логика ML pipeline
    contracts/catalog.py       # общие доменные контракты для API и pipeline
    nlp/intent/                 # taxonomy, dataset loader, train and inference
    nlp/slot_extraction.py     # проверка и загрузка trip-slot benchmark
    retrieval/
      pipeline.py              # выбор стратегии и единая выдача MRT-AI
      bm25.py                  # внутренний лексический baseline
      encoders/
        sbert.py               # адаптер внешнего SBERT для эмбеддингов
  models/                      # локальный кэш весов, исключён из Git
    embeddings/
      sbert_large_nlu_ru/      # ai-forever/sbert_large_nlu_ru, MIT
    encoders/
      rubert_tiny2/             # cointegrated/rubert-tiny2 pretrained weights, MIT
    classifiers/
      misha-intent-rubert-tiny2/ # MRT-AI fine-tuned experimental weights
  data/
    datasets/
      intent-v1.json           # 135 synthetic multi-label examples, family split
      trip-slots-v1.json       # 63 synthetic requests, benchmark schema v2
    fixtures/                  # только явно синтетические тестовые данные
    normalized/                # нормализованные карточки регионов
    runtime/                   # локальное состояние SQLite; сохранять
    *.csv                      # исходные карточки пользователя; сохранять
  scripts/                     # локальный запуск, загрузчики и evaluator
  schemas/                     # экспортированные API-контракты
  tests/                       # регрессионные, контрактные и API-тесты
  docs/                        # требования, архитектура, оценка и журнал
```

## Кто за что отвечает

| Компонент | Принадлежит | Статус |
|---|---|---|
| Общие Candidate/Offer/search contracts | mrt-ai | `mrt_ai/contracts/catalog.py`; используются API и retrieval |
| `MrtAiRetrievalPipeline` | mrt-ai | Реализован; выбирает BM25 или embedding retrieval |
| BM25 | mrt-ai | Реализованный воспроизводимый default |
| SBERT encoder | Внешние веса, адаптер mrt-ai | Локальный CPU encoder; MIT, бесплатно, 1.7 GB |
| RuBERT-tiny2 encoder | Внешние веса, классификатор mrt-ai | MIT encoder загружен локально; закреплён revision и verified SHA-256 |
| Intent taxonomy/dataset | mrt-ai | 9 labels, 135 synthetic examples; 81 train / 27 validation / 27 test, grouped by wording family |
| `mrt-ai-misha-intent-rubert-tiny2` | mrt-ai | Fine-tuned multi-label experimental checkpoint; test macro F1 0.6266 против rules-v1 0.7797 на этом synthetic pilot |
| Миша | mrt-ai | Ответы и изменение состояния — deterministic `rules-v1`; только local developer chat дополнительно сравнивает экспериментальный classifier |

Предобученные encoder-веса — внешний компонент; pipeline, контракт, labels, обученная classification head и inference-код принадлежат mrt-ai. RuBERT-tiny2 сам по себе не является классификатором. Обученный checkpoint — ранний эксперимент на синтетике: пока он хуже `rules-v1`. Локальный dev-чат включает structured TripRequest-форму и показывает передаваемый JSON; это не ML slot extraction. Свободные фразы отдельно сравниваются через `rules-v1` и classifier. Classifier не управляет диалогом или состоянием поездки; сравнительный endpoint доступен только при запуске через `scripts.dev`.

## Лицензии и стоимость

- [ai-forever/sbert_large_nlu_ru](https://huggingface.co/ai-forever/sbert_large_nlu_ru): карточка модели указывает MIT. Модель открытая и не требует платы за вызовы; скачивание/работа локальны. Основные затраты — диск, RAM и CPU-время.
- [cointegrated/rubert-tiny2](https://huggingface.co/cointegrated/rubert-tiny2): карточка модели указывает MIT и описывает компактную русскоязычную основу для embeddings или дообучения. За локальное использование платы нет.
- Модели хранятся в `models/`, не коммитятся; версия, роль, лицензия и контрольная сумма для SBERT записаны в локальном manifest. API загружает веса только с диска и явно сообщает, если они отсутствуют.
- Лицензия весов не отменяет проверку лицензий зависимостей, требований атрибуции и условий распространения весов при публикации проекта.

## Эксперимент intent-классификации и дальнейшая работа

Начальный pipeline воспроизводится командами:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\venv\Scripts\python.exe -B -m scripts.build_intent_dataset
.\venv\Scripts\python.exe -B -m scripts.download_intent_encoder
.\venv\Scripts\python.exe -B -m scripts.train_intent_classifier --epochs 10
.\venv\Scripts\python.exe -B -m scripts.evaluate_intent_classifier
```

Следующий шаг — собрать вручную размеченные, обезличенные сообщения, не смешивать семейства перефразировок между split и расширить независимый test. Повторно сравнить macro/per-intent F1 и exact match с `rules-v1`. До прохождения целевого порога и проверки holdout classifier не подключать к Мише.

Для извлечения параметров из свободного текста `rules-v1` остаётся рабочим baseline. Добавлены regression cases на направление перед городом отправления, разговорные выражения размера группы и даты, записанные словами. `data/datasets/trip-slots-v1.json` версии v2 имеет 63 синтетические фразы, 8 нормализованных слотов и split 15/33/15. Текущая новая test-группа даёт 15/15 exact match; она мала и синтетична, поэтому этот результат не является мерой качества на пользователях. До обучения slot-модели требуется реальная разрешённая разметка.
