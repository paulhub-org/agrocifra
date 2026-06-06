"""Финансово-математический модуль оптимального уровня затрат на цифровизацию.

Распределяет ограниченный бюджет цифровизации между организациями (проектами),
максимизируя суммарный экономический (интегральный) эффект. Постановка —
смешанно-целочисленное линейное программирование (MILP) на решателе CBC (PuLP),
комбинированный подход к финансированию: для каждого проекта одновременно
определяются бинарный выбор (финансировать ли) и непрерывный объём средств.

Целевая функция:
    max  Σ (эффект_i / стоимость_i) · f_i  +  w · Σ_{оценка_i ≥ порога} x_i
где x_i ∈ {0,1} — отбор проекта, f_i ∈ [0, cap_i] — объём финансирования,
эффект_i — ожидаемый эффект при полном финансировании, w — вес охвата
(число организаций с оценкой зрелости/эффективности не ниже порога).

Ограничения:
    f_i ≤ cap_i · x_i            cap_i = min(стоимость_i, кредитный лимит_i)
                                 (граница кредитоспособности / долгового риска);
    бинарный проект:    f_i ≥ стоимость_i · x_i           (всё-или-ничего);
    непрерывный проект: f_i ≥ min_share_i · стоимость_i · x_i (мин. жизнеспособная доля);
    Σ f_i ≤ бюджет.

Эффект масштабируется долей финансирования (для бинарных проектов доля = 1),
поэтому вклад в цель линеен: (эффект_i / стоимость_i) · f_i.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pulp


@dataclass
class OptProject:
    """Проект-кандидат на финансирование цифровизации."""
    key: str
    cost: float                       # требуемые инвестиции (capex), руб.
    effect: float                     # ожидаемый эффект при полном финансировании, руб.
    var_type: str = "continuous"      # "binary" (всё-или-ничего) | "continuous" (масштабируемый)
    score: float = 0.0                # КЭц или уровень зрелости (для порогового охвата)
    maturity: float = 0.0             # уровень цифровой зрелости (для отображения в таблице)
    min_share: float = 0.5            # мин. доля стоимости при отборе (для continuous)
    credit_limit: float | None = None  # предел финансирования по кредитоспособности, руб.
    name: str | None = None           # человекочитаемое наименование

    def cap(self) -> float:
        return self.cost if self.credit_limit is None else min(self.cost, self.credit_limit)


@dataclass
class Allocation:
    key: str
    name: str
    selected: bool
    funding: float
    funded_share: float
    effect: float
    score: float
    maturity: float
    above_threshold: bool


@dataclass
class AllocationResult:
    status: str
    budget: float
    total_effect: float
    total_spend: float
    utilization: float
    selected_count: int
    above_threshold_count: int
    allocations: list[Allocation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "budget": round(self.budget, 2),
            "total_effect": round(self.total_effect, 2),
            "total_spend": round(self.total_spend, 2),
            "utilization": round(self.utilization, 4),
            "selected_count": self.selected_count,
            "above_threshold_count": self.above_threshold_count,
            "allocations": [
                {
                    "key": a.key, "name": a.name, "selected": a.selected,
                    "funding": round(a.funding, 2), "funded_share": round(a.funded_share, 4),
                    "effect": round(a.effect, 2), "score": round(a.score, 4),
                    "maturity": round(a.maturity, 4),
                    "above_threshold": a.above_threshold,
                }
                for a in self.allocations
            ],
        }


def _validate(projects: list[OptProject], budget: float) -> None:
    if budget < 0:
        raise ValueError("Бюджет не может быть отрицательным")
    for p in projects:
        if p.cost <= 0:
            raise ValueError(f"{p.key}: стоимость проекта должна быть положительной")
        if p.effect < 0:
            raise ValueError(f"{p.key}: эффект не может быть отрицательным")
        if not 0.0 <= p.min_share <= 1.0:
            raise ValueError(f"{p.key}: min_share должна быть в диапазоне [0; 1]")
        if p.var_type not in ("binary", "continuous"):
            raise ValueError(f"{p.key}: var_type должен быть 'binary' или 'continuous'")


def optimize_allocation(
    projects: list[OptProject],
    budget: float,
    *,
    coverage_weight: float = 0.0,
    threshold: float = 1.0,
    msg: bool = False,
) -> AllocationResult:
    """Решить задачу распределения бюджета цифровизации (MILP, CBC).

    coverage_weight — вес вторичной цели (число отобранных организаций с оценкой
    не ниже `threshold`); при 0 учитывается только суммарный эффект.
    """
    _validate(projects, budget)
    if not projects:
        return AllocationResult("Optimal", budget, 0.0, 0.0, 0.0, 0, 0, [])

    prob = pulp.LpProblem("digitalization_budget_allocation", pulp.LpMaximize)
    x = {p.key: pulp.LpVariable(f"x_{i}", cat="Binary") for i, p in enumerate(projects)}
    f = {p.key: pulp.LpVariable(f"f_{i}", lowBound=0) for i, p in enumerate(projects)}

    for p in projects:
        cap = p.cap()
        prob += f[p.key] <= cap * x[p.key], f"cap_{p.key}"
        if p.var_type == "binary":
            prob += f[p.key] >= p.cost * x[p.key], f"full_{p.key}"        # всё-или-ничего
        else:
            prob += f[p.key] >= p.min_share * p.cost * x[p.key], f"min_{p.key}"

    prob += pulp.lpSum(f.values()) <= budget, "budget"

    effect_term = pulp.lpSum((p.effect / p.cost) * f[p.key] for p in projects)
    coverage_term = pulp.lpSum(x[p.key] for p in projects if p.score >= threshold)
    prob += effect_term + coverage_weight * coverage_term

    prob.solve(pulp.PULP_CBC_CMD(msg=msg))
    status = pulp.LpStatus[prob.status]

    allocations: list[Allocation] = []
    total_effect = total_spend = 0.0
    selected_count = above_count = 0
    for p in projects:
        fv = float(f[p.key].value() or 0.0)
        sel = bool((x[p.key].value() or 0) > 0.5) and fv > 1e-6
        share = fv / p.cost if p.cost else 0.0
        eff = p.effect * share
        above = sel and p.score >= threshold
        if sel:
            selected_count += 1
            total_spend += fv
            total_effect += eff
            above_count += int(above)
        allocations.append(Allocation(
            key=p.key, name=p.name or p.key, selected=sel,
            funding=fv, funded_share=share, effect=eff, score=p.score,
            maturity=p.maturity, above_threshold=above,
        ))

    util = total_spend / budget if budget > 0 else 0.0
    return AllocationResult(status, budget, total_effect, total_spend, util,
                            selected_count, above_count, allocations)


def candidate_projects_from_db(db, *, score_metric: str = "efficiency") -> list[OptProject]:
    """Построить проекты-кандидаты из БД (Project + DigitalProjectItem).

    Стоимость = Project.capex; эффект = Σ(npv + rov) элементов портфеля; тип переменной —
    «continuous», если хотя бы один элемент непрерывный, иначе «binary»; оценка —
    последняя КЭц (или зрелость) организации.
    """
    from sqlalchemy import select

    from app.models.models import (
        DigitalProjectItem,
        EfficiencyAssessment,
        MaturityAssessment,
        Organization,
        Project,
    )

    projects: list[OptProject] = []
    for proj in db.execute(select(Project)).scalars().all():
        if not proj.capex:
            continue
        items = db.execute(
            select(DigitalProjectItem).where(DigitalProjectItem.project_id == proj.id)
        ).scalars().all()
        effect = sum((it.npv or 0.0) + (it.rov or 0.0) for it in items)
        var_type = "continuous" if any(it.var_type == "continuous" for it in items) else "binary"
        org = db.get(Organization, proj.organization_id)
        mrow = db.execute(
            select(MaturityAssessment).where(
                MaturityAssessment.organization_id == proj.organization_id
            ).order_by(MaturityAssessment.id.desc())
        ).scalars().first()
        maturity = float(mrow.maturity) if mrow else 0.0
        if score_metric == "maturity":
            row = db.execute(
                select(MaturityAssessment).where(
                    MaturityAssessment.organization_id == proj.organization_id
                ).order_by(MaturityAssessment.id.desc())
            ).scalars().first()
            score = row.maturity if row else 0.0
        else:
            row = db.execute(
                select(EfficiencyAssessment).where(
                    EfficiencyAssessment.organization_id == proj.organization_id
                ).order_by(EfficiencyAssessment.id.desc())
            ).scalars().first()
            score = row.coefficient if row else 0.0
        projects.append(OptProject(
            key=str(proj.id), cost=float(proj.capex), effect=float(effect),
            var_type=var_type, score=float(score), maturity=maturity,
            credit_limit=float(proj.credit_limit) if proj.credit_limit is not None else None,
            name=org.name if org else f"project:{proj.id}",
        ))
    return projects
