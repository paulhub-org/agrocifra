"""Сквозной (E2E) сценарий через ASGI FastAPI: вход → оценки → отчёт → импорт модели → оптимизация.

Браузерный E2E в песочнице недоступен, поэтому проверяется вся цепочка на уровне API
(реальные HTTP-вызовы к приложению). Покрывает интеграцию модулей Спринтов 2–6.
"""
from pathlib import Path

import pytest

SAMPLE = Path(__file__).parent / "data" / "debt_risk_model_sample.xlsx"


def _login(client, u="office", p="office123"):
    r = client.post("/auth/login", data={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_e2e_full_workflow(client):
    h = _login(client)

    # 1. служебные эндпоинты
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/version").json()["app"]

    # 2. оценка цифровой зрелости (среднее геометрическое потребности и возможностей)
    r = client.post("/data/assessments/maturity", headers=h,
                    json={"organization_name": "РСДУП «Шипяны-АСК»",
                          "need_avg": 0.46, "capability_avg": 0.28})
    assert r.status_code in (200, 201), r.text
    assert r.json()["zone"] in ("низкая", "средняя", "высокая")

    # 3. оценка эффективности цифровизации (интегральный КЭц)
    r = client.post("/data/assessments/efficiency", headers=h, json={
        "organization_name": "РСДУП «Шипяны-АСК»",
        "cost_total_before": 6150100, "area_before_ha": 4500, "cost_per_ha_after": 1313.58,
        "yield_before": 0.59, "yield_after": 0.6,
        "profit_after": 1222000, "total_costs": 26232000,
        "profit_before": 1684000, "total_costs_before": 21749000,
        "petrol_before_t": 790, "petrol_after_t": 687,
        "diesel_before_t": 1350, "diesel_after_t": 1320,
        "productivity_after": 191934.21, "productivity_before": 173503.31,
        "taxes_after": 504000, "taxes_before": 359000,
    })
    assert r.status_code in (200, 201), r.text
    assert r.json()["coefficient"] > 0

    # 4. сводка и выгрузка отчёта (Excel)
    s = client.get("/reports/summary", headers=h)
    assert s.status_code == 200
    xlsx = client.get("/reports/export.xlsx", headers=h)
    assert xlsx.status_code == 200
    assert xlsx.content[:2] == b"PK"            # сигнатура zip/xlsx

    # 5. импорт Excel-модели долгового риска (CAPEX→стоимость, NPV→эффект, предел кредитоспособности)
    with open(SAMPLE, "rb") as f:
        imp = client.post("/optimization/projects/import-model", headers=h,
                          files={"file": ("model.xlsx", f.read(),
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                          data={"organization_name": "РСДУП «Шипяны-АСК»"})
    assert imp.status_code == 201, imp.text
    assert imp.json()["cost"] == pytest.approx(840.0)

    # 6. оптимизация по данным БД (финансирование ограничено кредитоспособностью)
    run = client.post("/optimization/run", headers=h, json={"budget": 1000})
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["status"] == "Optimal"
    assert body["allocations"][0]["funding"] <= 448.36 + 1.0

    # 7. оптимизация по явному портфелю организаций
    run2 = client.post("/optimization/run", headers=h, json={
        "budget": 4000000, "coverage_weight": 0, "threshold": 1.0,
        "projects": [
            {"name": "Шипяны-АСК", "cost": 1200000, "effect": 2100000, "score": 1.19},
            {"name": "Достоево", "cost": 900000, "effect": 1300000, "var_type": "binary", "score": 1.21},
            {"name": "Криничная", "cost": 1000000, "effect": 1500000, "score": 1.06, "credit_limit": 500000},
        ],
    })
    assert run2.status_code == 201, run2.text
    assert run2.json()["status"] == "Optimal"
    assert run2.json()["selected_count"] >= 1
