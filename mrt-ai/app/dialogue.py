"""Deterministic Russian baseline. No prices, routes or availability are generated."""
import re
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.contracts import TripRequest

QUESTIONS = {
    "origin": "Из какого города отправляетесь?",
    "destination": "Куда хотите поехать? Или напишите «подбери направление».",
    "dates.start_date": "Когда начнётся поездка? Укажите дату с годом, например 10.07.2027.",
    "dates.duration_days": "На сколько дней хотите поехать?",
    "party.total_count": "Сколько всего человек поедет? Укажите количество от 1 до 4.",
    "party.has_children": "Будут ли в поездке дети? Ответьте «да» или «нет».",
    "interests": "Что вам интересно: природа, горы, музеи, море, гастрономия?",
}
FIELDS = set(QUESTIONS) | {
    "party.total_count", "party.has_children",
    "party.adults", "party.children_count", "mode", "dates.end_date",
    "party.children_ages", "guide.required", "excluded_interests",
    "budget.amount_minor", "budget.basis", "budget.period",
    "format.pace", "transport.allowed_modes",
}
NUMBERS = {"один": 1, "одна": 1, "одного": 1, "два": 2, "двое": 2, "двух": 2,
           "трое": 3, "четверо": 4,
           "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7,
           "восемь": 8, "девять": 9, "десять": 10, "четырнадцать": 14}
NUMBER = r"(?:\d+|" + "|".join(NUMBERS) + r")"
MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
PLACES = {
    "Москва": r"москв(?:а|ы|у|е)", "Московская область": r"подмосковь[ея]|московск\w+ област\w*",
    "Санкт-Петербург": r"санкт-петербург(?:а|е)?|питер(?:а|е)?",
    "Казань": r"казан[ьиь]", "Сочи": r"сочи", "Алтай": r"алта[йея]",
    "Карелия": r"карели[яию]", "Байкал": r"байкал[ае]?", "Екатеринбург": r"екатеринбург[ае]?",
}
TAGS = {"природа": r"природ\w*|лес\w*", "горы": r"гор(?:ы|ах|ам|у|е|ой)?\b|горн\w*",
        "культура": r"культур\w*|архитектур\w*", "активный": r"активн\w*|трекинг\w*|поход\w*",
        "музеи": r"музе\w*", "море": r"мор[ея]|пляж\w*", "гастрономия": r"гастроном\w*|вкусн\w+ ед\w*",
        "озёра": r"озер\w*", "фотография": r"фото\w*", "экскурсии": r"экскурси\w*"}


def number(text):
    return int(text) if text.isdigit() else NUMBERS[text]


def parse_russian_date(day: str, month: str, year: str) -> date:
    return date(int(year), MONTHS[month], int(day))


def missing(trip):
    data = trip.model_dump()
    result = []
    for field in QUESTIONS:
        if field == "party.total_count" and trip.party.total_count is None and trip.party.adults is not None and trip.party.children_count is not None:
            continue
        if field == "party.has_children" and trip.party.children_count is not None:
            continue
        if field == "destination" and trip.mode == "DISCOVER":
            continue
        value = get(data, field)
        if value is None or value == []:
            result.append(field)
    return result


def get(data, path):
    for part in path.split("."):
        data = data[part]
    return data


def put(data, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        data = data[part]
    data[parts[-1]] = value


def reduce_trip(trip, updates, today):
    """Validate the whole proposed state before any storage mutation."""
    invalid = set(updates) - FIELDS
    if invalid:
        raise ValueError("Неизвестные поля: " + ", ".join(sorted(invalid)))
    data = deepcopy(trip.model_dump(mode="json"))
    for path, value in updates.items():
        put(data, path, value)
    party = data["party"]
    if "party.children_count" in updates and "party.has_children" not in updates:
        party["has_children"] = None if party["children_count"] is None else party["children_count"] > 0
    if "party.has_children" in updates:
        if party["has_children"] is False:
            party["children_count"] = 0
        elif party["has_children"] is True and party["children_count"] == 0:
            party["children_count"] = None
        if "party.children_ages" not in updates:
            party["children_ages"] = None
    if "party.adults" in updates and "party.total_count" not in updates:
        party["total_count"] = None
    if any(k in updates for k in ("party.total_count", "party.children_count", "party.has_children")):
        if party["total_count"] is not None and "party.adults" not in updates:
            party["adults"] = None if party["children_count"] is None else party["total_count"] - party["children_count"]
    if updates.get("mode") == "DISCOVER":
        data["destination"] = None
        data["destination_region_id"] = None
    elif updates.get("destination"):
        data["mode"] = "PLAN"
    if "destination" in updates:
        data["destination_region_id"] = None
    if "party.children_count" in updates and "party.children_ages" not in updates:
        data["party"]["children_ages"] = None
    # Only derive after validating individual values, not by silently fixing invalid input.
    dates = data["dates"]
    if "dates.duration_days" in updates and "dates.end_date" not in updates:
        dates["end_date"] = None
    if "dates.start_date" in updates and "dates.end_date" not in updates:
        dates["end_date"] = None
    if "dates.end_date" in updates and "dates.duration_days" not in updates:
        dates["duration_days"] = None
    candidate = TripRequest.model_validate(data)
    d = candidate.dates
    if d.start_date and d.start_date < today:
        raise ValueError("Дата начала уже прошла. Укажите будущую дату с годом.")
    if d.start_date and d.end_date and d.duration_days is None:
        d.duration_days = (d.end_date - d.start_date).days + 1
    elif d.start_date and d.duration_days and d.end_date is None:
        d.end_date = d.start_date + timedelta(days=d.duration_days - 1)
    return TripRequest.model_validate(candidate.model_dump())


def parse(message, trip, pending, reference, timezone):
    text = message.lower().replace("ё", "е").strip()
    updates, notices, intents = {}, [], []
    today = reference.astimezone(ZoneInfo(timezone)).date()
    if re.search(r"подбери (?:сам|направление|регион)|не знаю куда|куда поехать", text):
        updates["mode"] = "DISCOVER"
    for name, pattern in PLACES.items():
        if re.search(r"\bиз\s+(?:" + pattern + r")\b", text):
            updates["origin"] = name
        if re.search(r"\b(?:в|на)\s+(?:" + pattern + r")\b", text):
            updates["destination"] = name
        destination_context = (
            r"(?:^|[,;:]\s*|(?:планирую|хочу|едем|поедем|направляемся)\s+)"
            + r"(?:" + pattern + r")\s+из\b"
        )
        if re.search(destination_context, text):
            updates["destination"] = name
        if re.search(r"\bв\s+(?:" + pattern + r")(?=\s+из\s)", text):
            updates["destination"] = name
    if pending in ("origin", "destination") and re.fullmatch(r"[а-я -]{2,80}", text):
        # A short place answer only; do not swallow unrelated corrections as a city.
        canonical = next((n for n, p in PLACES.items() if re.fullmatch(p, text)), None)
        if canonical:
            updates[pending] = canonical
        elif not updates:
            notices.append("Город не распознан словарём. Укажите его в параметрах поездки; покрытие направления проверяется отдельно.")

    duration = re.search(r"\b(" + NUMBER + r")\s*(?:день|дня|дней|суток)\b", text)
    if duration:
        updates["dates.duration_days"] = number(duration[1])
    elif "две недели" in text:
        updates["dates.duration_days"] = 14
    elif re.search(r"\b(?:на |лучше )?(?:неделю|неделя)\b", text):
        updates["dates.duration_days"] = 7

    found_dates = re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4})\b", text)
    if found_dates:
        try:
            parsed = [date.fromisoformat(d) if "-" in d else datetime.strptime(d, "%d.%m.%Y").date() for d in found_dates]
            updates["dates.start_date"] = parsed[0].isoformat()
            if len(parsed) > 1:
                updates["dates.end_date"] = parsed[1].isoformat()
        except ValueError:
            notices.append("Такой даты нет в календаре. Используйте ДД.ММ.ГГГГ.")
    else:
        written_range = re.search(
            r"\b(?:с\s+)?(\d{1,2})\s*(?:и|по|[-—])\s*(\d{1,2})\s+"
            r"(января|февраля|марта|апреля|мая|июня|июля|августа|"
            r"сентября|октября|ноября|декабря)\s+(\d{4})(?:\s+года?)?\b",
            text,
        )
        written_single = re.search(
            r"\b(?:с\s+)?(\d{1,2})\s+"
            r"(января|февраля|марта|апреля|мая|июня|июля|августа|"
            r"сентября|октября|ноября|декабря)\s+(\d{4})(?:\s+года?)?\b",
            text,
        )
        try:
            if written_range:
                first = parse_russian_date(
                    written_range[1], written_range[3], written_range[4]
                )
                second = parse_russian_date(
                    written_range[2], written_range[3], written_range[4]
                )
                updates["dates.start_date"] = first.isoformat()
                updates["dates.end_date"] = second.isoformat()
            elif written_single:
                parsed = parse_russian_date(
                    written_single[1], written_single[2], written_single[3]
                )
                updates["dates.start_date"] = parsed.isoformat()
        except ValueError:
            notices.append("Такой даты нет в календаре. Используйте ДД.ММ.ГГГГ.")
    if not found_dates and not updates.get("dates.start_date") and (
        "послезавтра" in text or "завтра" in text
    ):
        updates["dates.start_date"] = (today + timedelta(days=2 if "послезавтра" in text else 1)).isoformat()
    elif not found_dates and not updates.get("dates.start_date") and re.search(r"\b(?:летом|зимой|весной|осенью|июл\w*|август\w*|пятниц\w*)\b", text):
        notices.append("Для поиска понадобятся точные даты с годом; пока сезон не заменяет дату.")

    money = re.search(r"(?<![\d.,-])(\d+(?:[ \u00a0]\d{3})*(?:[,.]\d{1,2})?)\s*(тысяч\w*|тыс\.?|к\b|руб\w*|₽)", text)
    unsupported_currency = bool(re.search(r"доллар|евро|usd|eur|[$€]", text))
    if unsupported_currency:
        notices.append("Сейчас поддерживаются рубли. Укажите сумму в RUB; валюту автоматически не пересчитываю.")
    elif re.search(r"-\s*\d[\d ]*\s*(?:руб|тыс|к\b|₽)", text):
        notices.append("Бюджет не может быть отрицательным.")
    elif money:
        amount = Decimal(money[1].replace(" ", "").replace("\u00a0", "").replace(",", "."))
        multiplier = 1000 if money[2].startswith(("ты", "к")) else 1
        if money.start() > 0 and text[money.start()-1] == "-":
            notices.append("Бюджет не может быть отрицательным.")
        else:
            updates["budget.amount_minor"] = int(amount * multiplier * 100)
    elif pending == "budget.amount_minor" and re.fullmatch(r"\d+(?: \d{3})*", text):
        updates["budget.amount_minor"] = int(text.replace(" ", "")) * 100
    if re.search(r"на (?:всех|двоих|всю группу)|общий бюджет", text):
        updates["budget.basis"] = "group"
    elif "на человека" in text:
        updates["budget.basis"] = "person"
    if re.search(r"на всю поездку|за всю поездку|на все путешествие", text):
        updates["budget.period"] = "trip"
    elif re.search(r"в (?:день|сутки)|каждый день", text):
        updates["budget.period"] = "day"

    adults = re.search(r"\b(" + NUMBER + r")\s*взросл", text)
    if not adults and re.search(r"\bвчетвером\b", text):
        updates["party.total_count"] = 4
    elif not adults and re.search(r"\bвтроем\b", text):
        updates["party.total_count"] = 3
    elif not adults and re.search(r"\bвдвоем\b|\bпарой\b", text):
        updates["party.total_count"] = 2
    elif not adults and re.search(r"\bв одиночку\b|\bодин путешественник\b|\bодна путешественница\b", text):
        updates["party.total_count"] = 1
    total = re.search(r"\b(" + NUMBER + r")\s*(?:человек|человека|путешественник\w*)\b", text)
    if total:
        updates["party.total_count"] = number(total[1])
    elif re.search(r"\bнас\s+(" + NUMBER + r")\b", text):
        total = re.search(r"\bнас\s+(" + NUMBER + r")\b", text)
        updates["party.total_count"] = number(total[1])
    if adults:
        updates["party.adults"] = number(adults[1])
        if not re.search(r"\b(?:ребен|дет|ребят)\w*", text):
            updates.setdefault("party.total_count", number(adults[1]))
    elif re.search(r"\bвдвоем\b|\bнас двое\b", text):
        updates["party.adults"] = 2
        updates["party.total_count"] = 2
    elif re.search(r"\bеду один\b|\bеду одна\b", text):
        updates["party.adults"] = 1
        updates["party.total_count"] = 1
    children = re.search(r"\b(" + NUMBER + r")\s*(?:ребен|дет|ребят)", text)
    if "без детей" in text:
        updates["party.children_count"] = 0
    elif children:
        updates["party.children_count"] = number(children[1])
    elif re.search(r"\b(?:с ребенком|и ребенок)\b", text):
        updates["party.children_count"] = 1
    elif re.search(r"\b(?:есть дети|будут дети|с детьми|дети будут)\b", text):
        updates["party.has_children"] = True
    elif re.search(r"\b(?:нет детей|детей нет|детей не будет)\b", text):
        updates["party.children_count"] = 0
    if pending in ("party.adults", "party.children_count", "party.total_count", "dates.duration_days") and re.fullmatch(NUMBER, text):
        updates[pending] = number(text)
    elif pending == "party.total_count" and text in ("вдвоем", "нас двое"):
        updates["party.total_count"] = 2
    elif pending == "party.total_count" and text in ("нас трое", "втроем"):
        updates["party.total_count"] = 3
    elif pending == "party.total_count" and text in ("нас четверо", "вчетвером"):
        updates["party.total_count"] = 4
    if pending == "party.children_count" and text in ("нет", "нет детей"):
        updates[pending] = 0
    elif pending == "party.children_count" and text == "да":
        updates["party.has_children"] = True
        notices.append("Уточните, сколько детей едет: это нужно для состава группы и расчёта стоимости.")
    elif pending == "party.has_children" and text in ("да", "есть", "есть дети", "с детьми", "будут дети"):
        updates["party.has_children"] = True
    elif pending == "party.has_children" and text in ("нет", "нет детей", "детей нет", "без детей", "детей не будет"):
        updates["party.has_children"] = False

    positive, negative = set(trip.interests), set(trip.excluded_interests)
    for tag, pattern in TAGS.items():
        if re.search(r"\b(?:" + pattern + r")\b", text):
            if re.search(r"(?:без|не хочу|не любим|не люблю|исключи)\s+(?:" + pattern + r")", text):
                negative.add(tag)
                positive.discard(tag)
            else:
                positive.add(tag)
                negative.discard(tag)
    if positive != set(trip.interests) or negative != set(trip.excluded_interests):
        updates["interests"] = sorted(positive)
        updates["excluded_interests"] = sorted(negative)
    for pattern, value in [(r"спокойн\w*|неспешн\w*", "relaxed"), (r"сбалансирован\w*|умеренн\w*", "balanced"), (r"активн\w*", "active")]:
        if re.search(r"\b(?:" + pattern + r")\b", text) and not re.search(r"\bне\s+(?:" + pattern + r")", text):
            updates["format.pace"] = value

    modes, excluded = [], []
    for mode, pattern in [("FLIGHT", r"самолет\w*|перелет\w*"), ("TRAIN", r"поезд(?:ом|а|е|у|ов)?\b"), ("CAR", r"машин\w*|автомобил\w*"), ("BUS", r"автобус\w*")]:
        if re.search(pattern, text):
            if re.search(r"(?:без|не на|не хочу)\s+(?:" + pattern + r")", text):
                excluded.append(mode)
            else:
                modes.append(mode)
    if "любой транспорт" in text or (pending == "transport.allowed_modes" and text == "любой"):
        modes = ["TRAIN", "FLIGHT", "CAR", "BUS"]
    if modes or excluded:
        updates["transport.allowed_modes"] = [m for m in (modes or trip.transport.allowed_modes or ["TRAIN", "FLIGHT", "CAR", "BUS"]) if m not in excluded]
    if re.search(r"без гида|гид не нужен|убери гида", text):
        updates["guide.required"] = False
    elif re.search(r"нужен гид|добавь гида|с гидом", text):
        updates["guide.required"] = True

    # Detect requests for future modules without pretending they were executed.
    unsupported = re.search(r"(?:поменяй|замени|убери|добавь).*(?:отель|ресторан|экскурси|активност)|перестрой маршрут|забронируй|сохрани поездку", text)
    if unsupported:
        notices.append("Пока доступно изменение параметров поездки. Подбор и редактирование конкретных услуг появятся на следующем этапе.")
    for prefix, intent in [("dates.", "CHANGE_DATE"), ("budget.", "CHANGE_BUDGET"), ("transport.", "CHANGE_TRANSPORT")]:
        if any(k.startswith(prefix) for k in updates):
            intents.append(intent)
    if "guide.required" in updates:
        intents.append("ADD_GUIDE" if updates["guide.required"] else "REMOVE_GUIDE")
    if not intents:
        intents = ["ANSWER_QUESTION" if updates and pending else "CHANGE_TRIP" if updates else "UNKNOWN"]
    if not any(trip.model_dump()[k] for k in ("origin", "destination", "interests")) and updates:
        intents = ["CREATE_TRIP", *intents]
    return {"updates": updates, "intents": intents, "notices": notices, "reference_date": today.isoformat(), "parser": "rules-v1"}
