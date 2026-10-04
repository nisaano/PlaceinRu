"""Explicit importer for the user-supplied tokenized CSV cards.

Every source row is preserved in the audit. Only unambiguous fields are typed.
No HTTP requests, dates/prices inferred from climate, or silent row omissions.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

from mrt_ai.contracts.catalog import Catalog, Region, Source

NORMALIZER_VERSION = "cards-v1"
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
ROOT = Path(__file__).resolve().parent.parent


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstructed(cells):
    # Empty interior cells encode punctuation in these particular exports.
    return re.sub(r"\s+([,.;:])", r"\1", " ".join(cell if cell else "," for cell in cells)).strip()


def parse_card(path: Path):
    records = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader)
        if header[:4] != ["Раздел", "Параметр", "Значение", "Комментарий"]:
            raise ValueError(f"Unexpected header: {path.name}")
        for cells in reader:
            while cells and not cells[-1].strip():
                cells.pop()
            records.append({"line": reader.line_num, "cells": cells, "status": "preserved_unmapped", "mapped_fields": []})
    fields, field_lines, tech = {}, {}, {}

    def set_field(key, value, row):
        if key in fields:
            raise ValueError(f"Duplicate field {key} in {path.name}:{row['line']}")
        fields[key] = value
        field_lines[key] = [row["line"]]
        row["mapped_fields"].append(key)
        row["status"] = "mapped"

    for row in records:
        c = row["cells"]
        if not c:
            continue
        if c[:4] == ["1.", "Общая", "информация", "Название"]:
            set_field("name", reconstructed(c[4:]), row)
        elif c[:6] == ["2.", "Визитная", "карточка", "/", "описание", "Описание"]:
            set_field("description", reconstructed(c[6:]), row)
            row["status"] = "reconstructed_reviewed"
        elif c[:6] == ["1.", "Общая", "информация", "Выход", "к", "морю"]:
            if c[6:] not in (["нет"], ["да"]):
                raise ValueError("Ambiguous sea access")
            set_field("has_sea", c[6] == "да", row)
        elif c[:6] == ["10.", "Технические", "признаки", "backend", "/", "ML"]:
            if len(c) < 8 or c[6] in tech:
                raise ValueError(f"Invalid/duplicate technical field in {path.name}:{row['line']}")
            tech[c[6]] = c[7]
            set_field("technical." + c[6], c[7], row)
        elif c[:6] == ["7.", "Сезонность", "—", "оценка", "по", "месяцам"]:
            month = MONTHS.index(c[6].lower()) + 1
            if not re.fullmatch(r"[0-5]/5", c[7]):
                raise ValueError("Invalid monthly score")
            set_field(f"month_scores.{month}", int(c[7][0]), row)
        elif c[:4] == ["12.", "Семантические", "теги", "semantic_tags"]:
            tags = []
            for cell in c[4:]:
                if not cell:
                    continue
                if not re.fullmatch(r"[a-z][a-z_]*", cell):
                    break  # trailing explanatory comment, retained in audit
                tags.append(cell)
            if len(tags) != len(set(tags)):
                raise ValueError("Duplicate semantic tags")
            set_field("tags", tags, row)
    required = ["region_id", "region_slug", "recommended_trip_days_min", "recommended_trip_days_max", "budget_level", "car_required", "year_round"]
    if any(key not in tech for key in required):
        raise ValueError("Missing required technical fields")
    if tech["year_round"] not in ("true", "false"):
        raise ValueError("Invalid year_round")
    code = tech["region_id"]
    source = Source(provider="user-region-cards", source_file=path.name, source_sha256=file_hash(path), source_lines=field_lines,
                    data_mode="manual", verification="user_supplied_unverified", attribution="Карточка региона, предоставленная пользователем; внешняя актуальность не проверена")
    aliases = [fields["name"], tech["region_slug"]]
    if code == "50":
        aliases.append("Подмосковье")  # present in source search_keywords
    region = Region(region_id=f"ru:region:{code}", code=code, slug=tech["region_slug"], name=fields["name"], aliases=aliases,
                    description=fields["description"], tags=fields["tags"], scores={k: int(v) for k, v in tech.items() if k.startswith("tourism_score_") or k in ("accessibility_score", "public_transport_score", "infrastructure_score", "seasonality_score")},
                    month_scores={str(i): fields[f"month_scores.{i}"] for i in range(1, 13)}, trip_days_min=int(tech["recommended_trip_days_min"]),
                    trip_days_max=int(tech["recommended_trip_days_max"]), budget_level=int(tech["budget_level"]),
                    car_required={"true": "required", "false": "not_required", "preferred": "preferred"}[tech["car_required"]],
                    year_round=tech["year_round"] == "true", has_sea=fields["has_sea"], source=source)
    review = {"source_file": path.name, "source_sha256": source.source_sha256, "row_count": len(records),
              "mapped_count": sum(bool(row["mapped_fields"]) for row in records), "records": records,
              "warnings": ["Свободные описания восстановлены из разбитых ячеек; не используются для числовых ограничений.",
                           "Ненормализованные строки сохранены полностью в records, но не участвуют в рекомендациях.",
                           "Экспертные оценки и бюджетный уровень из карточки не подтверждают стоимость или наличие услуг."]}
    return region, review


def build_catalog(paths):
    regions, reports = [], []
    for path in sorted(paths):
        region, report = parse_card(path)
        regions.append(region)
        reports.append(report)
    payload = {"normalizer_version": NORMALIZER_VERSION, "regions": [r.model_dump(mode="json") for r in sorted(regions, key=lambda r: r.region_id)]}
    catalog = Catalog(**payload, snapshot_id=digest(payload))
    return catalog, {"snapshot_id": catalog.snapshot_id, "normalizer_version": NORMALIZER_VERSION, "sources": reports}


def main():
    paths = list((ROOT / "data").glob("карточка_региона_*_ML_backend.csv"))
    if not paths:
        raise ValueError("No region cards found")
    catalog, report = build_catalog(paths)
    output = ROOT / "data/normalized"
    output.mkdir(exist_ok=True)
    # Catalogue is a single atomic snapshot; readers never observe half a JSON file.
    for name, value in (("import-report.json", report), ("catalog.json", catalog.model_dump(mode="json"))):
        temporary = output / (name + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output / name)
    print(f"Imported {len(catalog.regions)} regions; audited {sum(r['row_count'] for r in report['sources'])} rows; snapshot {catalog.snapshot_id[:12]}")


if __name__ == "__main__":
    main()
