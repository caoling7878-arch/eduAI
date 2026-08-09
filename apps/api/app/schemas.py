from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    display_name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    role: str = "student"
    status: str = "active"
    tags: str = ""
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserAdminIn(BaseModel):
    email: EmailStr
    display_name: str
    password: Optional[str] = Field(default=None, min_length=6, max_length=72)
    role: str = Field(default="student", pattern="^(admin|teacher|student)$")
    status: str = Field(default="active", pattern="^(active|disabled)$")
    tags: str = ""


class ProgressUpsertIn(BaseModel):
    course_id: str = Field(min_length=1, max_length=64)
    item_id: str = Field(min_length=1, max_length=128)
    status: str = Field(default="started", pattern="^(started|completed)$")
    score: int = Field(default=0, ge=0, le=100)
    meta: Dict[str, Any] = Field(default_factory=dict)


class ProgressItemOut(BaseModel):
    course_id: str
    item_id: str
    status: str
    score: int
    meta: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


class CourseSummary(BaseModel):
    course_id: str
    total_items: int
    started: int
    completed: int
    percent: int


class ProgressSummaryOut(BaseModel):
    user: UserOut
    courses: List[CourseSummary]
    items: List[ProgressItemOut]


class TeacherOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    email: str
    title: str
    bio: str
    subjects: str


class TeacherIn(BaseModel):
    user_id: int
    title: str = "教师"
    bio: str = ""
    subjects: str = ""


class LessonIn(BaseModel):
    title: str
    content_type: str = "richtext"
    content: str = ""
    sort_order: int = 0


class ChapterIn(BaseModel):
    title: str
    sort_order: int = 0
    lessons: List[LessonIn] = Field(default_factory=list)


class CourseIn(BaseModel):
    title: str
    cover: str = ""
    summary: str = ""
    price_type: str = "public"
    price: float = 0
    status: str = "draft"
    sort_order: int = 0


class LessonOut(BaseModel):
    id: int
    title: str
    content_type: str
    content: str
    sort_order: int

    model_config = {"from_attributes": True}


class ChapterOut(BaseModel):
    id: int
    title: str
    sort_order: int
    lessons: List[LessonOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CourseOut(BaseModel):
    id: int
    title: str
    cover: str
    summary: str
    price_type: str
    price: float
    status: str
    sort_order: int
    student_count: int
    chapters: List[ChapterOut] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClassIn(BaseModel):
    name: str
    teacher_id: Optional[int] = None
    course_id: Optional[int] = None
    member_ids: List[int] = Field(default_factory=list)


class ClassOut(BaseModel):
    id: int
    name: str
    teacher_id: Optional[int]
    course_id: Optional[int]
    member_ids: List[int] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class QuestionIn(BaseModel):
    type: str = "single"
    stem: str
    options: List[str] = Field(default_factory=list)
    answer: str = ""
    analysis: str = ""
    knowledge_points: str = ""
    difficulty: int = 1


class QuestionOut(BaseModel):
    id: int
    type: str
    stem: str
    options: List[str]
    answer: str
    analysis: str
    knowledge_points: str
    difficulty: int
    version: int


class PaperIn(BaseModel):
    title: str
    status: str = "draft"
    question_ids: List[int] = Field(default_factory=list)


class PaperOut(BaseModel):
    id: int
    title: str
    status: str
    question_ids: List[int]
    created_at: Optional[datetime] = None


class SubmitIn(BaseModel):
    paper_id: int
    answers: Dict[str, str] = Field(default_factory=dict)


class SubmissionOut(BaseModel):
    id: int
    paper_id: int
    score: float
    total: float
    answers: Dict[str, str]
    created_at: Optional[datetime] = None


class AnnouncementIn(BaseModel):
    title: str
    body: str = ""
    published: bool = True


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str
    published: bool
    views: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StudyPlanIn(BaseModel):
    title: str


class StudyPlanOut(BaseModel):
    id: int
    title: str
    done: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CheckinOut(BaseModel):
    day: str
    streak: int
    total: int
    checked_today: bool


class AssistantIn(BaseModel):
    name: str
    avatar: str = "助"
    persona: str = ""
    system_prompt: str = ""
    suggested_prompts: List[str] = []
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    knowledge_base_id: Optional[int] = None
    enabled: bool = True


class AssistantOut(BaseModel):
    id: int
    name: str
    avatar: str
    persona: str
    system_prompt: str = ""
    suggested_prompts: List[str] = []
    model: str
    temperature: float
    knowledge_base_id: Optional[int]
    enabled: bool

    model_config = {"from_attributes": True}


class KnowledgeBaseIn(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseOut(BaseModel):
    id: int
    name: str
    description: str
    doc_count: int = 0
    chunk_count: int = 0

    model_config = {"from_attributes": True}


class KnowledgeDocIn(BaseModel):
    title: str
    content: str = ""


class KnowledgeDocOut(BaseModel):
    id: int
    kb_id: int
    title: str
    content: str
    status: str
    source_filename: str = ""
    source_type: str = "text"

    model_config = {"from_attributes": True}


class KbGenerateQuestionsIn(BaseModel):
    count: int = Field(default=5, ge=1, le=20)
    difficulty: int = Field(default=2, ge=1, le=5)
    topic: str = ""
    query: str = ""


class KbGenerateCourseIn(BaseModel):
    title: str = ""
    chapter_count: int = Field(default=3, ge=1, le=8)
    query: str = ""
    create_assistant: bool = True


class PptIn(BaseModel):
    title: str
    outline: str = ""


class PptOut(BaseModel):
    id: int
    title: str
    outline: str
    slides: List[Dict[str, str]]
    status: str
    created_at: Optional[datetime] = None


class PlanOut(BaseModel):
    id: int
    name: str
    price: float
    days: int
    benefits: str

    model_config = {"from_attributes": True}


class OrderIn(BaseModel):
    plan_id: Optional[int] = None
    course_id: Optional[int] = None


class OrderOut(BaseModel):
    id: int
    user_id: int
    plan_id: Optional[int]
    course_id: Optional[int]
    amount: float
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource: str
    detail: str
    ip: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    users: int
    teachers: int
    students: int
    courses: int
    classes: int
    questions: int
    orders: int
    checkins_today: int
    active_members: int = 0
    revenue_total: float = 0
    revenue_today: float = 0
    orders_today: int = 0
    feedback_open: int = 0
    grade_pending: int = 0
    learning_minutes_30d: int = 0
    checkin_trend: List[dict] = []
    user_growth: List[dict] = []
    order_trend: List[dict] = []
    activity_dist: dict = {}
    top_students: List[dict] = []
    top_classes: List[dict] = []
    recent_audits: List[AuditOut]
    # 租户用量摘要（管理员仪表盘）
    tenant_count: int = 0
    quota_alert_count: int = 0
    token_used_total: int = 0
    token_quota_total: int = 0
    request_used_total: int = 0
    request_quota_total: int = 0
    token_pct_max: float = 0
    quota_tenants: List[dict] = []


class SettingsOut(BaseModel):
    items: Dict[str, str]


class SettingsIn(BaseModel):
    items: Dict[str, str]
