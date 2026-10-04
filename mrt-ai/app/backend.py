"""Read-only client for the existing Java trip API."""
import os
import re
from collections.abc import Callable

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class BackendError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class BackendModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


MoneyValue = str | int | float | None


class BackendRouteItem(BackendModel):
    id: int | None = None
    dayId: int | None = None
    type: str | None = None
    objectId: str | None = None
    startTime: str | None = None
    endTime: str | None = None
    durationMinutes: int | None = None
    order: int | None = None
    estimatedCost: MoneyValue = None
    notes: str | None = None


class BackendTripDay(BackendModel):
    id: int | None = None
    date: str | None = None
    dayNumber: int | None = None
    items: list[BackendRouteItem] = Field(default_factory=list)


class BackendTrip(BackendModel):
    id: int
    userId: int | None = None
    title: str | None = None
    status: str | None = None
    origin: str | None = None
    destination: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    budget: MoneyValue = None
    currency: str | None = None
    adults: int | None = None
    children: int | None = None
    tourismType: str | None = None
    transportType: str | None = None
    guideRequired: bool | None = None
    guideId: int | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    days: list[BackendTripDay] = Field(default_factory=list)


class BackendTripsClient:
    def __init__(
        self,
        base_url: str | None = None,
        transport_factory: Callable[[], httpx.BaseTransport] | None = None,
    ):
        configured_url = base_url if base_url is not None else os.getenv("PLACEINRU_BACKEND_URL")
        if not configured_url:
            self.base_url = None
        else:
            try:
                url = httpx.URL(configured_url)
            except httpx.InvalidURL as error:
                raise ValueError("PLACEINRU_BACKEND_URL must be a valid HTTP(S) base URL") from error
            if (
                url.scheme not in ("http", "https")
                or not url.host
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError("PLACEINRU_BACKEND_URL must be an HTTP(S) base URL without credentials or query")
            self.base_url = str(url).rstrip("/")
        self.transport_factory = transport_factory

    @property
    def configured(self) -> bool:
        return self.base_url is not None

    @staticmethod
    def validate_authorization(authorization: str | None) -> str:
        if not authorization or not re.fullmatch(r"(?i)Bearer\s+\S+", authorization):
            raise BackendError(401, "BACKEND_TOKEN_REQUIRED", "Передайте JWT пользователя в заголовке Authorization: Bearer.")
        return authorization

    def list_trips(self, authorization: str | None) -> list[BackendTrip]:
        return self._get("/api/v1/trips", authorization, list[BackendTrip])

    def get_trip(self, trip_id: int, authorization: str | None) -> BackendTrip:
        if trip_id < 1:
            raise BackendError(422, "INVALID_TRIP_ID", "ID поездки должен быть положительным числом.")
        return self._get(f"/api/v1/trips/{trip_id}", authorization, BackendTrip)

    def _get(self, path: str, authorization: str | None, response_type):
        token = self.validate_authorization(authorization)
        if not self.base_url:
            raise BackendError(503, "BACKEND_NOT_CONFIGURED", "Адрес Java Backend не настроен в mrt-ai.")
        try:
            with httpx.Client(
                timeout=httpx.Timeout(5.0),
                follow_redirects=False,
                transport=self.transport_factory() if self.transport_factory else None,
            ) as client:
                response = client.get(
                    self.base_url + path,
                    headers={"Authorization": token, "Accept": "application/json"},
                )
        except httpx.TimeoutException as error:
            raise BackendError(503, "BACKEND_TIMEOUT", "Java Backend не ответил за отведённое время.") from error
        except httpx.RequestError as error:
            raise BackendError(503, "BACKEND_UNAVAILABLE", "Не удалось подключиться к Java Backend.") from error

        if response.is_redirect:
            raise BackendError(502, "BACKEND_REDIRECT_REJECTED", "Java Backend вернул перенаправление; запрос остановлен.")
        if response.status_code == 401:
            raise BackendError(401, "BACKEND_UNAUTHORIZED", "Java Backend отклонил JWT пользователя.")
        if response.status_code == 403:
            raise BackendError(403, "BACKEND_FORBIDDEN", "У пользователя нет доступа к этим поездкам.")
        if response.status_code == 404:
            raise BackendError(404, "BACKEND_TRIP_NOT_FOUND", "Поездка не найдена в Java Backend.")
        if response.status_code == 429 or response.status_code >= 500:
            raise BackendError(503, "BACKEND_UNAVAILABLE", "Java Backend временно недоступен.")
        if response.status_code >= 400:
            raise BackendError(502, "BACKEND_REQUEST_FAILED", "Java Backend отклонил запрос.")
        try:
            payload = response.json()
            if response_type == list[BackendTrip]:
                if not isinstance(payload, list):
                    raise ValueError("Expected a JSON array")
                return [BackendTrip.model_validate(item) for item in payload]
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            return BackendTrip.model_validate(payload)
        except (ValueError, ValidationError) as error:
            raise BackendError(502, "BACKEND_INVALID_RESPONSE", "Java Backend вернул ответ неожиданного формата.") from error
