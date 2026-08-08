from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from .models import AuditLog, User


def write_audit(
    db: Session,
    *,
    user: Optional[User],
    action: str,
    resource: str = "",
    detail: str = "",
    ip: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            resource=resource,
            detail=detail,
            ip=ip,
        )
    )
