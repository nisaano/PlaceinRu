"""Shared catalogue and search contracts owned by the MRT-AI domain."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)


Score = Annotated[int, Field(strict=True, ge=0, le=5)]
Kind = Literal["REGION", "HOTEL", "TRANSPORT", "ATTRACTION", "RESTAURANT", "ACTIVITY", "GUIDE"]
DataMode = Literal["manual", "fixture", "cached", "live"]


class Source(CatalogModel):
    provider: str
    source_file: str | None = None
    source_url: HttpUrl | None = None
    source_sha256: str | None = None
    source_lines: dict[str, list[int]] = Field(default_factory=dict)
    data_mode: DataMode
    verification: Literal["user_supplied_unverified", "synthetic", "provider_reported"]
    license_reference: str | None = None
    attribution: str
    checked_at: AwareDatetime | None = None


class Region(CatalogModel):
    region_id: str
    code: str
    slug: str
    name: str
    aliases: list[str]
    description: str
    tags: list[str]
    scores: dict[str, Score]
    month_scores: dict[str, Score]
    trip_days_min: int = Field(ge=1, le=90)
    trip_days_max: int = Field(ge=1, le=90)
    car_required: Literal["required", "preferred", "not_required"]
    budget_level: int = Field(ge=1, le=5)
    year_round: bool
    has_sea: bool
    source: Source

    @model_validator(mode="after")
    def consistent(self):
        if self.trip_days_min > self.trip_days_max:
            raise ValueError("Invalid duration range")
        if set(self.month_scores) != {str(i) for i in range(1, 13)}:
            raise ValueError("Expected all twelve month scores")
        return self


class Catalog(CatalogModel):
    schema_version: Literal["1.0"] = "1.0"
    normalizer_version: str
    snapshot_id: str
    regions: list[Region]

    @model_validator(mode="after")
    def unique(self):
        for attribute in ("region_id", "slug"):
            values = [getattr(r, attribute) for r in self.regions]
            if len(values) != len(set(values)):
                raise ValueError("Duplicate region identifiers")
        return self


class RegionOption(CatalogModel):
    region_id: str
    name: str
    description: str
    score: float
    score_components: dict[str, float]
    matched_interests: list[str]
    unmatched_interests: list[str]
    reasons: list[str]
    warnings: list[str]
    source: Source
    budget_status: Literal["unknown"] = "unknown"
    total_price_minor: None = None


class RegionRecommendations(CatalogModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["needs_parameters", "partial", "no_matches", "outside_coverage", "unavailable"]
    catalog_snapshot_id: str | None = None
    based_on_state_version: int | None = None
    ranking_version: str = "region-rules-v1"
    options: list[RegionOption] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_parameters: list[str] = Field(default_factory=list)


class Coordinates(CatalogModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class Candidate(CatalogModel):
    object_id: str
    kind: Kind
    region_id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    coordinates: Coordinates | None = None
    opening_hours: str | None = None
    visit_duration_minutes: int | None = Field(default=None, ge=1)
    rating: float | None = Field(default=None, ge=0, le=5, allow_inf_nan=False)
    source: Source


class FixturePlaceCatalog(CatalogModel):
    schema_version: Literal["1.0"]
    data_mode: Literal["fixture"]
    description: str
    coordinate_notice: str
    candidates: list[Candidate]

    @model_validator(mode="after")
    def synthetic_only(self):
        identifiers = [candidate.object_id for candidate in self.candidates]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Duplicate fixture candidate IDs")
        for candidate in self.candidates:
            source = candidate.source
            if (
                not candidate.object_id.startswith("fixture:")
                or not candidate.name.startswith("ДЕМО · ")
                or source.data_mode != "fixture"
                or source.verification != "synthetic"
                or candidate.coordinates is None
                or not (candidate.opening_hours or "").startswith("ДЕМО:")
            ):
                raise ValueError("Fixture places must be labelled synthetic, demo-only and have demo schedule/coordinates")
        return self


class Price(CatalogModel):
    amount_minor: int = Field(strict=True, ge=0)
    currency: Literal["RUB"] = "RUB"
    basis: Literal["person", "group", "room_night", "stay", "leg"]
    quantity: int = Field(strict=True, ge=1)
    taxes_included: bool | None = None
    fees_included: bool | None = None
    status: Literal["quoted", "estimated"]


class Offer(CatalogModel):
    offer_id: str
    object_id: str
    query_fingerprint: str
    data_mode: DataMode
    availability: Literal["available", "unavailable", "unknown", "on_request"] = "unknown"
    price: Price | None = None
    booking_url: HttpUrl | None = None
    booking_link_type: Literal["offer", "search", "inquiry"] | None = None
    checked_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def consistent(self):
        if bool(self.booking_url) != bool(self.booking_link_type):
            raise ValueError("URL and link type must be supplied together")
        if self.data_mode == "fixture" and self.booking_url:
            raise ValueError("Synthetic offers must not contain booking links")
        if self.expires_at and (not self.checked_at or self.expires_at <= self.checked_at):
            raise ValueError("Invalid offer validity period")
        return self


class CandidateQuery(CatalogModel):
    region_id: str
    data_mode: Literal["manual", "fixture"] = "manual"
    kinds: list[Kind] = Field(default_factory=lambda: ["HOTEL", "TRANSPORT", "ATTRACTION", "RESTAURANT", "ACTIVITY", "GUIDE"], max_length=7)
    excluded_tags: list[str] = Field(default_factory=list, max_length=20)
    start_date: date | None = None
    end_date: date | None = None
    adults: int | None = Field(default=None, ge=1, le=30)
    children_ages: list[Annotated[int, Field(ge=0, le=17)]] | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date precedes start date")
        return self


class PlaceSearchRequest(CatalogModel):
    region_id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=500)
    data_mode: Literal["fixture"]
    ranking_method: Literal["bm25", "embedding"] = "bm25"
    top_k: int = Field(default=5, ge=1, le=20)
    kinds: list[Literal["HOTEL", "TRANSPORT", "ATTRACTION", "RESTAURANT", "ACTIVITY", "GUIDE"]] = Field(
        default_factory=lambda: ["HOTEL", "TRANSPORT", "ATTRACTION", "RESTAURANT", "ACTIVITY", "GUIDE"],
        max_length=6,
    )
    excluded_tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Search query must not be blank")
        return value


class PlaceSearchHit(CatalogModel):
    candidate: Candidate
    score: float = Field(ge=0, allow_inf_nan=False)
    matched_terms: list[str]


class PlaceSearchResponse(CatalogModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["partial", "no_candidates", "outside_coverage"]
    data_mode: Literal["fixture"]
    ranking_version: Literal["bm25-lexical-v1", "sbert-large-nlu-ru-mean-v1"] = "bm25-lexical-v1"
    snapshot_id: str
    results: list[PlaceSearchHit] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CandidateBatch(CatalogModel):
    schema_version: Literal["1.0"] = "1.0"
    provider: str
    data_mode: DataMode
    status: Literal["partial", "no_candidates", "outside_coverage"]
    snapshot_id: str
    query_fingerprint: str
    candidates: list[Candidate] = Field(default_factory=list)
    offers: list[Offer] = Field(default_factory=list)
    unavailable_kinds: list[Kind] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def references(self):
        ids = [c.object_id for c in self.candidates]
        offers = [o.offer_id for o in self.offers]
        if len(ids) != len(set(ids)) or len(offers) != len(set(offers)):
            raise ValueError("Duplicate candidate or offer IDs")
        if any(c.source.data_mode != self.data_mode for c in self.candidates):
            raise ValueError("Mixed candidate data modes")
        if any(o.object_id not in ids or o.data_mode != self.data_mode or o.query_fingerprint != self.query_fingerprint for o in self.offers):
            raise ValueError("Offer does not match batch/query")
        return self
