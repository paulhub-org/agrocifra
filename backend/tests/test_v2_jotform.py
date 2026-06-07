"""Живая загрузка Jotform (V2.0, задачи 16/17/18).

Предзаполнение форм организации и идемпотентная синхронизация её показателей.
Сеть не используется: клиент Jotform заменяется заглушкой (_FakeClient).
"""
import pytest

from app.core.config import settings
from app.models.models import EfficiencyAssessment, MaturityAssessment
from app.services import etl

_ADDR = "222160, Минская область, Смолевичский р-н, аг. Шипяны"


def _cells(pairs):
    return {str(i): {"answer": v, "text": t} for i, (t, v) in enumerate(pairs, 1)}


_EFF = _cells([
    ("Наименование сельскохозяйственной организации", "РСДУП «Шипяны-АСК»"),
    ("Юридический (почтовый) адрес организации", _ADDR),
    ("Сумма затрат организации на производство продукции растительного происхождения ДО цифровизации, рублей", "6150100"),
    ("1.2.1 Площадь обрабатываемых земель ДО цифровизации, га", "4500"),
    ("Затраты организации на 1 га обрабатываемых земель, рублей/га", "1313.58"),
    ("Средняя урожайность культур в организации ДО цифровизации, тонн/га", "0.59"),
    ("2.1 Объем сожженного бензина ДО цифровизации, тонн", "790"),
    ("2.2 Объем сожженного бензина ПОСЛЕ цифровизации, тонн", "700"),
    ("2.3 Объем сожженного топлива дизельного ДО цифровизации, тонн", "1350"),
    ("2.4 Объем сожженного топлива дизельного ПОСЛЕ цифровизации, тонн", "1200"),
    ("Производительность труда ПОСЛЕ цифровизации, рублей/чел.", "191934.21"),
    ("Производительность труда ДО цифровизации, рублей/чел.", "173503.31"),
    ("Направлено денежных средств на уплату налогов и сборов ПОСЛЕ цифровизации, рублей", "300000"),
    ("Направлено денежных средств на уплату налогов и сборов ДО цифровизации, рублей", "359000"),
    ("1.1.8 Валовый сбор урожая возделываемых культур, тонн", "2700"),
    ("1.1.7 Площадь обрабатываемых земель, га", "4500"),
])
_MAT = _cells([
    ("Наименование сельскохозяйственной организации", "РСДУП «Шипяны-АСК»"),
    ("Юридический (почтовый) адрес организации", _ADDR),
    ("Среднее значение показателей потребности во внедрении цифровых технологий", "0,46"),
    ("Среднее значение показателей возможностей во внедрении цифровых технологий", "0,28"),
    ("Уровень цифровой зрелости Вашей организации", "0,36"),
])


class _FakeClient:
    """Заглушка JotformClient: отдаёт заранее заданные сабмишены, без сети."""

    def __init__(self, subs):
        self._subs = subs

    def iter_submissions(self, form_id, page_size=100):
        yield from self._subs

    def close(self):
        pass


def _eff_client():
    return _FakeClient([{"id": "501", "created_at": "2026-06-01 10:00:00", "answers": _EFF}])


def _mat_client():
    return _FakeClient([{"id": "601", "created_at": "2026-06-06 06:52:40", "answers": _MAT}])


def _hdr(client, username, password):
    tok = client.post("/auth/login", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


@pytest.fixture
def _key():
    old = settings.jotform_api_key
    settings.jotform_api_key = "TEST"
    yield
    settings.jotform_api_key = old


# ─────────────────────────── предзаполнение (17/18) ───────────────────────────
def test_prefill_maturity(_key):
    r = etl.jotform_org_prefill("РСДУП «Шипяны-АСК»", "maturity", client=_mat_client())
    assert r["available"] is True
    d = r["data"]
    assert d["need_avg"] == pytest.approx(0.46)
    assert d["capability_avg"] == pytest.approx(0.28)
    assert d["region"] == "Минская"
    assert d["district"] == "Смолевичский"


def test_prefill_efficiency(_key):
    r = etl.jotform_org_prefill("РСДУП «Шипяны-АСК»", "efficiency", client=_eff_client())
    assert r["available"] is True
    v = r["data"]["values"]
    assert v["yield_after"] == pytest.approx(0.60, abs=0.001)  # 2700 / 4500
    assert v["cost_total_before"] == pytest.approx(6150100)
    assert r["data"]["region"] == "Минская"
    assert r["data"]["district"] == "Смолевичский"


def test_prefill_not_configured():
    out = etl.jotform_org_prefill("X", "maturity", client=_mat_client())
    assert out["available"] is False and out["reason"] == "not_configured"


def test_prefill_no_submission(_key):
    out = etl.jotform_org_prefill("Несуществующая организация", "maturity", client=_mat_client())
    assert out["available"] is False and out["reason"] == "no_submission"


# ─────────────────────────── синхронизация показателей (16) ───────────────────────────
def test_sync_org_latest_idempotent(_key, db):
    r1 = etl.sync_org_latest(db, "РСДУП «Шипяны-АСК»", "efficiency", client=_eff_client())
    assert r1["available"] is True and r1.get("loaded") is True and r1["coefficient"] > 0
    r2 = etl.sync_org_latest(db, "РСДУП «Шипяны-АСК»", "efficiency", client=_eff_client())
    assert r2.get("already") is True
    assert db.query(EfficiencyAssessment).count() == 1  # повтор не создаёт дубль

    m = etl.sync_org_latest(db, "РСДУП «Шипяны-АСК»", "maturity", client=_mat_client())
    assert m["available"] is True and m["maturity"] == pytest.approx(0.36)
    assert db.query(MaturityAssessment).count() == 1


# ─────────────────────────── эндпоинты ───────────────────────────
def test_prefill_endpoint_no_org_for_office(client):
    # демо-учётка офиса не привязана к организации → available=false
    r = client.get("/data/jotform/prefill/maturity", headers=_hdr(client, "office", "office123"))
    assert r.status_code == 200 and r.json()["reason"] == "no_org"


def test_jotform_endpoints_reject_unknown_kind(client):
    headers = _hdr(client, "office", "office123")
    assert client.get("/data/jotform/prefill/wrong", headers=headers).status_code == 404
    assert client.post("/data/jotform/sync-mine/wrong", headers=headers).status_code == 404
