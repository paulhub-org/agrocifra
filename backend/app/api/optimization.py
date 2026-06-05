"""Эндпоинты финансово-математического модуля оптимального уровня затрат на цифровизацию.

Комбинированный подход (PuLP/CBC): максимизация суммарного эффекта при бюджетном
ограничении и границах кредитоспособности; учёт охвата организаций выше порога.
Запуск доступен офису цифровизации и государственному органу.
"""
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import OptimizationRun, Role
from app.schemas.optimization import OptimizationRequest
from app.services import etl
from app.services import optimization as opt

router = APIRouter(prefix="/optimization", tags=["Оптимизация затрат"])


@router.post("/projects/import-model", status_code=201,
             summary="Импорт Excel-модели долгового риска (CAPEX→стоимость, NPV→эффект)")
async def import_debt_risk_model(
    file: UploadFile = File(...),
    organization_name: str = Form(...),
    dscr_norm: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.digitalization_office, Role.state_authority)),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="Ожидается файл .xlsx модели долгового риска")
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        result = etl.load_project_finance(db, organization_name, tmp_path, dscr_norm=dscr_norm)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return result


@router.post("/run", status_code=201,
             summary="Оптимальное распределение бюджета цифровизации (комбинированный подход)")
def run_optimization(
    payload: OptimizationRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.digitalization_office, Role.state_authority)),
):
    if payload.projects:
        projects = [
            opt.OptProject(
                key=p.key or str(i + 1), name=p.name, cost=p.cost, effect=p.effect,
                var_type=p.var_type, score=p.score, min_share=p.min_share,
                credit_limit=p.credit_limit,
            )
            for i, p in enumerate(payload.projects)
        ]
    else:
        projects = opt.candidate_projects_from_db(db, score_metric=payload.score_metric)

    if not projects:
        raise HTTPException(
            status_code=422,
            detail="Нет проектов-кандидатов: передайте projects или заполните "
                   "данные проектов (capex и ЧДД) в базе.",
        )

    try:
        result = opt.optimize_allocation(
            projects, payload.budget,
            coverage_weight=payload.coverage_weight, threshold=payload.threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    run = OptimizationRun(
        project_id=None,
        params={"budget": payload.budget, "coverage_weight": payload.coverage_weight,
                "threshold": payload.threshold, "score_metric": payload.score_metric},
        status=result.status,
        result=result.to_dict(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, **result.to_dict()}


@router.get("/runs", summary="Список запусков оптимизации")
def list_runs(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rows = db.execute(
        select(OptimizationRun).order_by(OptimizationRun.id.desc())
    ).scalars().all()
    return [
        {"id": r.id, "status": r.status, "params": r.params,
         "total_effect": (r.result or {}).get("total_effect"),
         "total_spend": (r.result or {}).get("total_spend"),
         "selected_count": (r.result or {}).get("selected_count")}
        for r in rows
    ]


@router.get("/runs/{run_id}", summary="Результат запуска оптимизации")
def get_run(run_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    r = db.get(OptimizationRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Запуск не найден")
    return {"id": r.id, "status": r.status, "params": r.params, **(r.result or {})}
