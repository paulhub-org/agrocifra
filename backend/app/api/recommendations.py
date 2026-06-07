"""Эндпоинты конструктора рекомендаций (V2.0, задача 3)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.reports import _stream
from app.core.deps import get_current_user, scope_filters
from app.db.session import get_db
from app.services import exporters, recommendations
from app.services.reporting import _allowed_org_ids

router = APIRouter(prefix="/recommendations", tags=["Рекомендации"])


def _allowed(db: Session, user):
    org_id, region_id, district = scope_filters(user)
    return _allowed_org_ids(db, org_id, region_id, district)


@router.get("", summary="Рекомендации по показателям цифровизации (с учётом роли)")
def get_recommendations(db: Session = Depends(get_db), user=Depends(get_current_user)):
    allowed = _allowed(db, user)
    items = recommendations.build_recommendations(db, allowed)
    return {
        "indicators": [{"key": k, "label": v} for k, v in recommendations.INDICATORS],
        "items": items,
    }


_REC_BUILDERS = {
    "xlsx": exporters.build_recommendations_excel,
    "docx": exporters.build_recommendations_word,
    "pdf": exporters.build_recommendations_pdf,
}


@router.get("/export.{fmt}", summary="Экспорт рекомендаций (Word/Excel/PDF)")
def export_recommendations(
    fmt: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    organization_id: int | None = None,
    indicator: str | None = None,
    region: str | None = None,
    district: str | None = None,
):
    builder = _REC_BUILDERS.get(fmt)
    if builder is None:
        raise HTTPException(status_code=404, detail="Неизвестный формат экспорта")
    allowed = _allowed(db, user)
    items = recommendations.build_recommendations(
        db, allowed, organization_id=organization_id, indicator=indicator,
        region=region, district=district,
    )
    return _stream(builder(items))
