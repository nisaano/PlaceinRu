"""Multi-label intent contract shared with Misha's current parser/API."""

INTENTS = (
    "CREATE_TRIP",
    "CHANGE_DATE",
    "CHANGE_BUDGET",
    "CHANGE_TRANSPORT",
    "ADD_GUIDE",
    "REMOVE_GUIDE",
    "ANSWER_QUESTION",
    "CHANGE_TRIP",
    "UNKNOWN",
)

INTENT_DESCRIPTIONS = {
    "CREATE_TRIP": "Начинается новая поездка; совместима с предметным intent из того же сообщения.",
    "CHANGE_DATE": "Пользователь сообщает или меняет даты поездки/длительность.",
    "CHANGE_BUDGET": "Пользователь сообщает или меняет бюджет.",
    "CHANGE_TRANSPORT": "Пользователь сообщает или меняет допустимый транспорт.",
    "ADD_GUIDE": "Пользователь просит добавить гида.",
    "REMOVE_GUIDE": "Пользователь просит убрать гида.",
    "ANSWER_QUESTION": "Пользователь отвечает на ожидающий уточняющий вопрос.",
    "CHANGE_TRIP": "Другая поддерживаемая правка параметров поездки.",
    "UNKNOWN": "Поддерживаемое действие не определено.",
}


def validate_intents(labels: list[str]) -> list[str]:
    unknown = set(labels) - set(INTENTS)
    if unknown:
        raise ValueError(f"Unknown intent labels: {sorted(unknown)}")
    return sorted(set(labels))
