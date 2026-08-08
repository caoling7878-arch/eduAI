from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import SiteSetting, User
from ..rbac import require_admin
from ..schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)) -> SettingsOut:
    rows = list(db.scalars(select(SiteSetting)))
    return SettingsOut(items={r.key: r.value for r in rows})


@router.put("", response_model=SettingsOut)
def put_settings(
    body: SettingsIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SettingsOut:
    for k, v in body.items.items():
        row = db.scalar(select(SiteSetting).where(SiteSetting.key == k))
        if row:
            row.value = v
        else:
            db.add(SiteSetting(key=k, value=v))
    write_audit(db, user=admin, action="settings.update", resource="site")
    db.commit()
    return get_settings(db)
