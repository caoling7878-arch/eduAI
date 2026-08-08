from __future__ import annotations

from fastapi import Depends, HTTPException, status

from .auth import get_current_user
from .models import User


def require_roles(*roles: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return user

    return _dep


require_admin = require_roles("admin")
require_staff = require_roles("admin", "teacher")
require_active = require_roles("admin", "teacher", "student")
