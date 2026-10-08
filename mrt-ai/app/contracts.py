from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from mrt_ai.contracts.catalog import CandidateBatch, RegionRecommendations


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)


class Dates(Model):
    start_date: date | None = None
    end_date: date | None = None
    duration_days: Annotated[int, Field(strict=True, ge=1, le=90)] | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.start_date and self.end_date:
            days = (self.end_date - self.start_date).days + 1
            if days < 1 or days > 90:
                raise ValueError("Период поездки должен составлять от 1 до 90 дней")
            if self.duration_days is not None and self.duration_days != days:
                raise ValueError("Даты и длительность не совпадают")
        return self


class Budget(Model):
    amount_minor: Annotated[int, Field(strict=True, ge=0, le=100_000_000_000)] | None = None
    currency: Literal["RUB"] = "RUB"
    basis: Literal["group", "person"] | None = None
    period: Literal["trip", "day"] | None = None
    hard_limit: bool = True


class Party(Model):
    total_count: Annotated[int, Field(strict=True, ge=1, le=50)] | None = None
    has_children: bool | None = None
    adults: Annotated[int, Field(strict=True, ge=1, le=30)] | None = None
    children_count: Annotated[int, Field(strict=True, ge=0, le=20)] | None = None
    children_ages: list[Annotated[int, Field(strict=True, ge=0, le=17)]] | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.children_count is not None:
            present = self.children_count > 0
            if self.has_children is not None and self.has_children != present:
                raise ValueError("Наличие детей не совпадает с их количеством")
            self.has_children = present
        if self.adults is not None and self.children_count is not None:
            total = self.adults + self.children_count
            if self.total_count is not None and self.total_count != total:
                raise ValueError("Общее число путешественников не совпадает с составом группы")
            self.total_count = total
        if self.total_count is not None and self.children_count is not None and self.children_count >= self.total_count:
            raise ValueError("В группе должен быть хотя бы один взрослый")
        if self.children_ages is not None and len(self.children_ages) != self.children_count:
            raise ValueError("Число возрастов должно совпадать с количеством детей")
        return self


class Format(Model):
    pace: Literal["relaxed", "balanced", "active"] | None = None


class Transport(Model):
    allowed_modes: list[Literal["TRAIN", "FLIGHT", "CAR", "BUS"]] = Field(default_factory=list)


class Guide(Model):
    required: bool | None = None


class TripRequest(Model):
    mode: Literal["DISCOVER", "PLAN"] = "DISCOVER"
    # Names supplied by the user; canonical IDs are resolved by the future catalogue.
    origin: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    destination: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    destination_region_id: str | None = None
    dates: Dates = Field(default_factory=Dates)
    budget: Budget = Field(default_factory=Budget)
    party: Party = Field(default_factory=Party)
    interests: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=20)
    excluded_interests: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=20)
    format: Format = Field(default_factory=Format)
    transport: Transport = Field(default_factory=Transport)
    guide: Guide = Field(default_factory=Guide)

    @field_validator("origin", "destination")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Название не может быть пустым")
        return value.strip() if value else value

    @model_validator(mode="after")
    def destination_mode(self):
        if self.mode == "DISCOVER" and self.destination is not None:
            raise ValueError("Для выбранного направления используйте режим PLAN")
        if self.destination_region_id is not None and (self.mode != "PLAN" or self.destination is None):
            raise ValueError("ID региона требует выбранного направления")
        if set(self.interests) & set(self.excluded_interests):
            raise ValueError("Интерес не может одновременно быть выбран и исключён")
        return self


class CandidateRankingRequest(Model):
    trip: TripRequest
    candidates: CandidateBatch


class RoutePlannerRequest(CandidateRankingRequest):
    pass


class Message(Model):
    role: Literal["user", "assistant"]
    text: str


class SessionState(Model):
    schema_version: Literal["1.0"] = "1.0"
    session_id: str
    state_version: int = 0
    timezone: str = "Europe/Moscow"
    trip: TripRequest = Field(default_factory=TripRequest)
    messages: list[Message] = Field(default_factory=list)
    pending_question: str | None = None
    missing_parameters: list[str] = Field(default_factory=list)
    slot_metadata: dict = Field(default_factory=dict)
    status: Literal["needs_clarification", "ready_for_search"] = "needs_clarification"
    recommendations: RegionRecommendations | None = None


class SessionCreate(Model):
    timezone: str = "Europe/Moscow"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Неизвестный часовой пояс")
        return value


class Mutation(Model):
    schema_version: Literal["1.0"] = "1.0"
    request_id: str = Field(min_length=8, max_length=100)
    expected_state_version: int = Field(ge=0)


class Turn(Mutation):
    message: str = Field(min_length=1, max_length=3000)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Введите сообщение")
        return value.strip()


class Edit(Mutation):
    # Explicit null clears a slot. Missing keys are not changed.
    updates: dict = Field(min_length=1, max_length=30)
    message: str | None = Field(default=None, min_length=1, max_length=3000)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Сообщение не может быть пустым")
        return value.strip() if value else value


class SelectRegion(Mutation):
    region_id: str = Field(min_length=1, max_length=100)
    catalog_snapshot_id: str = Field(min_length=64, max_length=64)


class RecommendRequest(Model):
    trip: TripRequest


class ParseRequest(Model):
    message: str = Field(min_length=1, max_length=3000)
    state: TripRequest = Field(default_factory=TripRequest)
    pending_question: str | None = None
    reference_datetime: datetime
    timezone: str = "Europe/Moscow"

    @model_validator(mode="after")
    def aware_time(self):
        if self.reference_datetime.utcoffset() is None:
            raise ValueError("reference_datetime должен содержать часовой пояс")
        SessionCreate(timezone=self.timezone)
        return self


class IntentProbe(Model):
    message: str = Field(min_length=1, max_length=3000)
    state: TripRequest = Field(default_factory=TripRequest)
    pending_question: str | None = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Введите сообщение")
        return value.strip()
