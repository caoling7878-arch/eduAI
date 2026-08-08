"""LTI 1.1 兼容简易启动（演示级 LMS 对接）。"""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password
from ..db import get_db
from ..models import Tenant, User
from ..services.billing import seed_billing

router = APIRouter(prefix="/lti", tags=["lti"])


class LtiConfigOut(BaseModel):
    title: str
    description: str
    launch_url: str
    login_hint: str
    supports: list[str]


def _public_base(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        return f"{proto}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/config", response_model=LtiConfigOut)
def tool_config(request: Request) -> LtiConfigOut:
    base = _public_base(request)
    return LtiConfigOut(
        title="eduAI 智慧教育云",
        description="LTI 简易工具：从 LMS 一键进入学员端课堂/练习。",
        launch_url=f"{base}/api/v1/lti/launch",
        login_hint="支持 LTI 1.1 资源链接启动（演示，未校验 OAuth 签名）",
        supports=["resource_link", "deep_linking_stub"],
    )


@router.post("/launch")
async def lti_launch(
    request: Request,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Form(default=None),
    lis_person_contact_email_primary: Optional[str] = Form(default=None),
    lis_person_name_full: Optional[str] = Form(default=None),
    roles: Optional[str] = Form(default=None),
    context_id: Optional[str] = Form(default=None),
    custom_redirect: Optional[str] = Form(default="/classroom"),
) -> RedirectResponse:
    """
    LMS POST 启动。演示环境不验签；生产需补 OAuth1 / LTI 1.3。
    """
    seed_billing(db)
    form = dict(await request.form())
    email = (
        (lis_person_contact_email_primary or form.get("lis_person_contact_email_primary") or "")
        .strip()
        .lower()
    )
    ext_id = (user_id or form.get("user_id") or "").strip()
    name = (lis_person_name_full or form.get("lis_person_name_full") or "").strip() or "LTI 学员"
    role_raw = (roles or form.get("roles") or "").lower()
    redirect_path = (custom_redirect or form.get("custom_redirect") or "/classroom").strip()
    if not redirect_path.startswith("/"):
        redirect_path = "/classroom"

    if not email:
        if ext_id:
            digest = hashlib.md5(ext_id.encode()).hexdigest()[:10]
            email = f"lti_{digest}@lti.local"
        else:
            raise HTTPException(status_code=400, detail="缺少 LTI 用户标识（email / user_id）")

    if "instructor" in role_raw or "teacher" in role_raw or "administrator" in role_raw:
        mapped_role = "teacher"
    else:
        mapped_role = "student"

    user = db.scalar(select(User).where(User.email == email))
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo-school"))
    if not user:
        user = User(
            email=email,
            display_name=name[:120],
            password_hash=hash_password(secrets.token_urlsafe(16)),
            role=mapped_role,
            status="active",
            tags=f"lti,{context_id or ''}"[:255],
            tenant_id=tenant.id if tenant else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if name and user.display_name != name:
            user.display_name = name[:120]
        if tenant and not user.tenant_id:
            user.tenant_id = tenant.id
        if "lti" not in (user.tags or ""):
            user.tags = ((user.tags or "") + ",lti").strip(",")[:255]
        db.commit()

    token = create_access_token(user.id, user.email)
    web_base = (
        form.get("custom_web_base")
        or request.query_params.get("web_base")
        or "http://127.0.0.1:5173"
    ).rstrip("/")
    qs = urlencode({"token": token, "from": "lti", "redirect": redirect_path})
    target = f"{web_base}/auth?{qs}"
    return RedirectResponse(url=target, status_code=302)


@router.get("/demo", response_class=HTMLResponse)
def demo_launch_page(request: Request) -> HTMLResponse:
    """本地演示：模拟 LMS 表单启动。"""
    base = _public_base(request)
    return HTMLResponse(
        f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>LTI Demo Launch</title>
<style>
body{{font-family:system-ui;max-width:560px;margin:40px auto;padding:0 16px}}
label{{display:block;margin:10px 0 4px}}
input,select,button{{width:100%;padding:10px;font-size:14px;box-sizing:border-box}}
button{{background:#0f6b5c;color:#fff;border:0;border-radius:8px;margin-top:16px;cursor:pointer}}
</style></head><body>
<h1>eduAI LTI 演示启动</h1>
<p>模拟 LMS 向 <code>/api/v1/lti/launch</code> 提交资源链接。</p>
<form method="post" action="{base}/api/v1/lti/launch">
  <label>Email</label>
  <input name="lis_person_contact_email_primary" value="lti.student@demo.school"/>
  <label>姓名</label>
  <input name="lis_person_name_full" value="LTI 演示学员"/>
  <label>角色</label>
  <input name="roles" value="Learner"/>
  <label>课程上下文</label>
  <input name="context_title" value="高一数学"/>
  <label>进入页面</label>
  <select name="custom_redirect">
    <option value="/classroom">课堂中心</option>
    <option value="/courses/math-calc">小学数学计算</option>
    <option value="/ai">AI 助手</option>
    <option value="/practice">练习中心</option>
    <option value="/">首页</option>
  </select>
  <input type="hidden" name="context_id" value="math-101"/>
  <input type="hidden" name="user_id" value="lms-user-001"/>
  <input type="hidden" name="resource_link_id" value="res-classroom"/>
  <button type="submit">从 LMS 进入 eduAI</button>
</form>
</body></html>"""
    )
