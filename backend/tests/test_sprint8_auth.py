"""Спринт 8: регистрация с подтверждением (задача 16) и режим «просмотр как» (задачи 10/14)."""


def _login(client, login, password):
    r = client.post("/auth/login", data={"username": login, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_registration_requires_confirmation(client):
    # новая заявка создаётся неактивной
    r = client.post("/auth/register", json={
        "login": "newfarm", "password": "secret123",
        "role": "organization", "full_name": "Новое хозяйство",
    })
    assert r.status_code == 201
    # пока не подтверждена — вход запрещён (403)
    r = client.post("/auth/login", data={"username": "newfarm", "password": "secret123"})
    assert r.status_code == 403
    # дубликат логина — 409
    r = client.post("/auth/register", json={"login": "newfarm", "password": "x", "role": "organization"})
    assert r.status_code == 409
    # недопустимая роль — 422
    r = client.post("/auth/register", json={"login": "x2", "password": "x", "role": "superuser"})
    assert r.status_code == 422


def test_pending_and_activate_flow(client):
    client.post("/auth/register", json={"login": "farm2", "password": "secret123", "role": "organization"})
    office = _login(client, "office", "office123")
    # офис видит заявку в списке ожидающих
    pending = client.get("/auth/pending", headers=_auth(office)).json()
    target = next(u for u in pending if u["login"] == "farm2")
    # организация не имеет доступа к списку заявок (403)
    org = _login(client, "org", "org123")
    assert client.get("/auth/pending", headers=_auth(org)).status_code == 403
    # офис подтверждает — после этого вход работает
    r = client.post(f"/auth/users/{target['id']}/activate", headers=_auth(office))
    assert r.status_code == 200
    assert _login(client, "farm2", "secret123")


def test_switch_role_office_only(client):
    office = _login(client, "office", "office123")
    r = client.post("/auth/switch-role", json={"role": "state_authority"}, headers=_auth(office))
    assert r.status_code == 200
    assert r.json()["role"] == "state_authority"
    # не-офис не может переключать роль (403)
    org = _login(client, "org", "org123")
    assert client.post("/auth/switch-role", json={"role": "state_authority"},
                       headers=_auth(org)).status_code == 403
