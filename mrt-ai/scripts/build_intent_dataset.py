"""Build the versioned synthetic pilot set with family-separated splits."""
import json
from pathlib import Path

from mrt_ai.nlp.intent.taxonomy import INTENTS

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "datasets" / "intent-v1.json"

# Each family is kept wholly within one split. Wording families are independent
# templates; the generated dataset is only a pipeline smoke set.
FAMILIES = {
    "CHANGE_DATE": [
        ["Перенеси поездку на 10.07.2027", "Измени даты поездки на 10.07.2027", "Давай поедем с 10.07.2027"],
        ["Поездка будет с 01.08.2027 по 03.08.2027", "Поставь даты с 01.08.2027 по 03.08.2027", "Запланируй поездку на 01.08.2027—03.08.2027"],
        ["Хочу уехать на неделю с 10.09.2027", "Перенеси начало поездки на 10.09.2027", "Даты отдыха: 10.09.2027 и 16.09.2027"],
        ["Поедем через 2 дня", "Начало поездки — 10.10.2027", "Сделай поездку на пять дней"],
        ["Давай с 15.06.2027 по 17.06.2027", "Замени даты отдыха на 15.06.2027—17.06.2027", "Планируем поездку с 15.06.2027"],
    ],
    "CHANGE_BUDGET": [
        ["Бюджет 50 тысяч на всю поездку", "Установи общий бюджет 50 тысяч рублей", "На поездку готовы потратить 50 тысяч на всех"],
        ["Бюджет 30 тысяч рублей на человека", "Поставь лимит 30 тысяч на одного", "На каждого бюджет 30 000 рублей"],
        ["Увеличь бюджет до 80 тысяч рублей", "Пусть поездка стоит не больше 80 тыс.", "Снизь общий бюджет до 45 тысяч"],
        ["Можем потратить 12 тысяч рублей в день", "Бюджет на сутки — 12 тысяч", "Рассчитывай по 10 000 рублей в день"],
        ["У нас общий бюджет 100000 рублей", "На всех выделено 70 тысяч", "Ограничь расходы на поездку суммой 25 тыс. рублей"],
    ],
    "CHANGE_TRANSPORT": [
        ["Поедем на поезде", "Выбери поезд как транспорт", "Предпочитаем добираться поездом"],
        ["Хочу ехать на машине", "Разреши поездку на автомобиле", "Лучше поедем на машине"],
        ["Рассматриваем самолёт", "Добавь перелёт в варианты транспорта", "Можно лететь самолётом"],
        ["На автобусе ехать не хочу", "Исключи автобус", "Убери автобус из допустимого транспорта"],
        ["Подойдут поезд и самолёт", "Разреши поезд или автомобиль", "Для поездки рассматриваем автобус"],
    ],
    "ADD_GUIDE": [
        ["Добавь гида в поездку", "Нужен гид", "Хочу путешествовать с гидом"],
        ["Подбери экскурсию с гидом", "Включи услуги гида", "Добавь сопровождение гида"],
        ["Пусть нас сопровождает гид", "Нам нужен местный гид", "Закажи в план гида"],
        ["Можно добавить гида к маршруту", "Хочу экскурсовода", "Предусмотри гида на поездку"],
        ["Сделай вариант с гидом", "Добавь экскурсовода", "Гид обязателен"],
    ],
    "REMOVE_GUIDE": [
        ["Убери гида из поездки", "Гид не нужен", "Исключи услуги гида"],
        ["Не хочу экскурсию с гидом", "Сделай поездку без гида", "Удали гида из плана"],
        ["Убери экскурсовода", "Мы поедем самостоятельно без гида", "Не добавляй услуги гида"],
        ["Отмени гида", "Можно без экскурсовода", "Гид нам не требуется"],
        ["Исключи сопровождение гида", "Передумали насчёт гида", "Оставь маршрут без гида"],
    ],
    "ANSWER_QUESTION": [
        ["Казань", "Москва", "Санкт-Петербург"],
        ["Казань", "Москва", "Сочи"],
        ["Екатеринбург", "Карелия", "Алтай"],
        ["Санкт-Петербург", "Казань", "Москва"],
        ["Алтай", "Сочи", "Екатеринбург"],
    ],
    "CHANGE_TRIP": [
        ["Хочу больше природы в поездке", "Добавь интерес к музеям", "Исключи гастрономию"],
        ["Пусть отдых будет активным", "Сделай темп поспокойнее", "Предпочитаю сбалансированную поездку"],
        ["Нас будет четверо", "Едем вдвоём без детей", "Добавь одного ребёнка"],
        ["Подбери направление для отдыха", "Давай спланируем путешествие", "Хочу поездку на природу"],
        ["Не включай ночные переезды", "Добавь интерес к культуре", "Хочу спокойный семейный отдых"],
    ],
    "UNKNOWN": [
        ["Какая сегодня погода?", "Расскажи анекдот", "Спасибо за помощь"],
        ["Привет!", "Который сейчас час?", "Что нового?"],
        ["Как дела?", "Расскажи про историю кино", "Назови случайное число"],
        ["Ладно", "Понятно", "Хорошо"],
        ["Можешь посоветовать книгу?", "Кто выиграл матч?", "Расскажи интересный факт"],
    ],
}

CREATE_FAMILIES = [
    [
        ("Составь поездку с 10.07.2027 на пять дней", ["CREATE_TRIP", "CHANGE_DATE"]),
        ("Хочу спланировать отдых с 10.07.2027 на неделю", ["CREATE_TRIP", "CHANGE_DATE"]),
        ("Давай начнём новую поездку с 10.07.2027", ["CREATE_TRIP", "CHANGE_DATE"]),
    ],
    [
        ("Запланируй путешествие на 01.08.2027, бюджет 50 тысяч рублей", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_BUDGET"]),
        ("Создай поездку с 01.08.2027 и бюджетом 50 тыс.", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_BUDGET"]),
        ("Хочу начать план поездки на 01.08.2027, потратить можно 50 тысяч", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_BUDGET"]),
    ],
    [
        ("Подбери направление на неделю с 10.09.2027, люблю природу", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRIP"]),
        ("Начнём планировать поездку на 10.09.2027 для отдыха на природе", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRIP"]),
        ("Хочу новую поездку с 10.09.2027 и интересуюсь музеями", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRIP"]),
    ],
    [
        ("Создай план поездки с 15.06.2027, поедем на поезде", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRANSPORT"]),
        ("Спланируй путешествие с 15.06.2027 на поезде", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRANSPORT"]),
        ("Давай составим поездку на 15.06.2027, добираться будем поездом", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRANSPORT"]),
    ],
    [
        ("Хочу новую поездку на 10.10.2027, нас двое, без детей", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRIP"]),
        ("Помоги спланировать путешествие с 10.10.2027 для семьи с детьми", ["CREATE_TRIP", "CHANGE_DATE", "CHANGE_TRIP"]),
        ("Давай начнём поездку с 10.10.2027 и добавим гида", ["CREATE_TRIP", "CHANGE_DATE", "ADD_GUIDE"]),
    ],
]


def build() -> dict:
    records = []
    for intent, families in FAMILIES.items():
        for family_index, utterances in enumerate(families):
            split = "train" if family_index < 3 else "validation" if family_index == 3 else "test"
            pending = "origin" if intent == "ANSWER_QUESTION" else None
            for variation_index, text in enumerate(utterances):
                records.append({
                    "id": f"{intent.lower()}-{family_index + 1}-{variation_index + 1}",
                    "family_id": f"{intent.lower()}-family-{family_index + 1}",
                    "split": split,
                    "text": text,
                    "pending_question": pending,
                    "previous_trip": "partial",
                    "labels": [intent],
                    "provenance": "synthetic_manual",
                })
    for family_index, utterances in enumerate(CREATE_FAMILIES):
        split = "train" if family_index < 3 else "validation" if family_index == 3 else "test"
        for variation_index, (text, labels) in enumerate(utterances):
            records.append({
                "id": f"create-trip-{family_index + 1}-{variation_index + 1}",
                "family_id": f"create-trip-family-{family_index + 1}",
                "split": split,
                "text": text,
                "pending_question": None,
                "previous_trip": "empty",
                "labels": sorted(labels),
                "provenance": "synthetic_manual",
            })

    if any(label not in INTENTS for row in records for label in row["labels"]):
        raise ValueError("Dataset contains a label outside the MRT-AI taxonomy.")
    return {
        "dataset_version": "intent-synthetic-v1",
        "annotation_version": "intent-taxonomy-v1",
        "data_mode": "fixture",
        "description": (
            "Synthetic manually annotated pipeline smoke set. It is not a real-user "
            "benchmark and must not be used to claim production classifier quality."
        ),
        "labels": list(INTENTS),
        "split_policy": "grouped by family_id; train/validation/test wording families are disjoint",
        "examples": records,
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['examples'])} synthetic examples to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
