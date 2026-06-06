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
