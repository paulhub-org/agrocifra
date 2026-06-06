"""Спринт 8: маторитет в оптимизации (задача 4), ролевое ограничение сводки
(задачи 2/3/5), последние оценки зрелости (задача 13)."""
from sqlalchemy import select

from app.db.seed import seed_pilot
from app.models import models as m
from app.services import reporting
from app.services.optimization import OptProject, optimize_allocation


def test_optimization_exposes_maturity_column():
    res = optimize_allocation(
        [OptProject(key="a", cost=100.0, effect=200.0, score=1.10, maturity=0.42)],
        budget=100.0,
    ).to_dict()
    assert res["allocations"][0]["maturity"] == 0.42


def test_summary_scoping_and_recent_maturity(db):
    seed_pilot(db)
    full = reporting.summary(db)
    assert full["overall"]["organizations"] == 7
    assert len(full["recent_maturity"]) == 5
    assert {"name", "maturity", "zone"} <= set(full["recent_maturity"][0])

    oid = db.execute(select(m.Organization.id)).scalars().first()
    scoped = reporting.summary(db, org_id=oid)
    assert scoped["overall"]["organizations"] == 1
    assert all(r["organization_id"] == oid for r in scoped["maturity_by_org"])
    assert all(r["organization_id"] == oid for r in scoped["efficiency_by_org"])


def test_summary_region_scoping(db):
    seed_pilot(db)
    # Минская область содержит две пилотные организации (Шипяны-АСК и Минскоблагросервис)
    minsk = db.execute(select(m.Region).where(m.Region.name == "Минская")).scalar_one()
    scoped = reporting.summary(db, region_id=minsk.id)
    assert scoped["overall"]["organizations"] == 2


def test_org_only_candidate_filter_and_run(db):
    """Задача 6: кандидаты ограничиваются одной организацией, расчёт идёт по её данным."""
    from app.models import models as m
    from app.services.optimization import candidate_projects_from_db, optimize_allocation

    o1 = m.Organization(name="Орг-1")
    o2 = m.Organization(name="Орг-2")
    db.add_all([o1, o2])
    db.flush()
    p1 = m.Project(organization_id=o1.id, capex=1000.0, credit_limit=None)
    p2 = m.Project(organization_id=o2.id, capex=2000.0, credit_limit=None)
    db.add_all([p1, p2])
    db.flush()
    db.add(m.DigitalProjectItem(project_id=p1.id, title="ИС-1", pclass="general",
                                npv=500.0, var_type="continuous"))
    db.add(m.DigitalProjectItem(project_id=p2.id, title="ИС-2", pclass="general",
                                npv=900.0, var_type="continuous"))
    db.commit()

    assert len(candidate_projects_from_db(db)) == 2
    only1 = candidate_projects_from_db(db, org_id=o1.id)
    assert len(only1) == 1
    assert only1[0].cost == 1000.0

    res = optimize_allocation(only1, budget=only1[0].cost).to_dict()
    assert len(res["allocations"]) == 1
    assert res["allocations"][0]["funding"] <= 1000.0
