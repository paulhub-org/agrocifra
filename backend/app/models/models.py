"""Модель данных АИС «АгроЦифра» (см. ТЗ, раздел 4.4.3, рисунок 2).

Базовый набор сущностей Спринта 1. Полный набор и миграции — Спринт 3.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Role(str, enum.Enum):
    organization = "organization"                    # сельскохозяйственная организация
    regional_operator = "regional_operator"          # региональный оператор
    digitalization_office = "digitalization_office"  # офис цифровизации
    state_authority = "state_authority"              # государственный орган


class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)


class Organization(Base):
    __tablename__ = "organization"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    oked: Mapped[str] = mapped_column(String(8), default="011")   # ОКЭД 011–017
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region.id"))
    address: Mapped[str | None] = mapped_column(String(512))
    periods: Mapped[list["ReportingPeriod"]] = relationship(back_populates="organization")


class UserAccount(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(128), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(256))
    email: Mapped[str | None] = mapped_column(String(256))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default=Role.organization.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region.id"))


class ReportingPeriod(Base):
    __tablename__ = "reporting_period"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))
    year: Mapped[int] = mapped_column(Integer)
    organization: Mapped["Organization"] = relationship(back_populates="periods")


class EfficiencyIndicator(Base):
    """12 показателей эффективности: 4 экономических, 4 экологических, 4 социальных."""
    __tablename__ = "efficiency_indicator"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("reporting_period.id"))
    component: Mapped[str] = mapped_column(String(16))   # economic | ecological | social
    code: Mapped[str] = mapped_column(String(32))
    value_before: Mapped[float | None] = mapped_column(Float)
    value_after: Mapped[float | None] = mapped_column(Float)


class Project(Base):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))
    horizon_years: Mapped[int] = mapped_column(Integer, default=3)
    capex: Mapped[float | None] = mapped_column(Float)
    credit_limit: Mapped[float | None] = mapped_column(Float)  # предел по кредитоспособности


class DigitalProjectItem(Base):
    __tablename__ = "digital_project_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    title: Mapped[str] = mapped_column(String(256))
    pclass: Mapped[str] = mapped_column(String(16))      # класс портфеля ИТ-инвестиций
    npv: Mapped[float | None] = mapped_column(Float)
    rov: Mapped[float | None] = mapped_column(Float, default=0.0)
    var_type: Mapped[str] = mapped_column(String(8), default="binary")  # binary | continuous


class IndustryNorm(Base):
    __tablename__ = "industry_norm"
    oked: Mapped[str] = mapped_column(String(8), primary_key=True)
    k1_min: Mapped[float] = mapped_column(Float, default=1.5)   # текущая ликвидность
    k2_min: Mapped[float] = mapped_column(Float, default=0.2)   # Косос
    k3_max: Mapped[float] = mapped_column(Float, default=0.85)  # Кооа
    roa_min: Mapped[float] = mapped_column(Float, default=0.03)
    autonomy: Mapped[float] = mapped_column(Float, default=0.5)
    leverage: Mapped[float] = mapped_column(Float, default=0.7)


class CalibrationParam(Base):
    __tablename__ = "calibration_param"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(256))


class OptimizationRun(Base):
    __tablename__ = "optimization_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id"))  # None — портфельный прогон
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="created")
    result: Mapped[dict | None] = mapped_column(JSON)


# ─────────────────────────── СЛОЙ ДАННЫХ (Спринт 3) ───────────────────────────
class RawSubmission(Base):
    """Сырой ответ (Jotform / Excel / CSV) — для трассируемости и идемпотентного ETL."""
    __tablename__ = "raw_submission"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(16))              # jotform | excel | csv
    form_id: Mapped[str | None] = mapped_column(String(32))
    external_id: Mapped[str | None] = mapped_column(String(64))  # submission id / ключ строки
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_raw_source_external"),
    )


class MaturityAssessment(Base):
    """Результат оценки цифровой зрелости (метод Гурвица, пороги 0,134 / 0,366)."""
    __tablename__ = "maturity_assessment"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    period_id: Mapped[int | None] = mapped_column(ForeignKey("reporting_period.id"))
    need_avg: Mapped[float] = mapped_column(Float)
    capability_avg: Mapped[float] = mapped_column(Float)
    maturity: Mapped[float] = mapped_column(Float)
    zone: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16), default="jotform")
    external_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EfficiencyAssessment(Base):
    """Результат оценки эффективности цифровизации (индексная формула КЭц)."""
    __tablename__ = "efficiency_assessment"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    period_id: Mapped[int | None] = mapped_column(ForeignKey("reporting_period.id"))
    economic_index: Mapped[float | None] = mapped_column(Float)
    ecological_index: Mapped[float | None] = mapped_column(Float)
    social_index: Mapped[float | None] = mapped_column(Float)
    coefficient: Mapped[float] = mapped_column(Float)
    zone: Mapped[str] = mapped_column(String(16))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)     # нормализованные входные поля
    source: Mapped[str] = mapped_column(String(16), default="jotform")
    external_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
