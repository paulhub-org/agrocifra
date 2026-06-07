"""Эндпоинты слоя данных: синхронизация с Jotform, импорт Excel, выборка оценок."""
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles, scope_filters
from app.db.session import get_db
from app.models.models import EfficiencyAssessment, MaturityAssessment, Organization, Region
from app.schemas.data import (
    EfficiencyAssessmentOut,
    EfficiencyInputIn,
    ImportResult,
    MaturityAssessmentOut,
    MaturityInputIn,
    OrganizationOut,
    SyncResult,
)
from app.models.models import Role
from app.services import etl
from app.services.efficiency import EfficiencyIndexInputs

router = APIRouter(prefix="/data", tags=["Слой данных"])


def _scoped_org_ids(db: Session, user) -> list[int] | None:
    """Список допустимых организаций по роли (None — без ограничения)."""
    org_id, region_id, district = scope_filters(user)
    if org_id is not None:
        return [org_id]
    if region_id is not None and district:
        return list(db.execute(
            select(Organization.id).where(
                Organization.region_id == region_id, Organization.district == district
            )
        ).scalars().all())
    if region_id is not None:
        return list(db.execute(
            select(Organization.id).where(Organization.region_id == region_id)
        ).scalars().all())
    return None


def _apply_location(db: Session, org_name: str, region: str | None, district: str | None) -> None:
    """Проставить организации область и район (для отчёта «Среднее КЭц по регионам»)."""
    if not region and not district:
        return
    org = db.execute(select(Organization).where(Organization.name == org_name)).scalar_one_or_none()
    if not org:
        return
    if region:
        reg = db.execute(select(Region).where(Region.name == region)).scalar_one_or_none()
        if not reg:
            reg = Region(name=region)
            db.add(reg)
            db.flush()
        org.region_id = reg.id
    if district:
        org.district = district
    db.flush()


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(db: Session = Depends(get_db),
                       user=Depends(get_current_user)):
    org_id, region_id, district = scope_filters(user)
    q = select(Organization)
    if org_id is not None:
        q = q.where(Organization.id == org_id)
    elif region_id is not None and district:
        q = q.where(Organization.region_id == region_id, Organization.district == district)
    elif region_id is not None:
        q = q.where(Organization.region_id == region_id)
    return db.execute(q).scalars().all()


@router.get("/assessments/efficiency", response_model=list[EfficiencyAssessmentOut])
def list_efficiency(db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    ids = _scoped_org_ids(db, user)
    q = select(EfficiencyAssessment)
    if ids is not None:
        q = q.where(EfficiencyAssessment.organization_id.in_(ids))
    return db.execute(q).scalars().all()


@router.get("/assessments/maturity", response_model=list[MaturityAssessmentOut])
def list_maturity(db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    ids = _scoped_org_ids(db, user)
    q = select(MaturityAssessment)
    if ids is not None:
        q = q.where(MaturityAssessment.organization_id.in_(ids))
    return db.execute(q).scalars().all()


@router.post("/etl/jotform/efficiency/sync", response_model=SyncResult)
def sync_efficiency(db: Session = Depends(get_db),
                    _user=Depends(require_roles(Role.digitalization_office, Role.state_authority))):
    try:
        return etl.sync_efficiency_from_jotform(db)
    except Exception as exc:  # noqa: BLE001 — внешняя интеграция
        raise HTTPException(status_code=502, detail=f"Jotform sync failed: {exc}") from exc


@router.post("/etl/jotform/maturity/sync", response_model=SyncResult)
def sync_maturity(db: Session = Depends(get_db),
                  _user=Depends(require_roles(Role.digitalization_office, Role.state_authority))):
    try:
        return etl.sync_maturity_from_jotform(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Jotform sync failed: {exc}") from exc


@router.get("/jotform/prefill/{kind}",
            summary="Автозагрузка данных организации из её последней заявки Jotform (задачи 16/17/18)")
def jotform_prefill(kind: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Подставить данные текущей организации из её заявки Jotform.

    Доступно роли «Организация» (организация определяется по учётной записи). Для
    учётных записей без привязки к организации возвращается available=false.
    """
    if kind not in ("maturity", "efficiency"):
        raise HTTPException(status_code=404, detail="Неизвестный тип формы")
    if not user.organization_id:
        return {"available": False, "reason": "no_org"}
    org = db.get(Organization, user.organization_id)
    if org is None:
        return {"available": False, "reason": "no_org"}
    try:
        return etl.jotform_org_prefill(org.name, kind)
    except Exception as exc:  # noqa: BLE001 — сетевые/HTTP ошибки внешней интеграции
        raise HTTPException(status_code=502, detail=f"Jotform: {exc}") from exc


@router.post("/jotform/sync-mine/{kind}",
             summary="Загрузить последнюю заявку Jotform своей организации как оценку (задача 16)")
def jotform_sync_mine(kind: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Обновить оценку текущей организации из её последней заявки Jotform.

    Применяется автозагрузкой модуля оптимизации: после обновления КЭц организации
    расчёт оптимального уровня затрат опирается на актуальные данные Jotform.
    """
    if kind not in ("maturity", "efficiency"):
        raise HTTPException(status_code=404, detail="Неизвестный тип формы")
    if not user.organization_id:
        return {"available": False, "reason": "no_org"}
    org = db.get(Organization, user.organization_id)
    if org is None:
        return {"available": False, "reason": "no_org"}
    try:
        return etl.sync_org_latest(db, org.name, kind)
    except Exception as exc:  # noqa: BLE001 — сетевые/HTTP ошибки внешней интеграции
        raise HTTPException(status_code=502, detail=f"Jotform: {exc}") from exc


def _save_upload(file: UploadFile) -> Path:
    tmp = Path(tempfile.mkdtemp()) / (file.filename or "upload.xlsx")
    with tmp.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return tmp


@router.post("/etl/import/excel/maturity", response_model=ImportResult)
def import_excel_maturity(file: UploadFile = File(...), db: Session = Depends(get_db),
                          _user=Depends(require_roles(Role.digitalization_office))):
    return etl.import_maturity_from_excel(db, _save_upload(file))


@router.post("/etl/import/excel/efficiency", response_model=ImportResult)
def import_excel_efficiency(file: UploadFile = File(...), db: Session = Depends(get_db),
                            _user=Depends(require_roles(Role.digitalization_office))):
    return etl.import_efficiency_from_excel(db, _save_upload(file))


@router.post("/assessments/efficiency", response_model=EfficiencyAssessmentOut,
             status_code=201, summary="Ручной ввод данных эффективности и расчёт КЭц")
def create_efficiency(payload: EfficiencyInputIn, db: Session = Depends(get_db),
                      _user=Depends(get_current_user)):
    fields = {k: getattr(payload, k) for k in EfficiencyIndexInputs.__dataclass_fields__}
    inputs = EfficiencyIndexInputs(**fields)
    assessment = etl.load_efficiency(db, payload.organization_name, inputs,
                                     source="manual", external_id=None)
    _apply_location(db, payload.organization_name, payload.region, payload.district)
    db.commit()
    return assessment


@router.post("/assessments/maturity", response_model=MaturityAssessmentOut,
             status_code=201, summary="Ручной ввод цифровой зрелости (метод Гурвица)")
def create_maturity(payload: MaturityInputIn, db: Session = Depends(get_db),
                    _user=Depends(get_current_user)):
    assessment = etl.load_maturity(db, payload.organization_name,
                                   payload.need_avg, payload.capability_avg,
                                   source="manual", external_id=None)
    _apply_location(db, payload.organization_name, payload.region, payload.district)
    db.commit()
    return assessment
