"""Тесты отчётов, экспорта и эндпоинтов визуализации (Спринт 5)."""
import io
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import select

from app.models.models import Organization
from app.services import exporters, reporting
from app.services.etl import import_efficiency_from_json, import_maturity_from_excel

DATA = Path(__file__).parent / "data"


@pytest.fixture
def populated(db):
    import_efficiency_from_json(db, DATA / "pilot_efficiency.json")   # 6 организаций
    import_maturity_from_excel(db, DATA / "Pilot_Organizations.xlsx")  # 7 организаций
    return db


# ─────────────────────────── агрегация ───────────────────────────
def test_summary_aggregates(populated):
    s = reporting.summary(populated)
    assert s["overall"]["efficiency_count"] == 7
    assert s["overall"]["maturity_count"] == 7
    assert s["overall"]["mean_ke"] == pytest.approx(1.00, abs=0.01)
    assert s["overall"]["mean_maturity"] == pytest.approx(0.35, abs=0.01)
    assert len(s["efficiency_by_org"]) == 7
    assert s["overall"]["efficiency_effective"] == sum(
        1 for r in s["efficiency_by_org"] if r["coefficient"] > 1.0
    )
    assert s["by_region"]  # хотя бы один разрез (регион «Не указан»)


def test_organization_report_before_after(populated):
    org = populated.execute(
        select(Organization).where(Organization.name.like("%Шипяны%"))
    ).scalar_one()
    rep = reporting.organization_report(populated, org.id)
    labels = {b["indicator"] for b in rep["before_after"]}
    assert "Урожайность" in labels and "Производительность труда" in labels
    yld = next(b for b in rep["before_after"] if b["indicator"] == "Урожайность")
    assert yld["before"] == pytest.approx(0.59) and yld["after"] == pytest.approx(0.60, abs=0.01)


# ─────────────────────────── экспорт ───────────────────────────
def test_export_excel(populated):
    content, name, mime = exporters.build_excel(populated)
    assert content and name.endswith(".xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(content))
    assert {"Эффективность", "Зрелость", "Сводка по регионам"} <= set(wb.sheetnames)
    assert wb["Эффективность"].max_row >= 8  # заголовок + 7 организаций


def test_export_word(populated):
    from docx import Document
    content, name, mime = exporters.build_word(populated)
    assert content and name.endswith(".docx")
    doc = Document(io.BytesIO(content))
    assert len(doc.tables) >= 2


def test_export_pdf(populated):
    content, name, mime = exporters.build_pdf(populated)
    assert name.endswith(".pdf") and content.startswith(b"%PDF")
    assert len(content) > 1500


# ─────────────────────────── эндпоинты ───────────────────────────
def _token(client, u="gov", p="gov123"):
    return client.post("/auth/login", data={"username": u, "password": p}).json()["access_token"]


def test_summary_endpoint_requires_auth(client):
    assert client.get("/reports/summary").status_code == 401
    r = client.get("/reports/summary", headers={"Authorization": f"Bearer {_token(client)}"})
    assert r.status_code == 200 and "overall" in r.json()


@pytest.mark.parametrize("fmt,mime", [
    ("xlsx", "spreadsheetml"),
    ("docx", "wordprocessingml"),
    ("pdf", "application/pdf"),
])
def test_export_endpoints(client, fmt, mime):
    r = client.get(f"/reports/export.{fmt}",
                   headers={"Authorization": f"Bearer {_token(client)}"})
    assert r.status_code == 200, r.text
    assert mime in r.headers["content-type"]
    assert len(r.content) > 500
