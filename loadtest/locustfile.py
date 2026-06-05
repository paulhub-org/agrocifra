"""Нагрузочное тестирование API АгроЦифра (Locust).

Запуск (веб-интерфейс Locust на http://localhost:8089):
    pip install locust
    locust -f loadtest/locustfile.py --host http://localhost:8000
        (прямой backend; для доступа через nginx используйте --host https://ВАШ_ДОМЕН/api)

Безголовый прогон (например, 50 пользователей, 5/с, 2 минуты):
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 50 -r 5 -t 2m --csv loadtest/report
"""
from locust import HttpUser, between, task

OPT_PAYLOAD = {
    "budget": 4000000, "coverage_weight": 0.0, "threshold": 1.0,
    "projects": [
        {"name": "Шипяны-АСК", "cost": 1200000, "effect": 2100000, "score": 1.19},
        {"name": "Достоево", "cost": 900000, "effect": 1300000, "var_type": "binary", "score": 1.21},
        {"name": "Криничная", "cost": 1000000, "effect": 1500000, "score": 1.06, "credit_limit": 500000},
        {"name": "Учхоз БГСХА", "cost": 950000, "effect": 1350000, "score": 1.08},
    ],
}


class AgroCifraUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {}
        r = self.client.post("/auth/login",
                             data={"username": "office", "password": "office123"},
                             name="/auth/login")
        if r.ok:
            self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    @task(4)
    def health(self):
        self.client.get("/health", name="/health")

    @task(3)
    def summary(self):
        self.client.get("/reports/summary", headers=self.headers, name="/reports/summary")

    @task(2)
    def optimize(self):
        self.client.post("/optimization/run", json=OPT_PAYLOAD,
                         headers=self.headers, name="/optimization/run")

    @task(1)
    def list_runs(self):
        self.client.get("/optimization/runs", headers=self.headers, name="/optimization/runs")
