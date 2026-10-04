import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from app.catalog_import import NORMALIZER_VERSION, digest, file_hash
from mrt_ai.contracts.catalog import Catalog, RegionOption, RegionRecommendations
from app.dialogue import missing


class CatalogUnavailable(ValueError):
    pass


def normalized(text):
    return " ".join(text.casefold().replace("ё", "е").split())


class RegionCatalog:
    def __init__(self, path: Path):
        self.path = path

    def load(self):
        try:
            catalog = Catalog.model_validate_json(self.path.read_text(encoding="utf-8"))
            payload = {"normalizer_version": catalog.normalizer_version, "regions": [r.model_dump(mode="json") for r in catalog.regions]}
            if catalog.normalizer_version != NORMALIZER_VERSION or digest(payload) != catalog.snapshot_id:
                raise ValueError("Snapshot checksum/version mismatch")
            for region in catalog.regions:
                source_name = region.source.source_file
                if not source_name or Path(source_name).name != source_name:
                    raise ValueError("Invalid source path")
                if file_hash(self.path.parent.parent / source_name) != region.source.source_sha256:
                    raise ValueError("Source card changed")
            return catalog
        except (OSError, ValueError, KeyError) as error:
            raise CatalogUnavailable("Каталог недоступен или устарел. Выполните импорт карточек: python -m app.catalog_import") from error

    @staticmethod
    def resolve(catalog, name):
        return next((r for r in catalog.regions if normalized(name) in {normalized(alias) for alias in r.aliases} | {r.region_id}), None)

    def recommend(self, trip, version=None, today=None):
        unknown = missing(trip)
        if today and trip.dates.start_date and trip.dates.start_date < today:
            unknown = list(dict.fromkeys(["dates.start_date", *unknown]))
        if unknown:
            return RegionRecommendations(status="needs_parameters", based_on_state_version=version, missing_parameters=unknown)
        try:
            catalog = self.load()
        except CatalogUnavailable as error:
            return RegionRecommendations(status="unavailable", based_on_state_version=version, warnings=[str(error)])
        base = {"catalog_snapshot_id": catalog.snapshot_id, "based_on_state_version": version}
        regions = catalog.regions
        if trip.mode == "PLAN":
            region = self.resolve(catalog, trip.destination or "")
            if not region:
                return RegionRecommendations(**base, status="outside_coverage", warnings=["Пока в каталоге только Москва и Московская область. Выбранное направление не заменено автоматически."])
            regions = [region]
        options = []
        for region in regions:
            if region.car_required == "required" and "CAR" not in trip.transport.allowed_modes:
                continue
            values, matched, unmatched = [], [], []
            for interest in trip.interests:
                value = interest_score(region, normalized(interest))
                values.append(value or 0)
                (matched if value and value > 0 else unmatched).append(interest)
            if not any(values):
                continue
            interest_value = sum(values) / len(values)
            month_counts = Counter((trip.dates.start_date + timedelta(days=i)).month for i in range(trip.dates.duration_days))
            season_value = sum(region.month_scores[str(month)] / 5 * count for month, count in month_counts.items()) / sum(month_counts.values())
            duration_value = 1.0 if region.trip_days_min <= trip.dates.duration_days <= region.trip_days_max else .35
            pace_key = "tourism_score_nature" if trip.format.pace == "relaxed" else "tourism_score_active" if trip.format.pace == "active" else "tourism_score_city"
            pace_value = region.scores.get(pace_key, 0) / 5 if trip.format.pace else .5
            components = {"interests": round(.65 * interest_value, 4), "season": round(.15 * season_value, 4), "duration": round(.1 * duration_value, 4), "pace": round(.1 * pace_value, 4)}
            warnings = ["Стоимость поездки и доступность услуг не проверены; бюджетный уровень региона не является ценой."]
            reasons = ["По карточке региона подходят интересы: " + ", ".join(matched),
                       f"Рекомендуемая длительность по карточке: {region.trip_days_min}–{region.trip_days_max} дней.",
                       "Учтены экспертные оценки месяцев поездки; это не прогноз погоды."]
            if duration_value < 1:
                warnings.append("Ваша длительность выходит за рекомендованный в карточке диапазон.")
            if unmatched:
                warnings.append("Нет подтверждённого соответствия интересам: " + ", ".join(unmatched))
            if region.car_required == "preferred" and "CAR" not in trip.transport.allowed_modes:
                warnings.append("По карточке для части поездок желательна машина; доступность конкретных мест ещё не проверена.")
            if trip.excluded_interests:
                warnings.append("Исключённые интересы сохранены. Проверка конкретных объектов выполняется отдельно от выбора региона.")
            options.append(RegionOption(region_id=region.region_id, name=region.name, description=region.description,
                          score=round(sum(components.values()), 4), score_components=components,
                          matched_interests=matched, unmatched_interests=unmatched, reasons=reasons, warnings=warnings, source=region.source))
        options.sort(key=lambda option: (-option.score, option.region_id))
        return RegionRecommendations(**base, status="partial" if options else "no_matches", options=options[:3], warnings=[
            "Это подбор направлений по двум пользовательским карточкам, а не готовые поездки. Реальные билеты, отели и маршрут пока не подключены."
            if options else "В текущем каталоге нет подтверждённого соответствия вашим интересам. Условия не были ослаблены автоматически."])


def interest_score(region, interest):
    mapping = {"природа": "nature", "лес": "nature", "музеи": "culture", "культура": "culture",
               "архитектура": "culture", "экскурсии": "culture", "гастрономия": "food", "еда": "food",
               "город": "city", "семья": "family", "с детьми": "family", "активный": "active"}
    if interest in mapping:
        value = region.scores.get("tourism_score_" + mapping[interest])
        return None if value is None else value / 5
    if interest in ("море", "пляж"):
        return 0 if not region.has_sea else region.scores.get("tourism_score_beach", 0) / 5
    if interest == "озера":
        return region.scores.get("tourism_score_nature", 0) / 5 if "lake" in region.tags else None
    # In particular, hills/parks are not treated as alpine mountains.
    return None
