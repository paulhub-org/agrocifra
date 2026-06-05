"""Тесты подключения Excel-модели «Оценка проекта и долгового риска» к оптимизации."""
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.models import DigitalProjectItem, Project
from app.services import etl
from app.services.debt_risk_model import (
    credit_limit_from_finance,
    parse_debt_risk_model,
    project_finance_to_opt,
)
from app.services.optimization import candidate_projects_from_db

SAMPLE = Path(__file__).parent / "data" / "debt_risk_model_sample.xlsx"


# ───────────────────────── парсер модели ─────────────────────────
def test_parse_extracts_cost_effect_and_debt_risk():
    pf = parse_debt_risk_model(SAMPLE)
    assert pf.capex_total == pytest.approx(840.0)          # 700+80+60+0
    assert pf.capex_by_year == [700, 80, 60, 0]
    assert pf.npv == pytest.approx(172.84, abs=0.1)
    assert pf.irr == pytest.approx(0.2702, abs=0.001)
    assert pf.npv_stress == pytest.approx(-288.65, abs=0.1)
    assert pf.irr_stress == pytest.approx(-0.2238, abs=0.001)
    assert pf.dscr_min == pytest.approx(0.694, abs=0.01)   # мин. по годам с обслуживанием долга
    assert pf.icr_min == pytest.approx(6.371, abs=0.01)
    assert pf.dscr_stress_min == pytest.approx(0.1065, abs=0.001)


def test_credit_limit_reflects_debt_capacity():
    pf = parse_debt_risk_model(SAMPLE)
    # DSCR_min 0,694 < норматив 1,3 → лимит = 840·0,694/1,3 ≈ 448,36
    assert credit_limit_from_finance(pf, 1.3) == pytest.approx(448.36, abs=1.0)
    # при мягком нормативе (≤ DSCR_min) ограничение не накладывается
    assert credit_limit_from_finance(pf, 0.5) is None


def test_converter_builds_opt_project():
    pf = parse_debt_risk_model(SAMPLE)
    op = project_finance_to_opt(pf, "Шипяны-АСК", score=1.19)
    assert op.cost == pytest.approx(840.0)
    assert op.effect == pytest.approx(172.84, abs=0.1)     # NPV база
    assert op.credit_limit == pytest.approx(448.36, abs=1.0)
    assert op.cap() == pytest.approx(448.36, abs=1.0)      # cap = min(cost, credit_limit)
    # стресс-режим использует NPV при стрессе
    assert project_finance_to_opt(pf, "X", use_stress=True).effect == pytest.approx(-288.65, abs=0.1)


# ───────────────────────── ETL → кандидат оптимизации ─────────────────────────
def test_load_project_finance_then_build_candidate(db):
    res = etl.load_project_finance(db, "Шипяны-АСК", SAMPLE)
    assert res["cost"] == pytest.approx(840.0)
    assert res["effect"] == pytest.approx(172.84, abs=0.1)
    assert res["credit_limit"] == pytest.approx(448.36, abs=1.0)

    proj = db.execute(select(Project)).scalar_one()
    assert proj.capex == pytest.approx(840.0) and proj.credit_limit == pytest.approx(448.36, abs=1.0)
    assert db.execute(select(DigitalProjectItem)).scalar_one().npv == pytest.approx(172.84, abs=0.1)

    cands = candidate_projects_from_db(db)
    assert len(cands) == 1
    c = cands[0]
    assert c.name == "Шипяны-АСК"
    assert c.cost == pytest.approx(840.0) and c.effect == pytest.approx(172.84, abs=0.1)
    assert c.credit_limit == pytest.approx(448.36, abs=1.0)


# ───────────────────────── API: загрузка модели и оптимизация по БД ─────────────────────────
def _login(client, u, p):
    return client.post("/auth/login", data={"username": u, "password": p}).json()["access_token"]


def _upload(client, token):
    with open(SAMPLE, "rb") as f:
        return client.post(
            "/optimization/projects/import-model",
            files={"file": ("model.xlsx", f.read(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"organization_name": "Шипяны-АСК"},
            headers={"Authorization": f"Bearer {token}"},
        )


def test_import_model_endpoint(client):
    r = _upload(client, _login(client, "office", "office123"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cost"] == pytest.approx(840.0)
    assert body["effect"] == pytest.approx(172.84, abs=0.1)
    assert body["credit_limit"] == pytest.approx(448.36, abs=1.0)


def test_import_model_forbidden_for_organization_role(client):
    r = _upload(client, _login(client, "org", "org123"))
    assert r.status_code == 403


def test_optimization_uses_imported_costs_and_credit_limit(client):
    token = _login(client, "office", "office123")
    _upload(client, token)
    # бюджет выше стоимости, но финансирование ограничено кредитным пределом (≈448)
    r = client.post("/optimization/run", json={"budget": 1000},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "Optimal"
    alloc = body["allocations"][0]
    assert alloc["selected"] is True
    assert alloc["funding"] <= 448.36 + 1.0      # ограничено кредитоспособностью
    assert alloc["funding"] < 840                # не профинансировано полностью
