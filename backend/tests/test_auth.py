"""Тесты аутентификации (JWT) и ролевого доступа (Спринт 4)."""


def _token(client, username, password):
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_returns_token_and_role(client):
    r = client.post("/auth/login", data={"username": "office", "password": "office123"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    assert body["role"] == "digitalization_office"


def test_me_with_token(client):
    token = _token(client, "org", "org123")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    me = r.json()
    assert me["login"] == "org" and me["role"] == "organization"


def test_login_wrong_password(client):
    r = client.post("/auth/login", data={"username": "office", "password": "WRONG"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_protected_list_requires_auth(client):
    assert client.get("/data/organizations").status_code == 401
    token = _token(client, "gov", "gov123")
    r = client.get("/data/organizations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_rbac_organization_forbidden_on_sync(client):
    token = _token(client, "org", "org123")
    r = client.post("/data/etl/jotform/efficiency/sync",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403  # роль «организация» не имеет права на синхронизацию


def test_rbac_office_allowed_on_sync(client, monkeypatch):
    from app.api import data as data_api
    monkeypatch.setattr(data_api.etl, "sync_efficiency_from_jotform",
                        lambda db: {"loaded": 0, "skipped": 0, "errors": []})
    token = _token(client, "office", "office123")
    r = client.post("/data/etl/jotform/efficiency/sync",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200  # роль «офис цифровизации» допущена


def test_manual_efficiency_entry_computes_coefficient(client):
    token = _token(client, "org", "org123")
    payload = {
        "organization_name": "РСДУП «Шипяны-АСК»",
        "cost_total_before": 6150100, "area_before_ha": 4500, "cost_per_ha_after": 1313.58,
        "yield_before": 0.59, "yield_after": 0.60,
        "profit_after": 1222000, "total_costs": 26232000, "profit_before": 1684000,
        "total_costs_before": 21749000,
        "petrol_before_t": 790, "petrol_after_t": 687, "diesel_before_t": 1350, "diesel_after_t": 1320,
        "productivity_after": 191934.21, "productivity_before": 173503.31,
        "taxes_after": 504000, "taxes_before": 359000,
    }
    r = client.post("/data/assessments/efficiency", json=payload,
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    assert abs(r.json()["coefficient"] - 1.19) < 0.01


def test_manual_maturity_entry(client):
    token = _token(client, "org", "org123")
    r = client.post("/data/assessments/maturity",
                    json={"organization_name": "Озёрный", "need_avg": 0.55, "capability_avg": 0.67},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    assert r.json()["zone"] == "высокая"
