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


def _office_headers(client):
    t = client.post("/auth/login", data={"username": "office", "password": "office123"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_registration_captures_region_and_district(client):
    """V2.0, задачи 19/20/21: ФИО отдельно, область/район учитываются по роли."""
    assert client.post("/auth/register", json={
        "login": "reg_obl", "password": "secret123", "role": "regional_operator",
        "full_name": "Региональный Р.Р.", "region": "Минская",
    }).status_code == 201
    assert client.post("/auth/register", json={
        "login": "reg_dist", "password": "secret123", "role": "district_operator",
        "full_name": "Районный Р.Р.", "region": "Минская", "district": "Смолевичский",
    }).status_code == 201

    pending = client.get("/auth/pending", headers=_office_headers(client)).json()
    by_login = {u["login"]: u for u in pending}
    assert {"reg_obl", "reg_dist"} <= set(by_login)
    # область учтена — region_id проставлен (задачи 13/21)
    assert by_login["reg_obl"]["region_id"] is not None
    assert by_login["reg_dist"]["region_id"] is not None
    # ФИО отдельным полем (задача 19)
    assert by_login["reg_obl"]["full_name"] == "Региональный Р.Р."


def test_summary_by_district(db):
    """V2.0, задача 5: разрез по районам для карт «… по районам»."""
    reg = m.Region(name="Тестобласть")
    db.add(reg)
    db.flush()
    a = _org(db, "Орг-А", reg.id, "Перворайон")
    b = _org(db, "Орг-Б", reg.id, "Второрайон")
    _maturity(db, a.id, 0.4, 0.3, 0.35)
    _maturity(db, b.id, 0.5, 0.4, 0.45)

    s = reporting.summary(db)
    by_d = {r["district"]: r for r in s["by_district"]}
    assert set(by_d) == {"Перворайон", "Второрайон"}
    assert by_d["Перворайон"]["mean_maturity"] == 0.35
    # организации без района в разрез не попадают
    c = _org(db, "Орг-В", reg.id, None)
    _maturity(db, c.id, 0.6, 0.5, 0.55)
    assert None not in {r["district"] for r in reporting.summary(db)["by_district"]}


def _efficiency(db, org_id, coef, eco=0.5, env=0.5, soc=0.5, zone="эффективна"):
    db.add(m.EfficiencyAssessment(organization_id=org_id, economic_index=eco, ecological_index=env,
                                  social_index=soc, coefficient=coef, zone=zone, source="manual"))
    db.flush()


def test_recommendations_engine_and_filters(db):
    """V2.0, задача 3: рекомендации по 4 показателям + фильтры по показателю/организации."""
    from app.services import recommendations as rec
    reg = m.Region(name="Тестобласть")
    db.add(reg)
    db.flush()
    a = _org(db, "Орг-А", reg.id, "Перворайон")
    b = _org(db, "Орг-Б", reg.id, "Второрайон")
    _maturity(db, a.id, 0.7, 0.6, 0.65, zone="высокая")
    _maturity(db, b.id, 0.2, 0.2, 0.20, zone="средняя")
    _efficiency(db, a.id, 1.19, eco=0.6, env=0.5, soc=0.7)   # эффективна
    _efficiency(db, b.id, 0.56, eco=0.3, env=0.5, soc=0.6)   # неэффективна; слабее всего экономическая

    items = rec.build_recommendations(db, None)
    assert len(items) == 8  # 2 организации × 4 показателя
    assert {i["indicator"] for i in items} == {"need", "capability", "maturity", "efficiency"}

    eff = {i["organization"]: i for i in items if i["indicator"] == "efficiency"}
    assert eff["Орг-А"]["level"] == "эффективна" and "≥ 1,0" in eff["Орг-А"]["text"]
    assert eff["Орг-Б"]["level"] == "неэффективна" and "< 1,0" in eff["Орг-Б"]["text"]
    assert "экономической" in eff["Орг-Б"]["text"]  # приоритет — самая слабая составляющая

    # фильтр по показателю
    only_mat = rec.build_recommendations(db, None, indicator="maturity")
    assert {i["indicator"] for i in only_mat} == {"maturity"} and len(only_mat) == 2
    # фильтр по организации
    only_a = rec.build_recommendations(db, None, organization_id=a.id)
    assert {i["organization"] for i in only_a} == {"Орг-А"} and len(only_a) == 4
    # фильтр по району
    only_d = rec.build_recommendations(db, None, district="Второрайон")
    assert {i["organization"] for i in only_d} == {"Орг-Б"}


def test_recommendations_endpoint_and_export(client):
    headers = _office_headers(client)
    r = client.get("/recommendations", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert [i["key"] for i in body["indicators"]] == ["need", "capability", "maturity", "efficiency"]
    assert isinstance(body["items"], list)
    for fmt in ("xlsx", "docx", "pdf"):
        assert client.get(f"/recommendations/export.{fmt}", headers=headers).status_code == 200
    assert client.get("/recommendations/export.txt", headers=headers).status_code == 404
