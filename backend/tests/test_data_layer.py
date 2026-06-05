"""Тесты слоя данных и ETL: импорт Excel/JSON и синхронизация Jotform (книга v2, 7 организаций)."""
import json
import statistics
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from app.models.models import EfficiencyAssessment, MaturityAssessment, Organization, RawSubmission
from app.services.etl import (
    import_efficiency_from_json,
    import_maturity_from_excel,
    sync_efficiency_from_jotform,
    sync_maturity_from_jotform,
)
from app.services.jotform_client import JotformClient
from app.services.jotform_mapping import maturity_aggregates_from_answers

DATA = Path(__file__).parent / "data"


# ─────────────────── импорт зрелости из Excel (пилотная книга v2, 7 организаций) ───────────────────
def test_import_maturity_from_excel_pilot(db):
    res = import_maturity_from_excel(db, DATA / "Pilot_Organizations.xlsx")
    assert res["loaded"] == 7, res
    rows = db.execute(select(MaturityAssessment)).scalars().all()
    assert len(rows) == 7
    # итоговый уровень = геометрическое среднее потребности и возможностей; среднее ≈ 0,35
    assert statistics.mean(r.maturity for r in rows) == pytest.approx(0.35, abs=0.01)
    assert {r.zone for r in rows} <= {"низкая", "средняя", "высокая"}
    assert any(r.zone == "высокая" for r in rows)


# ─────────────────── импорт эффективности из JSON-фикстуры (7 организаций) ───────────────────
def test_import_efficiency_from_json_matches_benchmarks(db):
    res = import_efficiency_from_json(db, DATA / "pilot_efficiency.json")
    assert res["loaded"] == 7
    by_name = {
        db.get(Organization, a.organization_id).name: a
        for a in db.execute(select(EfficiencyAssessment)).scalars().all()
    }
    fixture = {r["name"]: r for r in json.loads((DATA / "pilot_efficiency.json").read_text("utf-8"))}
    # все 7 организаций воспроизводят интегральный коэффициент формы (r55)
    for name, rec in fixture.items():
        assert by_name[name].coefficient == pytest.approx(rec["ke"], abs=0.01), name
    assert statistics.mean(a.coefficient for a in by_name.values()) == pytest.approx(1.00, abs=0.01)


# ─────────────────── синхронизация с Jotform (MockTransport) ───────────────────
def _mock_jotform(answers: dict) -> JotformClient:
    payload = {"content": [{"id": "100", "answers": answers}]}

    def handler(request: httpx.Request) -> httpx.Response:
        if "/submissions" in request.url.path:
            if request.url.params.get("offset", "0") in ("0", None):
                return httpx.Response(200, json=payload)
            return httpx.Response(200, json={"content": []})
        return httpx.Response(200, json={"content": {}})

    transport = httpx.MockTransport(handler)
    return JotformClient(api_key="test", base_url="https://eu-api.jotform.com",
                         client=httpx.Client(transport=transport))


def test_sync_efficiency_from_jotform(db, efficiency_answers):
    res = sync_efficiency_from_jotform(db, client=_mock_jotform(efficiency_answers))
    assert res["loaded"] == 1 and not res["errors"], res
    a = db.execute(select(EfficiencyAssessment)).scalar_one()
    assert a.coefficient == pytest.approx(1.19, abs=0.01)   # Шипяны-АСК
    assert a.source == "jotform" and a.external_id == "100"
    assert db.execute(select(RawSubmission)).scalar_one().processed is True


def test_sync_is_idempotent(db, efficiency_answers):
    sync_efficiency_from_jotform(db, client=_mock_jotform(efficiency_answers))
    res2 = sync_efficiency_from_jotform(db, client=_mock_jotform(efficiency_answers))
    assert res2["loaded"] == 0 and res2["skipped"] == 1, res2
    assert db.execute(select(func.count()).select_from(EfficiencyAssessment)).scalar_one() == 1


# ─────────────────── зрелость из Jotform: режим агрегатов (по тексту полей) ───────────────────
def test_maturity_aggregates_resolution(maturity_answers):
    need, cap = maturity_aggregates_from_answers(maturity_answers)
    assert need == pytest.approx(0.46)
    assert cap == pytest.approx(0.28)


def test_sync_maturity_aggregate_mode(db, maturity_answers):
    res = sync_maturity_from_jotform(db, client=_mock_jotform(maturity_answers), form_id="MATURITYTEST")
    assert res["loaded"] == 1 and not res["errors"], res
    a = db.execute(select(MaturityAssessment)).scalar_one()
    # итоговый уровень читается из формы: 0,36 (= sqrt(0,46·0,28)) → «средняя»
    assert a.maturity == pytest.approx(0.36, abs=0.005)
    assert a.zone == "средняя"
    assert a.need_avg == pytest.approx(0.46)
    assert a.capability_avg == pytest.approx(0.28)
    assert a.source == "jotform"
