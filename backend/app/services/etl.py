"""ETL-пайплайн слоя данных (Спринт 3).

Извлечение (Jotform / Excel / CSV) → нормализация и сопоставление полей →
расчёт (индекс КЭц, цифровая зрелость) → загрузка в БД (идемпотентно по
паре источник+внешний идентификатор). Функции принимают сессию SQLAlchemy,
что упрощает тестирование на SQLite.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    DigitalProjectItem,
    EfficiencyAssessment,
    MaturityAssessment,
    Organization,
    Project,
    RawSubmission,
)
from app.services.calculations import digital_maturity, digital_maturity_zone
from app.services.efficiency import EfficiencyIndexInputs, efficiency_index
from app.services.importers import (
    import_efficiency_sheet,
    import_maturity_sheet,
    to_efficiency_inputs,
)
from app.services.jotform_client import JotformClient
from app.services.jotform_mapping import (
    efficiency_inputs_from_answers,
    maturity_aggregates_from_answers,
    maturity_level_from_answers,
    maturity_scores_from_answers,
    organization_name_from_answers,
)


# ─────────────────────────── вспомогательные операции ───────────────────────────
def get_or_create_organization(db: Session, name: str) -> Organization:
    org = db.execute(select(Organization).where(Organization.name == name)).scalar_one_or_none()
    if org is None:
        org = Organization(name=name)
        db.add(org)
        db.flush()
    return org


def _already_processed(db: Session, source: str, external_id: str | None) -> bool:
    if external_id is None:
        return False
    row = db.execute(
        select(RawSubmission).where(
            RawSubmission.source == source, RawSubmission.external_id == external_id
        )
    ).scalar_one_or_none()
    return bool(row and row.processed)


def _record_raw(db: Session, source: str, external_id: str | None,
                payload: dict, form_id: str | None = None) -> RawSubmission:
    raw = None
    if external_id is not None:
        raw = db.execute(
            select(RawSubmission).where(
                RawSubmission.source == source, RawSubmission.external_id == external_id
            )
        ).scalar_one_or_none()
    if raw is None:
        raw = RawSubmission(source=source, external_id=external_id, form_id=form_id, payload=payload)
        db.add(raw)
        db.flush()
    return raw


# ─────────────────────────── загрузка результатов ───────────────────────────
def load_efficiency(db: Session, name: str, inputs: EfficiencyIndexInputs,
                    source: str, external_id: str | None) -> EfficiencyAssessment:
    """Рассчитать КЭц по индексной формуле и сохранить оценку (идемпотентно)."""
    payload = asdict(inputs)
    raw = _record_raw(db, source, external_id, payload, form_id=settings.jotform_form_efficiency)
    org = get_or_create_organization(db, name)
    result = efficiency_index(inputs)
    assessment = EfficiencyAssessment(
        organization_id=org.id,
        economic_index=result["economic_index"],
        ecological_index=result["ecological_index"],
        social_index=result["social_index"],
        coefficient=result["coefficient"],
        zone=result["zone"],
        inputs=payload,
        source=source,
        external_id=external_id,
    )
    db.add(assessment)
    raw.processed = True
    db.flush()
    return assessment


def load_maturity(db: Session, name: str, need_avg: float, capability_avg: float,
                  source: str, external_id: str | None,
                  maturity: float | None = None) -> MaturityAssessment:
    """Сохранить оценку цифровой зрелости.

    Если итоговый уровень `maturity` передан (вычислен формой) — используется он;
    иначе вычисляется как геометрическое среднее КЗ = sqrt(потребность · возможности).
    Зона — по порогам 0,134 / 0,366.
    """
    payload = {"need": need_avg, "capability": capability_avg, "maturity": maturity}
    raw = _record_raw(db, source, external_id, payload,
                      form_id=settings.jotform_form_maturity)
    org = get_or_create_organization(db, name)
    if maturity is None:
        maturity = float(digital_maturity([need_avg], [capability_avg])["maturity"])
    assessment = MaturityAssessment(
        organization_id=org.id,
        need_avg=need_avg, capability_avg=capability_avg,
        maturity=round(maturity, 4), zone=digital_maturity_zone(maturity),
        source=source, external_id=external_id,
    )
    db.add(assessment)
    raw.processed = True
    db.flush()
    return assessment


# ─────────────────────────── синхронизация с Jotform ───────────────────────────
def sync_efficiency_from_jotform(db: Session, client: JotformClient | None = None,
                                 form_id: str | None = None) -> dict:
    """Импортировать сабмишены формы эффективности и рассчитать КЭц."""
    form_id = form_id or settings.jotform_form_efficiency
    client = client or JotformClient()
    loaded, skipped, errors = 0, 0, []
    for sub in client.iter_submissions(form_id):
        sid = str(sub.get("id"))
        if _already_processed(db, "jotform", sid):
            skipped += 1
            continue
        answers = sub.get("answers", {})
        name = organization_name_from_answers(answers) or f"submission:{sid}"
        try:
            inputs = efficiency_inputs_from_answers(answers)
            load_efficiency(db, name, inputs, source="jotform", external_id=sid)
            loaded += 1
        except ValueError as exc:
            errors.append({"submission": sid, "error": str(exc)})
    db.commit()
    return {"loaded": loaded, "skipped": skipped, "errors": errors}


def sync_maturity_from_jotform(db: Session, client: JotformClient | None = None,
                               form_id: str | None = None,
                               need_qids: list[str] | None = None,
                               capability_qids: list[str] | None = None) -> dict:
    """Импортировать сабмишены формы зрелости и рассчитать цифровую зрелость.

    По умолчанию (без явных qid) используется режим АГРЕГАТОВ: из сабмишена
    читаются поля «Среднее значение показателей потребности/возможностей»
    (резолвинг по тексту), затем КЗ = Гурвиц(потребность, возможности, 0,5).
    Если переданы списки qid показателей — используется режим усреднения по ним.
    """
    form_id = form_id or settings.jotform_form_maturity or settings.jotform_form_transformation
    need_qids = need_qids if need_qids is not None else settings.jotform_maturity_need_qids
    capability_qids = (capability_qids if capability_qids is not None
                       else settings.jotform_maturity_capability_qids)
    aggregate_mode = not (need_qids and capability_qids)
    client = client or JotformClient()
    loaded, skipped, errors = 0, 0, []
    for sub in client.iter_submissions(form_id):
        sid = str(sub.get("id"))
        if _already_processed(db, "jotform", sid):
            skipped += 1
            continue
        answers = sub.get("answers", {})
        name = organization_name_from_answers(answers) or f"submission:{sid}"
        try:
            if aggregate_mode:
                need_avg, cap_avg = maturity_aggregates_from_answers(answers)
                level = maturity_level_from_answers(answers)
                load_maturity(db, name, need_avg, cap_avg, source="jotform",
                              external_id=sid, maturity=level)
            else:
                need, cap = maturity_scores_from_answers(answers, need_qids, capability_qids)
                load_maturity(db, name, sum(need) / len(need), sum(cap) / len(cap),
                              source="jotform", external_id=sid)
            loaded += 1
        except ValueError as exc:
            errors.append({"submission": sid, "error": str(exc)})
    db.commit()
    return {"loaded": loaded, "skipped": skipped, "errors": errors}


# ─────────────────────────── импорт из Excel ───────────────────────────
def import_maturity_from_excel(db: Session, path: str | Path) -> dict:
    loaded, errors = 0, []
    for rec in import_maturity_sheet(path):
        try:
            load_maturity(db, rec["name"], rec["need_avg"], rec["capability_avg"],
                          source="excel", external_id=f"maturity:{rec['name']}",
                          maturity=rec.get("reference_maturity"))
            loaded += 1
        except (ValueError, TypeError) as exc:
            errors.append({"name": rec.get("name"), "error": str(exc)})
    db.commit()
    return {"loaded": loaded, "errors": errors}


def import_efficiency_from_excel(db: Session, path: str | Path,
                                 yield_after: dict[str, float] | None = None) -> dict:
    loaded, skipped, errors = 0, 0, []
    for rec in import_efficiency_sheet(path):
        if yield_after and rec.get("name") in yield_after:
            rec["yield_after"] = yield_after[rec["name"]]
        try:
            inputs = to_efficiency_inputs(rec)
        except ValueError as exc:
            skipped += 1
            errors.append({"name": rec.get("name"), "error": str(exc)})
            continue
        load_efficiency(db, rec["name"], inputs, source="excel",
                        external_id=f"efficiency:{rec['name']}")
        loaded += 1
    db.commit()
    return {"loaded": loaded, "skipped": skipped, "errors": errors}


def import_efficiency_from_json(db: Session, path: str | Path) -> dict:
    """Импорт из JSON-фикстуры пилотных организаций (поля EfficiencyIndexInputs)."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    loaded = 0
    for rec in records:
        fields = {k: rec.get(k) for k in EfficiencyIndexInputs.__dataclass_fields__}
        inputs = EfficiencyIndexInputs(**fields)
        load_efficiency(db, rec["name"], inputs, source="json",
                        external_id=f"json:{rec['name']}")
        loaded += 1
    db.commit()
    return {"loaded": loaded}


def load_project_finance(db: Session, org_name: str, path: str | Path, *,
                         dscr_norm: float | None = None, var_type: str = "continuous") -> dict:
    """Разобрать Excel-модель долгового риска и сохранить проект организации.

    CAPEX → Project.capex (стоимость), NPV → DigitalProjectItem.npv (эффект),
    предел кредитоспособности → Project.credit_limit. После загрузки данные доступны
    модулю оптимизации через candidate_projects_from_db.
    """
    from app.services.debt_risk_model import (
        DSCR_NORM_DEFAULT,
        credit_limit_from_finance,
        parse_debt_risk_model,
    )

    pf = parse_debt_risk_model(path)
    norm = DSCR_NORM_DEFAULT if dscr_norm is None else dscr_norm
    credit_limit = credit_limit_from_finance(pf, norm)
    org = get_or_create_organization(db, org_name)

    proj = db.execute(
        select(Project).where(Project.organization_id == org.id)
    ).scalars().first()
    if proj is None:
        proj = Project(organization_id=org.id)
        db.add(proj)
    proj.capex = pf.capex_total
    proj.credit_limit = credit_limit
    proj.horizon_years = max(len(pf.capex_by_year) - 1, 1)
    db.flush()

    item = db.execute(
        select(DigitalProjectItem).where(DigitalProjectItem.project_id == proj.id)
    ).scalars().first()
    if item is None:
        item = DigitalProjectItem(project_id=proj.id,
                                  title="Инвестиционный проект цифровизации", pclass="infra")
        db.add(item)
    item.npv = pf.npv
    item.rov = 0.0
    item.var_type = var_type
    db.commit()
    return {
        "organization": org.name, "project_id": proj.id,
        "cost": proj.capex, "effect": pf.npv, "credit_limit": credit_limit,
        "finance": pf.to_dict(),
    }
