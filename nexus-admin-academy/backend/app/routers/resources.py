from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resource import Resource

router = APIRouter(prefix="/api/resources", tags=["resources"])


def _ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None):
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload


@router.get("")
def get_resources(week: int | None = None, category: str | None = None, type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Resource)
    if week is not None:
        query = query.filter(Resource.week_number == week)
    if category:
        query = query.filter(Resource.category == category)
    if type:
        query = query.filter(Resource.resource_type == type)

    rows = query.order_by(Resource.created_at.desc()).all()
    data = [
        {
            "id": row.id,
            "title": row.title,
            "url": row.url,
            "resource_type": row.resource_type,
            "week_number": row.week_number,
            "category": row.category,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)
