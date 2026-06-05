"""Тесты финансово-математического модуля оптимизации затрат (PuLP/CBC, комбинированный подход)."""
import pytest

from app.services.optimization import OptProject, optimize_allocation


def _login(client, username, password):
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ───────────────────────── модуль расчёта (optimize_allocation) ─────────────────────────
def test_prefers_higher_effect_to_cost_ratio():
    projects = [
        OptProject(key="A", cost=100, effect=180, var_type="continuous"),  # ратио 1,8
        OptProject(key="B", cost=100, effect=90, var_type="continuous"),   # ратио 0,9
    ]
    r = optimize_allocation(projects, budget=100)
    a = {x.key: x for x in r.allocations}
    assert a["A"].selected and a["A"].funding == pytest.approx(100)
    assert not a["B"].selected
    assert r.total_spend <= 100 + 1e-6


def test_budget_constraint_respected():
    projects = [OptProject(key=str(i), cost=100, effect=150, var_type="continuous") for i in range(5)]
    r = optimize_allocation(projects, budget=250)
    assert r.total_spend <= 250 + 1e-6
    assert r.status == "Optimal"


def test_binary_is_all_or_nothing():
    projects = [
        OptProject(key="bin", cost=120, effect=200, var_type="binary"),
        OptProject(key="cont", cost=100, effect=120, var_type="continuous"),
    ]
    r = optimize_allocation(projects, budget=120)
    a = {x.key: x for x in r.allocations}
    # бинарный проект финансируется целиком либо не выбирается
    assert a["bin"].funded_share in (pytest.approx(0.0), pytest.approx(1.0))


def test_continuous_respects_min_share():
    projects = [OptProject(key="c", cost=100, effect=120, var_type="continuous", min_share=0.5)]
    r = optimize_allocation(projects, budget=70)
    c = r.allocations[0]
    assert c.selected and 0.5 - 1e-6 <= c.funded_share <= 1.0 + 1e-6


def test_credit_limit_caps_funding():
    # граница кредитоспособности / долгового риска: финансирование ≤ credit_limit
    # (credit_limit ≥ min_share·cost, иначе проект нежизнеспособен и не финансируется)
    projects = [OptProject(key="d", cost=100, effect=300, var_type="continuous",
                           min_share=0.5, credit_limit=60)]
    r = optimize_allocation(projects, budget=100)
    d = r.allocations[0]
    assert d.selected and d.funding <= 60 + 1e-6
    assert d.funding == pytest.approx(60, abs=1.0)        # доводится до кредитного предела
    assert d.effect == pytest.approx(300 * 0.6, abs=1.0)


def test_credit_limit_below_min_share_makes_project_infeasible():
    # если min_share·cost > credit_limit — проект не может быть профинансирован
    projects = [OptProject(key="d", cost=100, effect=300, var_type="continuous",
                           min_share=0.5, credit_limit=40)]
    r = optimize_allocation(projects, budget=100)
    assert not r.allocations[0].selected


def test_coverage_weight_increases_threshold_coverage():
    projects = [
        OptProject(key="hi_effect", cost=100, effect=200, var_type="continuous", score=0.5),
        OptProject(key="above_thr", cost=100, effect=50, var_type="continuous", score=1.5),
    ]
    base = optimize_allocation(projects, budget=100, coverage_weight=0.0, threshold=1.0)
    weighted = optimize_allocation(projects, budget=100, coverage_weight=1000.0, threshold=1.0)
    assert base.above_threshold_count == 0
    assert weighted.above_threshold_count >= 1


def test_empty_and_zero_budget():
    assert optimize_allocation([], budget=100).status == "Optimal"
    r = optimize_allocation([OptProject(key="a", cost=50, effect=80)], budget=0)
    assert r.selected_count == 0 and r.total_spend == 0


def test_validation_errors():
    with pytest.raises(ValueError):
        optimize_allocation([OptProject(key="a", cost=0, effect=10)], budget=100)
    with pytest.raises(ValueError):
        optimize_allocation([OptProject(key="a", cost=10, effect=10)], budget=-1)
    with pytest.raises(ValueError):
        optimize_allocation([OptProject(key="a", cost=10, effect=10, var_type="bad")], budget=100)


# ───────────────────────────────── API ─────────────────────────────────
def _payload():
    return {
        "budget": 200, "coverage_weight": 0.0, "threshold": 1.0,
        "projects": [
            {"name": "Шипяны-АСК", "cost": 100, "effect": 180, "var_type": "continuous", "score": 1.19},
            {"name": "Достоево", "cost": 120, "effect": 130, "var_type": "binary", "score": 1.21},
            {"name": "ДолжаАгро", "cost": 80, "effect": 60, "var_type": "continuous", "score": 0.56},
            {"name": "Криничная", "cost": 90, "effect": 110, "var_type": "continuous",
             "score": 1.06, "credit_limit": 45},
        ],
    }


def test_run_optimization_explicit_projects(client):
    token = _login(client, "office", "office123")
    r = client.post("/optimization/run", json=_payload(),
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "Optimal"
    assert body["total_spend"] <= 200 + 1e-6
    assert len(body["allocations"]) == 4
    assert "id" in body and body["selected_count"] >= 1


def test_run_requires_privileged_role(client):
    token = _login(client, "org", "org123")
    r = client.post("/optimization/run", json=_payload(),
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_run_without_projects_returns_422(client):
    token = _login(client, "gov", "gov123")
    r = client.post("/optimization/run", json={"budget": 100},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422  # нет проектов в БД и не переданы явно


def test_list_and_get_runs(client):
    token = _login(client, "office", "office123")
    h = {"Authorization": f"Bearer {token}"}
    run_id = client.post("/optimization/run", json=_payload(), headers=h).json()["id"]
    runs = client.get("/optimization/runs", headers=h)
    assert runs.status_code == 200 and any(x["id"] == run_id for x in runs.json())
    detail = client.get(f"/optimization/runs/{run_id}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["total_spend"] <= 200 + 1e-6
