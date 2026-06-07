"""Конструктор рекомендаций (V2.0, задача 3).

Формирует текстовые рекомендации по повышению показателей цифровизации —
потребность, возможности, цифровая зрелость, эффективность — на основе последней
оценки организации. Ограничение по роли реализуется через множество допустимых
организаций (allowed_ids); None означает «без ограничения» (офис, госорган).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import EfficiencyAssessment, MaturityAssessment
from app.services.reporting import org_region_map

INDICATORS = [
    ("need", "Потребность во внедрении цифровых технологий"),
    ("capability", "Возможности внедрения цифровых технологий"),
    ("maturity", "Цифровая зрелость"),
    ("efficiency", "Эффективность цифровизации"),
]
INDICATOR_LABELS = dict(INDICATORS)


def _fmt(v) -> str:
    return "—" if v is None else f"{v:.2f}".replace(".", ",")


def _tercile(v) -> str | None:
    if v is None:
        return None
    if v < 0.34:
        return "низкий"
    if v < 0.66:
        return "средний"
    return "высокий"


_NO_MATURITY = "Недостаточно данных: отсутствует оценка цифровой зрелости организации."
_NO_EFFICIENCY = "Недостаточно данных: отсутствует оценка эффективности цифровизации организации."


def _rec_need(v):
    lvl = _tercile(v)
    if lvl is None:
        return None, _NO_MATURITY
    if lvl == "низкий":
        return lvl, ("Рекомендуется провести инвентаризацию бизнес-процессов растениеводства и "
            "выявить операции с наибольшим потенциалом цифровизации (планирование севооборота, учёт "
            "полевых работ, мониторинг состояния посевов), что позволит обоснованно сформировать "
            "потребность и приоритизировать инвестиции.")
    if lvl == "средний":
        return lvl, ("Целесообразно сфокусировать цифровизацию на процессах с наибольшим экономическим "
            "эффектом — точное внесение средств защиты растений и удобрений, спутниковый мониторинг "
            "полей, телеметрия техники — и закрепить выявленную потребность в программе цифрового "
            "развития организации.")
    return lvl, ("Высокая потребность свидетельствует о значительном потенциале отдачи от "
        "цифровизации; рекомендуется перейти к реализации приоритетных цифровых проектов и обеспечить "
        "их ресурсную поддержку, не допуская разрыва между потребностью и фактическим уровнем внедрения.")


def _rec_capability(v):
    lvl = _tercile(v)
    if lvl is None:
        return None, _NO_MATURITY
    if lvl == "низкий":
        return lvl, ("Первоочередные меры — развитие ИТ-инфраструктуры (широкополосный доступ, "
            "серверное и полевое оборудование), повышение цифровых компетенций персонала и "
            "формирование бюджета цифровизации; на начальном этапе целесообразно применять облачные "
            "сервисы и типовые отраслевые решения, снижающие капитальные затраты.")
    if lvl == "средний":
        return lvl, ("Рекомендуется устранить «узкие места» готовности: обеспечить интеграцию "
            "имеющихся информационных систем, организовать регулярное обучение специалистов и "
            "закрепить ответственных за управление данными, что повысит отдачу от последующих вложений.")
    return lvl, ("Сформированный кадровый и инфраструктурный потенциал позволяет реализовывать "
        "комплексные цифровые проекты (системы поддержки принятия решений, цифровые двойники полей, "
        "сквозную аналитику) и масштабировать успешные практики.")


def _rec_maturity(v, zone):
    if v is None:
        return None, _NO_MATURITY
    z = zone or ("низкая" if v < 0.134 else "средняя" if v < 0.366 else "высокая")
    if z == "низкая":
        return z, ("Показатель рассчитывается как среднее геометрическое потребности и возможностей, "
            "поэтому необходимо сбалансированное развитие обоих компонентов: разработка программы "
            "цифровой трансформации, реализация пилотных проектов в наиболее значимых процессах "
            "растениеводства, поэтапное наращивание инфраструктуры и компетенций.")
    if z == "средняя":
        return z, ("Рекомендуется перейти от точечной автоматизации к системной цифровизации: "
            "интеграция данных агроопераций, внедрение систем поддержки принятия решений, мониторинг "
            "ключевых показателей эффективности цифровых проектов.")
    return z, ("Рекомендуется закрепить достигнутый уровень, тиражировать результативные цифровые "
        "решения и развивать продвинутую аналитику (предиктивные модели урожайности, оптимизация "
        "ресурсов), выступая центром компетенций для организаций района и области.")


def _rec_efficiency(coef, eco, env, soc):
    if coef is None:
        return None, _NO_EFFICIENCY
    parts = {"экономической": eco, "экологической": env, "социальной": soc}
    present = {k: v for k, v in parts.items() if v is not None}
    weakest = min(present, key=present.get) if present else None
    if coef >= 1.0:
        return "эффективна", ("Значение превышает пороговое (КЭц ≥ 1,0): цифровизация результативна. "
            "Рекомендуется масштабировать применяемые цифровые решения, распространять лучшие практики "
            "и поддерживать достигнутую эффективность за счёт постоянного мониторинга экономической, "
            "экологической и социальной составляющих.")
    txt = ("Значение ниже порогового (КЭц < 1,0): отдача вложений недостаточна. Рекомендуется "
        "сосредоточиться на проектах с быстрым экономическим эффектом — снижение затрат на средства "
        "защиты растений, удобрения и ГСМ за счёт точного земледелия, рост урожайности и "
        "производительности труда — и пересмотреть низкоэффективные инициативы.")
    if weakest:
        txt += (f" Наиболее низкое значение отмечается по {weakest} составляющей, её развитие следует "
                "считать приоритетным.")
    return "неэффективна", txt


def _latest(rows):
    out = {}
    for r in sorted(rows, key=lambda x: x.id):
        out[r.organization_id] = r
    return out


def build_recommendations(db: Session, allowed_ids, *, organization_id=None, indicator=None,
                          region=None, district=None) -> list[dict]:
    """Список рекомендаций по организациям и показателям с учётом фильтров."""
    omap = org_region_map(db)

    mq = select(MaturityAssessment)
    eq = select(EfficiencyAssessment)
    if allowed_ids is not None:
        if not allowed_ids:
            return []
        mq = mq.where(MaturityAssessment.organization_id.in_(allowed_ids))
        eq = eq.where(EfficiencyAssessment.organization_id.in_(allowed_ids))
    mat = _latest(db.execute(mq).scalars().all())
    eff = _latest(db.execute(eq).scalars().all())

    org_ids = set(mat) | set(eff)
    if allowed_ids is not None:
        org_ids &= set(allowed_ids)
    if organization_id:
        org_ids &= {organization_id}

    want = [indicator] if indicator else [k for k, _ in INDICATORS]
    items: list[dict] = []
    for oid in sorted(org_ids):
        info = omap.get(oid, {})
        oreg = info.get("region", "Не указан")
        odist = info.get("district")
        if region and oreg != region:
            continue
        if district and odist != district:
            continue
        m = mat.get(oid)
        e = eff.get(oid)
        generators = {
            "need": lambda: _rec_need(m.need_avg if m else None),
            "capability": lambda: _rec_capability(m.capability_avg if m else None),
            "maturity": lambda: _rec_maturity(m.maturity if m else None, m.zone if m else None),
            "efficiency": lambda: _rec_efficiency(
                e.coefficient if e else None,
                e.economic_index if e else None,
                e.ecological_index if e else None,
                e.social_index if e else None),
        }
        values = {
            "need": m.need_avg if m else None,
            "capability": m.capability_avg if m else None,
            "maturity": m.maturity if m else None,
            "efficiency": e.coefficient if e else None,
        }
        for key in want:
            if key not in generators:
                continue
            level, text = generators[key]()
            items.append({
                "organization_id": oid,
                "organization": info.get("name", f"#{oid}"),
                "region": oreg,
                "district": odist,
                "indicator": key,
                "indicator_label": INDICATOR_LABELS[key],
                "value": values[key],
                "level": level,
                "text": text,
            })
    return items
