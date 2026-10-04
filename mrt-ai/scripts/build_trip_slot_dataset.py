"""Build a synthetic, family-separated trip-slot extraction benchmark."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "datasets" / "trip-slots-v1.json"
SLOT_PATHS = (
    "origin",
    "destination",
    "dates.start_date",
    "dates.end_date",
    "dates.duration_days",
    "party.total_count",
    "party.has_children",
    "interests",
)

FAMILIES = [
    {
        "id": "train-complete-route",
        "split": "train",
        "expected": {
            "origin": "Москва", "destination": "Московская область",
            "dates.start_date": "2027-07-10", "dates.end_date": "2027-07-12",
            "dates.duration_days": 3, "party.total_count": 2,
            "party.has_children": False, "interests": ["природа"],
        },
        "texts": [
            "Из Москвы в Московскую область с 10.07.2027 по 12.07.2027, нас двое, детей нет. Любим природу.",
            "Нас двое без детей: отправляемся из Москвы в Подмосковье 10.07.2027, возвращаемся 12.07.2027. Интересует природа.",
            "Хотим на природу в Московскую область из Москвы на 10.07.2027—12.07.2027, едем вдвоём, без детей.",
        ],
    },
    {
        "id": "train-discover-active",
        "split": "train",
        "expected": {
            "origin": "Казань", "destination": None,
            "dates.start_date": "2027-08-03", "dates.end_date": "2027-08-07",
            "dates.duration_days": 5, "party.total_count": 3,
            "party.has_children": True, "interests": ["активный", "горы"],
        },
        "texts": [
            "Подбери направление из Казани на 5 дней с 03.08.2027, нас трое, есть дети. Хочется гор и активного отдыха.",
            "Стартуем из Казани 03.08.2027 на пять дней; едет 3 человека с детьми, интересуют горы и активный отдых. Куда поехать?",
            "Не знаем, куда поехать: из Казани, начало 03.08.2027, отдых пять дней, трое с детьми, хочется активности и гор.",
        ],
    },
    {
        "id": "train-date-party",
        "split": "train",
        "expected": {
            "origin": "Санкт-Петербург", "destination": "Сочи",
            "dates.start_date": "2027-09-11", "dates.end_date": "2027-09-14",
            "dates.duration_days": 4, "party.total_count": 1,
            "party.has_children": False, "interests": ["море"],
        },
        "texts": [
            "Из Санкт-Петербурга в Сочи с 11.09.2027 по 14.09.2027 еду одна, без детей, хочу к морю.",
            "Я одна еду из Питера в Сочи с 11.09.2027 до 14.09.2027, интересует море, детей нет.",
            "Планирую поездку Санкт-Петербург — Сочи, даты 11.09.2027—14.09.2027; один взрослый, без детей, хочется моря.",
        ],
    },
    {
        "id": "train-origin-nature",
        "split": "train",
        "expected": {
            "origin": "Москва", "destination": None,
            "dates.start_date": "2027-10-02", "dates.end_date": "2027-10-03",
            "dates.duration_days": 2, "party.total_count": 4,
            "party.has_children": False, "interests": ["природа", "музеи"],
        },
        "texts": [
            "Из Москвы на выходные с 02.10.2027 на два дня, нас четверо, детей нет. Любим природу и музеи, подбери направление.",
            "Подбери место на 02.10.2027 на 2 дня: выезжаем из Москвы, четыре человека без детей, интересуют музеи и природа.",
            "Куда съездить из Москвы? Четверо без детей, природа и музеи, старт 02.10.2027, всего два дня.",
        ],
    },
    {
        "id": "train-destination-interest",
        "split": "train",
        "expected": {
            "origin": "Екатеринбург", "destination": "Карелия",
            "dates.start_date": "2027-11-05", "dates.end_date": "2027-11-06",
            "dates.duration_days": 2, "party.total_count": 3,
            "party.has_children": True, "interests": ["культура"],
        },
        "texts": [
            "Из Екатеринбурга в Карелию с 05.11.2027 по 06.11.2027, нас трое: двое взрослых и ребёнок. Интересует культура.",
            "Планируем Карелию из Екатеринбурга на 05.11.2027—06.11.2027: двое взрослых и один ребёнок, всего три человека, хочется культуры.",
            "Три человека едут в Карелию из Екатеринбурга 05.11.2027 на два дня: двое взрослых и ребёнок, любим культурные места.",
        ],
    },
    {
        "id": "validation-discover-family",
        "split": "validation",
        "expected": {
            "origin": "Сочи", "destination": None,
            "dates.start_date": "2027-12-01", "dates.end_date": "2027-12-04",
            "dates.duration_days": 4, "party.total_count": 2,
            "party.has_children": True, "interests": ["гастрономия"],
        },
        "texts": [
            "Подбери направление из Сочи на четыре дня с 01.12.2027, едем вдвоём с детьми, любим гастрономию.",
            "Хотим поездку из Сочи: начало 01.12.2027, четыре дня, два человека с детьми, интересна местная кухня.",
            "Куда поехать из Сочи на 4 дня начиная 01.12.2027? Нас двое, будут дети, хочется гастрономических впечатлений.",
        ],
    },
    {
        "id": "validation-route-kazan",
        "split": "validation",
        "expected": {
            "origin": "Москва", "destination": "Казань",
            "dates.start_date": "2028-01-10", "dates.end_date": "2028-01-12",
            "dates.duration_days": 3, "party.total_count": 3,
            "party.has_children": False, "interests": ["культура", "гастрономия"],
        },
        "texts": [
            "Из Москвы в Казань с 10.01.2028 по 12.01.2028, нас трое без детей. Интересуют культура и гастрономия.",
            "Три человека без детей едут из Москвы в Казань 10.01.2028—12.01.2028, хотим культурную и гастрономическую поездку.",
            "Казань из Москвы: 10.01.2028 на три дня, едем втроём, детей нет, интересны еда и культура.",
        ],
    },
    {
        "id": "validation-partial-party",
        "split": "validation",
        "expected": {
            "origin": None, "destination": "Алтай",
            "dates.start_date": "2028-02-02", "dates.end_date": "2028-02-08",
            "dates.duration_days": 7, "party.total_count": 4,
            "party.has_children": False, "interests": ["природа", "горы"],
        },
        "texts": [
            "На Алтай с 02.02.2028 на неделю, нас четверо, без детей. Любим природу и горы.",
            "Хочу на Алтай 02.02.2028 на семь дней; четыре человека без детей, интересуют горы и природа.",
            "Алтай, старт 02.02.2028, отдых на 7 дней, едем вчетвером без детей, хочется горной природы.",
        ],
    },
    {
        "id": "validation-single-unknown-destination",
        "split": "validation",
        "expected": {
            "origin": "Санкт-Петербург", "destination": None,
            "dates.start_date": "2028-03-09", "dates.end_date": "2028-03-11",
            "dates.duration_days": 3, "party.total_count": 1,
            "party.has_children": False, "interests": ["активный"],
        },
        "texts": [
            "Подбери направление из Санкт-Петербурга с 09.03.2028 по 11.03.2028, еду один, интересует активный отдых.",
            "Куда съездить одному без детей? Старт из Питера 09.03.2028, вернусь 11.03.2028, люблю активный отдых.",
            "Из Санкт-Петербурга на три дня, 09.03.2028—11.03.2028; один путешественник, активный формат.",
        ],
    },
    {
        "id": "validation-nature-children",
        "split": "validation",
        "expected": {
            "origin": "Москва", "destination": "Байкал",
            "dates.start_date": "2028-04-04", "dates.end_date": "2028-04-05",
            "dates.duration_days": 2, "party.total_count": 3,
            "party.has_children": True, "interests": ["озёра", "природа"],
        },
        "texts": [
            "Из Москвы на Байкал с 04.04.2028 по 05.04.2028, нас трое, один ребёнок. Интересуют озёра и природа.",
            "Байкал из Москвы на 04.04.2028—05.04.2028: двое взрослых и ребёнок, хочется природы и озёр.",
            "Планируем Байкал с 04.04.2028 на два дня, отправляемся из Москвы втроём с ребёнком, любим природу и озёра.",
        ],
    },
    {
        "id": "test-complete-culture",
        "split": "validation",
        "expected": {
            "origin": "Казань", "destination": "Москва",
            "dates.start_date": "2028-05-15", "dates.end_date": "2028-05-17",
            "dates.duration_days": 3, "party.total_count": 2,
            "party.has_children": False, "interests": ["культура", "музеи"],
        },
        "texts": [
            "Из Казани в Москву с 15.05.2028 по 17.05.2028, путешествуем вдвоём без детей. Хотим музеи и культуру.",
            "Нас двое взрослых без детей, едем из Казани в Москву 15.05.2028—17.05.2028; интересны музеи и культурные места.",
            "Москва из Казани на 15.05.2028, назад 17.05.2028. Едем вдвоём, детей нет, любим культуру и музеи.",
        ],
    },
    {
        "id": "test-discover-two",
        "split": "validation",
        "expected": {
            "origin": "Екатеринбург", "destination": None,
            "dates.start_date": "2028-06-06", "dates.end_date": "2028-06-07",
            "dates.duration_days": 2, "party.total_count": 2,
            "party.has_children": False, "interests": ["природа"],
        },
        "texts": [
            "Подбери поездку из Екатеринбурга на 2 дня с 06.06.2028, нас двое, детей нет, хотим на природу.",
            "Не знаем куда поехать: выезжаем из Екатеринбурга 06.06.2028 на два дня, вдвоём без детей, интересует природа.",
            "Куда-нибудь на природу из Екатеринбурга, начало 06.06.2028, отдых два дня, два взрослых без детей.",
        ],
    },
    {
        "id": "test-short-duration",
        "split": "validation",
        "expected": {
            "origin": "Москва", "destination": "Московская область",
            "dates.start_date": "2028-07-01", "dates.end_date": "2028-07-02",
            "dates.duration_days": 2, "party.total_count": 4,
            "party.has_children": True, "interests": ["активный", "природа"],
        },
        "texts": [
            "Из Москвы в Подмосковье на 01.07.2028—02.07.2028: нас четверо, есть дети, любим природу и активный отдых.",
            "Московская область, выезжаем из Москвы 01.07.2028, вернёмся 02.07.2028. Четверо с детьми, хотим активно отдыхать на природе.",
            "На природу в Подмосковье из Москвы на 1 и 2 июля 2028 года, едем вчетвером с детьми, отдых активный.",
        ],
    },
    {
        "id": "test-children-no-interests",
        "split": "validation",
        "expected": {
            "origin": "Санкт-Петербург", "destination": "Карелия",
            "dates.start_date": "2028-08-20", "dates.end_date": "2028-08-24",
            "dates.duration_days": 5, "party.total_count": 3,
            "party.has_children": True, "interests": [],
        },
        "texts": [
            "Едем из Санкт-Петербурга в Карелию на 5 дней с 20.08.2028, нас трое, будут дети.",
            "Карелия из Питера: отправление 20.08.2028, на пять дней, три человека с детьми.",
            "Планирую Карелию из Санкт-Петербурга 20.08.2028 на пять дней; нас трое, один ребёнок.",
        ],
    },
    {
        "id": "test-budget-irrelevant",
        "split": "validation",
        "expected": {
            "origin": "Москва", "destination": None,
            "dates.start_date": "2028-09-03", "dates.end_date": "2028-09-05",
            "dates.duration_days": 3, "party.total_count": 2,
            "party.has_children": False, "interests": ["гастрономия"],
        },
        "texts": [
            "Подбери поездку из Москвы на три дня с 03.09.2028, нас двое без детей, интересует гастрономия.",
            "Из Москвы куда-нибудь на выходные: с 03.09.2028 на 3 дня, вдвоём, детей нет, хочется вкусной еды.",
            "Куда поехать из Москвы 03.09.2028 на три дня? Едем парой без детей, любим гастрономические места.",
        ],
    },
    {
        "id": "test-multi-interest",
        "split": "validation",
        "expected": {
            "origin": "Сочи", "destination": "Москва",
            "dates.start_date": "2028-10-10", "dates.end_date": "2028-10-12",
            "dates.duration_days": 3, "party.total_count": 4,
            "party.has_children": False, "interests": ["культура", "музеи"],
        },
        "texts": [
            "Из Сочи в Москву с 10.10.2028 по 12.10.2028, едем вчетвером без детей, хотим музеи и культуру.",
            "Нас четверо взрослых без детей, направляемся из Сочи в Москву 10.10.2028—12.10.2028; хотим музеи и культурные места.",
            "Москва из Сочи на три дня с 10.10.2028: четыре человека, детей нет, хочется музеев и культуры.",
        ],
    },
    {
        "id": "test-destination-first",
        "split": "test",
        "expected": {
            "origin": "Казань", "destination": "Москва",
            "dates.start_date": "2028-11-14", "dates.end_date": "2028-11-16",
            "dates.duration_days": 3, "party.total_count": 2,
            "party.has_children": False, "interests": ["культура", "музеи"],
        },
        "texts": [
            "Москва из Казани: поездка с 14.11.2028 по 16.11.2028, вдвоём без детей, интересуют культура и музеи.",
            "Планирую Москву из Казани на 14.11.2028—16.11.2028. Едем парой без детей, хотим музеи и культуру.",
            "Едем в Москву из Казани с 14.11.2028 до 16.11.2028, два взрослых без детей, интересны культурные места и музеи.",
        ],
    },
    {
        "id": "test-written-date-range",
        "split": "test",
        "expected": {
            "origin": "Москва", "destination": "Московская область",
            "dates.start_date": "2028-07-01", "dates.end_date": "2028-07-02",
            "dates.duration_days": 2, "party.total_count": 4,
            "party.has_children": True, "interests": ["природа"],
        },
        "texts": [
            "В Подмосковье из Москвы: даты 1 и 2 июля 2028 года. Едем вчетвером с детьми, хочется природы.",
            "Планирую Московскую область из Москвы на 1 по 2 июля 2028 года, четыре человека с детьми, любим природу.",
            "На природу в Подмосковье из Москвы, с 1 по 2 июля 2028 года; нас четверо с детьми.",
        ],
    },
    {
        "id": "test-destination-without-preposition",
        "split": "test",
        "expected": {
            "origin": "Санкт-Петербург", "destination": "Карелия",
            "dates.start_date": "2028-12-05", "dates.end_date": "2028-12-07",
            "dates.duration_days": 3, "party.total_count": 3,
            "party.has_children": True, "interests": ["горы"],
        },
        "texts": [
            "Карелия из Санкт-Петербурга: выезд 05.12.2028, возвращение 07.12.2028, три человека с детьми, хочется гор.",
            "Планирую Карелию из Питера на 05.12.2028—07.12.2028, нас трое с детьми, любим горы.",
            "Едем в Карелию из Санкт-Петербурга с 05.12.2028 до 07.12.2028: два взрослых и ребёнок, интересуют горы.",
        ],
    },
    {
        "id": "test-party-size-forms",
        "split": "test",
        "expected": {
            "origin": "Сочи", "destination": "Алтай",
            "dates.start_date": "2029-01-10", "dates.end_date": "2029-01-12",
            "dates.duration_days": 3, "party.total_count": 2,
            "party.has_children": False, "interests": ["горы"],
        },
        "texts": [
            "Алтай из Сочи с 10.01.2029 по 12.01.2029, едем парой без детей, любим горы.",
            "Планирую Алтай из Сочи на 10.01.2029—12.01.2029; нас двое взрослых, детей нет, интересуют горы.",
            "Из Сочи на Алтай с 10.01.2029 по 12.01.2029: два путешественника без детей, интересуют горы.",
        ],
    },
    {
        "id": "test-numbered-adults",
        "split": "test",
        "expected": {
            "origin": "Екатеринбург", "destination": "Байкал",
            "dates.start_date": "2029-02-15", "dates.end_date": "2029-02-16",
            "dates.duration_days": 2, "party.total_count": 4,
            "party.has_children": False, "interests": [],
        },
        "texts": [
            "Байкал из Екатеринбурга с 15.02.2029 по 16.02.2029: четверо взрослых без детей.",
            "Планируем поездку на Байкал из Екатеринбурга 15.02.2029—16.02.2029, едет четыре взрослых, детей нет.",
            "Едем из Екатеринбурга в Байкал с 15.02.2029 до 16.02.2029, четыре взрослых путешественника без детей.",
        ],
    },
]


def build() -> dict:
    examples = []
    for family in FAMILIES:
        if set(family["expected"]) != set(SLOT_PATHS):
            raise ValueError(f"Family {family['id']} must annotate every tracked slot.")
        for index, text in enumerate(family["texts"], start=1):
            examples.append({
                "id": f'{family["id"]}-{index}',
                "family_id": family["id"],
                "split": family["split"],
                "text": text,
                "pending_question": None,
                "expected": family["expected"],
                "provenance": "synthetic_manual",
            })
    return {
        "dataset_version": "trip-slots-synthetic-v2",
        "data_mode": "fixture",
        "reference_datetime": "2026-10-04T12:00:00+03:00",
        "timezone": "Europe/Moscow",
        "slot_paths": list(SLOT_PATHS),
        "examples": examples,
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(build(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(build()['examples'])} examples)")


if __name__ == "__main__":
    main()
