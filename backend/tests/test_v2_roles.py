"""V2.0, задачи 1/13/14: роль «районный оператор» и ролевое ограничение выборок."""
from app.api import data as data_api
from app.core.deps import scope_filters
from app.models import models as m
from app.models.models import Role, UserAccount
from app.services import reporting


def _org(db, name, region_id, district):
    o = m.Organization(name=name, region_id=region_id, district=district)
    db.add(o)
    db.flush()
    return o


def _maturity(db, org_id, need, cap, mat, zone="средняя"):
    db.add(m.MaturityAssessment(organization_id=org_id, need_avg=need,
                                capability_avg=cap, maturity=mat, zone=zone, source="manual"))
    db.flush()


def test_role_enum_and_demo_login_have_district_operator():
    from app.api.auth import _DEMO_LOGIN
    assert Role.district_operator.value == "district_operator"
    assert _DEMO_LOGIN[Role.district_operator.value] == "district"


def test_scope_filters_per_role():
    org = UserAccount(role=Role.organization.value, organization_id=7)
    reg = UserAccount(role=Role.regional_operator.value, region_id=3)
    dist = UserAccount(role=Role.district_operator.value, region_id=3, district="Смолевичский")
    office = UserAccount(role=Role.digitalization_office.value)
    assert scope_filters(org) == (7, None, None)
    assert scope_filters(reg) == (None, 3, None)
    assert scope_filters(dist) == (None, 3, "Смолевичский")
    assert scope_filters(office) == (None, None, None)


def test_district_operator_sees_only_its_district(db):
    reg = m.Region(name="Тестобласть")
    db.add(reg)
    db.flush()
    a = _org(db, "Орг-А", reg.id, "Перворайон")
    b = _org(db, "Орг-Б", reg.id, "Второрайон")
    _maturity(db, a.id, 0.4, 0.3, 0.35)
    _maturity(db, b.id, 0.5, 0.4, 0.45)

    user = UserAccount(login="d1", password_hash="x", role=Role.district_operator.value,
                       region_id=reg.id, district="Перворайон")
    db.add(user)
    db.flush()

    # data-слой
    assert data_api._scoped_org_ids(db, user) == [a.id]
    # сводка/отчёты — только организации района
    s = reporting.summary(db, region_id=reg.id, district="Перворайон")
    assert s["overall"]["organizations"] == 1
    assert [r["name"] for r in s["maturity_by_org"]] == ["Орг-А"]
    # область целиком видит обе организации
    s_region = reporting.summary(db, region_id=reg.id)
    assert s_region["overall"]["organizations"] == 2
