from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user, hash_password
from ..db import get_db
from ..models import ClassMember, ClassRoom, User
from ..rbac import require_admin, require_staff
from ..schemas import UserAdminIn, UserOut
from ..services.teacher_scope import teacher_student_ids

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/options", response_model=list[UserOut])
def list_user_options(
    role: str = Query(default=""),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> list[User]:
    """教师/管理员可读的轻量用户列表（用于班级花名册等）。

    教师请求学员列表时，仅返回自己班级内的学生。
    """
    stmt = select(User).where(User.status == "active").order_by(User.id.desc())
    if role:
        stmt = stmt.where(User.role == role)

    if user.role == "teacher" and (not role or role == "student"):
        allowed = teacher_student_ids(db, user) or []
        if role == "student" or not role:
            if not allowed:
                return []
            stmt = stmt.where(User.id.in_(allowed), User.role == "student")
    elif user.role == "teacher" and role == "teacher":
        # 教师改班级时通常不需要选其他教师；仅返回自己
        stmt = stmt.where(User.id == user.id)

    return list(db.scalars(stmt.limit(500)))


@router.get("", response_model=list[UserOut])
def list_users(
    q: str = Query(default=""),
    role: str = Query(default=""),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User).order_by(User.id.desc())
    if role:
        stmt = stmt.where(User.role == role)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.display_name.ilike(like)))
    return list(db.scalars(stmt))


@router.post("", response_model=UserOut)
def create_user(
    body: UserAdminIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    email = body.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")
    if not body.password:
        raise HTTPException(status_code=400, detail="请设置初始密码")
    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        status=body.status,
        tags=body.tags,
    )
    db.add(user)
    write_audit(db, user=admin, action="user.create", resource=email)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserAdminIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.email = body.email.lower().strip()
    user.display_name = body.display_name.strip()
    user.role = body.role
    user.status = body.status
    user.tags = body.tags
    if body.password:
        user.password_hash = hash_password(body.password)
    write_audit(db, user=admin, action="user.update", resource=str(user_id))
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    db.delete(user)
    write_audit(db, user=admin, action="user.delete", resource=str(user_id))
    db.commit()
    return {"status": "ok"}


@router.get("/me/profile", response_model=UserOut)
def my_profile(user: User = Depends(get_current_user)) -> User:
    return user
