"""Схемы запросов/ответов слоя данных (Спринт 3)."""
from pydantic import BaseModel, ConfigDict, Field


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class EfficiencyAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int | None
    economic_index: float | None
    ecological_index: float | None
    social_index: float | None
    coefficient: float
    zone: str
    source: str
    external_id: str | None


class MaturityAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int | None
    need_avg: float
    capability_avg: float
    maturity: float
    zone: str
    source: str
    external_id: str | None


class SyncResult(BaseModel):
    loaded: int
    skipped: int = 0
    errors: list = []


class ImportResult(BaseModel):
    loaded: int
    skipped: int = 0
    errors: list = []


class EfficiencyInputIn(BaseModel):
    organization_name: str
    cost_total_before: float
    area_before_ha: float
    cost_per_ha_after: float
    yield_before: float
    yield_after: float
    profit_after: float | None = None
    total_costs: float | None = None
    profit_before: float | None = None
    total_costs_before: float | None = None
    petrol_before_t: float
    petrol_after_t: float
    diesel_before_t: float
    diesel_after_t: float
    productivity_after: float
    productivity_before: float
    taxes_after: float
    taxes_before: float


class MaturityInputIn(BaseModel):
    organization_name: str
    need_avg: float = Field(ge=0)
    capability_avg: float = Field(ge=0)
