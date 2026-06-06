"""Агрегация результатов для дашбордов и отчётов (Спринт 5).

Сводка в целом, по регионам и по организациям; сравнительные ряды «до/после»
для эффективности (строятся из сохранённых нормализованных входных полей).
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    EfficiencyAssessment,
    MaturityAssessment,
    Organization,
    Region,
)


def _safe_mean(xs: list[float]) -> float | None:
    return round(mean(xs), 4) if xs else None


def _zone_distribution(zones: list[str]) -> dict[str, int]:
    dist: dict[str, int] = defaultdict(int)
    for z in zones:
        dist[z] += 1
    return dict(dist)


def org_region_map(db: Session) -> dict[int, dict[str, str]]:
    """{organization_id: {name, region}} с подстановкой «Не указан» при отсутствии региона."""
    rows = db.execute(
        select(Organization.id, Organization.name, Region.name)
        .join(Region, Organization.region_id == Region.id, isouter=True)
    ).all()
    return {oid: {"name": oname, "region": rname or "Не указан"} for oid, oname, rname in rows}


def efficiency_rows(db: Session) -> list[EfficiencyAssessment]:
    return list(db.execute(select(EfficiencyAssessment)).scalars().all())


def maturity_rows(db: Session) -> list[MaturityAssessment]:
    return list(db.execute(select(MaturityAssessment)).scalars().all())


def _allowed_org_ids(db: Session, org_id: int | None, region_id: int | None,
                     district: str | None = None) -> set[int] | None:
    """Множество допустимых организаций для ролевого ограничения; None — без ограничения.

    org_id — одна организация; (region_id, district) — организации района;
    region_id — организации области; всё None — без ограничения.
    """
    if org_id is not None:
        return {org_id}
    if region_id is not None and district:
        return set(db.execute(
            select(Organization.id).where(
                Organization.region_id == region_id, Organization.district == district
            )
        ).scalars().all())
    if region_id is not None:
        return set(db.execute(
            select(Organization.id).where(Organization.region_id == region_id)
        ).scalars().all())
    return None


def summary(db: Session, *, org_id: int | None = None, region_id: int | None = None,
            district: str | None = None) -> dict:
    """Сводка: общие показатели, разрез по регионам, эффективность по организациям.

    Ограничение по роли: org_id — одна организация; (region_id, district) — организации
    района; region_id — организации области; всё None — все данные (офис, госорган).
    """
    omap = org_region_map(db)
    allowed = _allowed_org_ids(db, org_id, region_id, district)
    eff = [a for a in efficiency_rows(db) if allowed is None or a.organization_id in allowed]
    mat = [a for a in maturity_rows(db) if allowed is None or a.organization_id in allowed]

    overall = {
        "organizations": (len(allowed) if allowed is not None
                          else db.execute(select(func.count()).select_from(Organization)).scalar_one()),
        "efficiency_count": len(eff),
        "maturity_count": len(mat),
        "mean_ke": _safe_mean([a.coefficient for a in eff]),
        "mean_maturity": _safe_mean([a.maturity for a in mat]),
        "efficiency_effective": sum(1 for a in eff if a.coefficient > 1.0),
        "efficiency_zones": _zone_distribution([a.zone for a in eff]),
        "maturity_zones": _zone_distribution([a.zone for a in mat]),
    }

    buckets: dict[str, dict[str, list]] = defaultdict(lambda: {"ke": [], "maturity": []})
    for a in eff:
        buckets[omap.get(a.organization_id, {}).get("region", "Не указан")]["ke"].append(a.coefficient)
    for a in mat:
        buckets[omap.get(a.organization_id, {}).get("region", "Не указан")]["maturity"].append(a.maturity)
    by_region = [
        {
            "region": region,
            "mean_ke": _safe_mean(v["ke"]),
            "efficiency_count": len(v["ke"]),
            "mean_maturity": _safe_mean(v["maturity"]),
            "maturity_count": len(v["maturity"]),
        }
        for region, v in sorted(buckets.items())
    ]

    efficiency_by_org = [
        {
            "organization_id": a.organization_id,
            "name": omap.get(a.organization_id, {}).get("name", f"#{a.organization_id}"),
            "region": omap.get(a.organization_id, {}).get("region", "Не указан"),
            "economic_index": a.economic_index,
            "ecological_index": a.ecological_index,
            "social_index": a.social_index,
            "coefficient": a.coefficient,
            "zone": a.zone,
        }
        for a in eff
    ]
    maturity_by_org = [
        {
            "organization_id": a.organization_id,
            "name": omap.get(a.organization_id, {}).get("name", f"#{a.organization_id}"),
            "region": omap.get(a.organization_id, {}).get("region", "Не указан"),
            "need_avg": a.need_avg,
            "capability_avg": a.capability_avg,
            "maturity": a.maturity,
            "zone": a.zone,
        }
        for a in mat
    ]
    recent = sorted(mat, key=lambda a: a.id, reverse=True)[:5]
    recent_maturity = [
        {
            "organization_id": a.organization_id,
            "name": omap.get(a.organization_id, {}).get("name", f"#{a.organization_id}"),
            "region": omap.get(a.organization_id, {}).get("region", "Не указан"),
            "maturity": a.maturity,
            "zone": a.zone,
            "date": a.created_at.isoformat() if a.created_at else None,
        }
        for a in recent
    ]
    return {
        "overall": overall,
        "by_region": by_region,
        "efficiency_by_org": efficiency_by_org,
        "maturity_by_org": maturity_by_org,
        "recent_maturity": recent_maturity,
    }


_BEFORE_AFTER_FIELDS = [
    ("Урожайность", "yield_before", "yield_after", "т/га"),
    ("Производительность труда", "productivity_before", "productivity_after", "руб./чел."),
    ("Налоги", "taxes_before", "taxes_after", "руб."),
    ("Бензин", "petrol_before_t", "petrol_after_t", "т"),
    ("Дизельное топливо", "diesel_before_t", "diesel_after_t", "т"),
]


def organization_report(db: Session, org_id: int) -> dict:
    """Карточка организации: оценки + сравнительные ряды «до/после» (последняя оценка)."""
    omap = org_region_map(db)
    info = omap.get(org_id, {"name": f"#{org_id}", "region": "Не указан"})
    eff = list(db.execute(
        select(EfficiencyAssessment).where(EfficiencyAssessment.organization_id == org_id)
    ).scalars().all())
    mat = list(db.execute(
        select(MaturityAssessment).where(MaturityAssessment.organization_id == org_id)
    ).scalars().all())

    before_after: list[dict] = []
    latest = eff[-1] if eff else None
    if latest and latest.inputs:
        i = latest.inputs
        for label, kb, ka, unit in _BEFORE_AFTER_FIELDS:
            b, a = i.get(kb), i.get(ka)
            if b is not None and a is not None:
                change = round((a - b) / b * 100, 1) if b else None
                before_after.append({"indicator": label, "before": b, "after": a,
                                     "unit": unit, "change_pct": change})
        cb, area, ca = i.get("cost_total_before"), i.get("area_before_ha"), i.get("cost_per_ha_after")
        if cb and area and ca:
            before = round(cb / area, 2)
            before_after.append({"indicator": "Затраты на 1 га", "before": before, "after": ca,
                                 "unit": "руб./га",
                                 "change_pct": round((ca - before) / before * 100, 1) if before else None})

    return {
        "organization_id": org_id,
        "name": info["name"],
        "region": info["region"],
        "efficiency": [
            {"economic_index": a.economic_index, "ecological_index": a.ecological_index,
             "social_index": a.social_index, "coefficient": a.coefficient, "zone": a.zone,
             "source": a.source} for a in eff
        ],
        "maturity": [
            {"need_avg": a.need_avg, "capability_avg": a.capability_avg,
             "maturity": a.maturity, "zone": a.zone, "source": a.source} for a in mat
        ],
        "before_after": before_after,
    }
