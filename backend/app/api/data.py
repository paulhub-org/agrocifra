"""Эндпоинты слоя данных: синхронизация с Jotform, импорт Excel, выборка оценок."""
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import EfficiencyAssessment, MaturityAssessment, Organization
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


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(db: Session = Depends(get_db),
                       _user=Depends(get_current_user)):
    return db.execute(select(Organization)).scalars().all()


@router.get("/assessments/efficiency", response_model=list[EfficiencyAssessmentOut])
def list_efficiency(db: Session = Depends(get_db),
                    _user=Depends(get_current_user)):
    return db.execute(select(EfficiencyAssessment)).scalars().all()


@router.get("/assessments/maturity", response_model=list[MaturityAssessmentOut])
def list_maturity(db: Session = Depends(get_db),
                  _user=Depends(get_current_user)):
    return db.execute(select(MaturityAssessment)).scalars().all()


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
    db.commit()
    return assessment


@router.post("/assessments/maturity", response_model=MaturityAssessmentOut,
             status_code=201, summary="Ручной ввод цифровой зрелости (метод Гурвица)")
def create_maturity(payload: MaturityInputIn, db: Session = Depends(get_db),
                    _user=Depends(get_current_user)):
    assessment = etl.load_maturity(db, payload.organization_name,
                                   payload.need_avg, payload.capability_avg,
                                   source="manual", external_id=None)
    db.commit()
    return assessment
