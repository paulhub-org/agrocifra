"""Эндпоинты отчётов и визуализации (Спринт 5): сводка, карточка организации, экспорт."""
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, scope_filters
from app.db.session import get_db
from app.services import exporters, reporting

router = APIRouter(prefix="/reports", tags=["Отчёты и визуализация"])


@router.get("/summary", summary="Сводка для дашбордов (в целом, по регионам, по организациям)")
def get_summary(db: Session = Depends(get_db), user=Depends(get_current_user)):
    org_id, region_id, district = scope_filters(user)
    return reporting.summary(db, org_id=org_id, region_id=region_id, district=district)


@router.get("/organization/{org_id}", summary="Карточка организации со сравнением «до/после»")
def get_organization_report(org_id: int, db: Session = Depends(get_db),
                            _user=Depends(get_current_user)):
    return reporting.organization_report(db, org_id)


def _stream(payload: tuple[bytes, str, str]) -> StreamingResponse:
    content, filename, media = payload
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return StreamingResponse(io.BytesIO(content), media_type=media, headers=headers)


@router.get("/export.xlsx", summary="Экспорт отчёта в Excel")
def export_xlsx(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return _stream(exporters.build_excel(db))


@router.get("/export.docx", summary="Экспорт отчёта в Word (приложение к диссертации)")
def export_docx(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return _stream(exporters.build_word(db))


@router.get("/export.pdf", summary="Экспорт отчёта в PDF")
def export_pdf(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return _stream(exporters.build_pdf(db))
