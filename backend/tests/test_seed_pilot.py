"""Проверка загрузки пилотных данных (Спринт 8, задача 1): 7 организаций,
оценки зрелости и эффективности, привязка к областям, модель долгового риска."""
from sqlalchemy import func, select

from app.db.seed import seed_pilot
from app.models import models as m


def test_seed_pilot_loads_pilot_organizations(db):
    seed_pilot(db)
    orgs = db.execute(select(m.Organization)).scalars().all()
    assert len(orgs) == 7
    # все организации привязаны к области
    assert all(o.region_id for o in orgs)
    # оценки зрелости и эффективности рассчитаны для всех
    assert db.execute(select(func.count()).select_from(m.MaturityAssessment)).scalar() == 7
    assert db.execute(select(func.count()).select_from(m.EfficiencyAssessment)).scalar() == 7
    # ведущая организация — КЭц и зрелость соответствуют выверенным значениям
    ship = db.execute(select(m.Organization)
                      .where(m.Organization.name.like("%Шипяны%"))).scalar_one()
    eff = db.execute(select(m.EfficiencyAssessment)
                     .where(m.EfficiencyAssessment.organization_id == ship.id)).scalar_one()
    mat = db.execute(select(m.MaturityAssessment)
                     .where(m.MaturityAssessment.organization_id == ship.id)).scalar_one()
    assert round(eff.coefficient, 2) == 1.19
    assert round(mat.maturity, 2) == 0.36
    # модель долгового риска загружена (хотя бы один проект)
    assert db.execute(select(func.count()).select_from(m.Project)).scalar() >= 1
