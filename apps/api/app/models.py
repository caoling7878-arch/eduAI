from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="student", index=True)  # admin|teacher|student
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|disabled
    tags: Mapped[str] = mapped_column(String(255), default="")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    progress_items: Mapped[list["ProgressItem"]] = relationship(back_populates="user")


class ProgressItem(Base):
    __tablename__ = "progress_items"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "item_id", name="uq_user_course_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="started")
    score: Mapped[int] = mapped_column(Integer, default=0)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="progress_items")


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(String(120), default="教师")
    bio: Mapped[str] = mapped_column(Text, default="")
    subjects: Mapped[str] = mapped_column(String(255), default="")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    cover: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    price_type: Mapped[str] = mapped_column(String(32), default="public")  # public|member|paid
    price: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|published
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    student_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped[Course] = relationship(back_populates="chapters")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(32), default="richtext")  # richtext|video|interactive_lab
    content: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    chapter: Mapped[Chapter] = relationship(back_populates="lessons")


class ClassRoom(Base):
    __tablename__ = "class_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassMember(Base):
    __tablename__ = "class_members"
    __table_args__ = (UniqueConstraint("class_id", "user_id", name="uq_class_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class_rooms.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), default="single")  # single|multi|judge|blank
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text, default="[]")
    answer: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    knowledge_points: Mapped[str] = mapped_column(String(255), default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    question_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    score: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_checkin_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[str] = mapped_column(String(16))  # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiAssistant(Base):
    __tablename__ = "ai_assistants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    avatar: Mapped[str] = mapped_column(String(8), default="助")
    persona: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    suggested_prompts: Mapped[str] = mapped_column(Text, default="[]")  # JSON string[]
    model: Mapped[str] = mapped_column(String(120), default="gpt-4o-mini")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    knowledge_base_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kb_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="ready")
    source_filename: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(32), default="text")  # text|pdf|md|txt|docx


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[float] = mapped_column(Float, default=0)
    days: Mapped[int] = mapped_column(Integer, default=30)
    benefits: Mapped[str] = mapped_column(Text, default="")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("membership_plans.id"), nullable=True)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="paid")  # pending|paid|refunded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SiteSetting(Base):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")


class PptJob(Base):
    __tablename__ = "ppt_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    outline: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="done")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LlmProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[str] = mapped_column(String(500), default="https://api.openai.com/v1")
    api_key: Mapped[str] = mapped_column(Text, default="")
    default_model: Mapped[str] = mapped_column(String(120), default="gpt-4o-mini")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), index=True)  # chat_system / rag_wrap / ...
    name: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assistant_id: Mapped[int] = mapped_column(ForeignKey("ai_assistants.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32))  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, default="")
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LlmUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    provider_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model: Mapped[str] = mapped_column(String(120), default="")
    purpose: Mapped[str] = mapped_column(String(64), default="chat")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GradeTask(Base):
    """主观题批改任务：AI 初评 → 教师复核。"""

    __tablename__ = "grade_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    submission_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    answer_text: Mapped[str] = mapped_column(Text, default="")
    max_score: Mapped[float] = mapped_column(Float, default=10)
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float] = mapped_column(Float, default=0)
    teacher_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    teacher_feedback: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | ai_scored | teacher_reviewed
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 抽样质检：none | sampled | passed | failed
    qc_status: Mapped[str] = mapped_column(String(32), default="none", index=True)
    qc_note: Mapped[str] = mapped_column(Text, default="")
    qc_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    qc_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class WrongItem(Base):
    __tablename__ = "wrong_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    submission_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_answer: Mapped[str] = mapped_column(Text, default="")
    correct_answer: Mapped[str] = mapped_column(Text, default="")
    knowledge_points: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(32), default="objective")  # objective|subjective
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(255), default="")
    kind: Mapped[str] = mapped_column(String(32), default="system")  # system|grade|announce|study
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Ebook(Base):
    __tablename__ = "ebooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    cover: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|published
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EbookChapter(Base):
    __tablename__ = "ebook_chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ebook_id: Mapped[int] = mapped_column(ForeignKey("ebooks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class LabPage(Base):
    """几何动图课页目录（可挂到课时）。"""

    __tablename__ = "lab_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(64), default="solid")  # solid|analytic
    description: Mapped[str] = mapped_column(Text, default="")
    preview_path: Mapped[str] = mapped_column(String(255), default="")
    knowledge_points: Mapped[str] = mapped_column(String(255), default="")
    # 显式挂接题库 ID，逗号分隔；空则回退知识点匹配
    question_ids: Mapped[str] = mapped_column(String(500), default="")


class LabPageQuestion(Base):
    """课页 ↔ 题目双向关联（可查询反查）。"""

    __tablename__ = "lab_page_questions"
    __table_args__ = (UniqueConstraint("page_key", "question_id", name="uq_lab_page_question"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_key: Mapped[str] = mapped_column(String(64), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kb_id: Mapped[int] = mapped_column(Integer, index=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("knowledge_docs.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, default="")
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")  # sparse/dense vector JSON
    token_count: Mapped[int] = mapped_column(Integer, default=0)


class VocabWord(Base):
    __tablename__ = "vocab_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(120), index=True)
    phonetic: Mapped[str] = mapped_column(String(120), default="")
    meaning: Mapped[str] = mapped_column(Text, default="")
    example: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(32), default="A2")
    day_tag: Mapped[str] = mapped_column(String(16), default="")  # YYYY-MM-DD or empty=pool
    # 词根词缀 JSON：{segments, story, image_key}
    morphology_json: Mapped[str] = mapped_column(Text, default="")
    # 意思配图键，前端用 SVG 场景渲染
    image_key: Mapped[str] = mapped_column(String(64), default="")
    # 词库分类：zhongkao_800|cet4|cet6|ielts|toefl|demo
    bank: Mapped[str] = mapped_column(String(32), default="zhongkao_800", index=True)
    # 词库内课程顺序（导入 JSON 下标），用于按考试词库顺序出题
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    pos: Mapped[str] = mapped_column(String(64), default="")
    scene: Mapped[str] = mapped_column(String(120), default="")
    frequency: Mapped[str] = mapped_column(String(120), default="")
    # [{"pos":"n.","text":"学校"}, ...]
    meanings_json: Mapped[str] = mapped_column(Text, default="[]")


class VocabProgress(Base):
    __tablename__ = "vocab_progress"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_vocab_user_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("vocab_words.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="learning")  # learning|known|hard
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    # 艾宾浩斯
    ease_step: Mapped[int] = mapped_column(Integer, default=0)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    next_review_date: Mapped[str] = mapped_column(String(16), default="")  # YYYY-MM-DD
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    last_result: Mapped[str] = mapped_column(String(16), default="")  # ok|wrong
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VocabDailyLog(Base):
    """每日背单词完成记录（打卡 / 星级）。"""

    __tablename__ = "vocab_daily_logs"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_vocab_daily_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM-DD
    bank: Mapped[str] = mapped_column(String(32), default="zhongkao_800")
    # 生成词单时的每日新词数量快照；变更设置后需重建
    daily_count: Mapped[int] = mapped_column(Integer, default=0)
    # 当日固定词单 [{"id":1,"role":"new|review|wrong"}, ...]，学习/测验共用，避免写进度后换词
    pack_json: Mapped[str] = mapped_column(Text, default="")
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    quiz_total: Mapped[int] = mapped_column(Integer, default=0)
    quiz_correct: Mapped[int] = mapped_column(Integer, default=0)
    # 最近一次测验结果（含错题解析），刷新页面仍可展示
    quiz_json: Mapped[str] = mapped_column(Text, default="")
    stars_earned: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VocabReward(Base):
    """背单词积分账户。"""

    __tablename__ = "vocab_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    stars_total: Mapped[int] = mapped_column(Integer, default=0)
    stars_month: Mapped[int] = mapped_column(Integer, default=0)
    month_key: Mapped[str] = mapped_column(String(8), default="")  # YYYY-MM
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_checkin_date: Mapped[str] = mapped_column(String(16), default="")
    redeemed_months: Mapped[int] = mapped_column(Integer, default=0)


class DailyArticle(Base):
    __tablename__ = "daily_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    lang: Mapped[str] = mapped_column(String(16), default="zh")
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    day_tag: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaperTemplate(Base):
    __tablename__ = "paper_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    question_types: Mapped[str] = mapped_column(String(255), default="single,judge,essay")
    default_count: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PptTemplate(Base):
    __tablename__ = "ppt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    theme: Mapped[str] = mapped_column(String(64), default="teal")
    outline_hint: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeedbackTicket(Base):
    __tablename__ = "feedback_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), default="general")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="open")  # open|processing|done
    reply: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    token_prefix: Mapped[str] = mapped_column(String(16), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    scopes: Mapped[str] = mapped_column(String(255), default="courses:read,announcements:read")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetSample(Base):
    """样本回流：错题 / AI 与教师评分差异。"""

    __tablename__ = "dataset_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), default="wrong")  # wrong|grade_diff
    question_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    knowledge_points: Mapped[str] = mapped_column(String(255), default="")
    exported: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FineTuneJob(Base):
    """外部微调任务（对接 OpenAI 兼容 / 自有训练服务的任务桩）。"""

    __tablename__ = "finetune_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(
        String(32), default="queued", index=True
    )  # queued|submitted|running|succeeded|failed|cancelled
    provider: Mapped[str] = mapped_column(String(64), default="openai_compatible")
    base_model: Mapped[str] = mapped_column(String(120), default="gpt-4o-mini")
    sample_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    training_preview: Mapped[str] = mapped_column(Text, default="")  # JSONL 预览前几行
    external_job_id: Mapped[str] = mapped_column(String(120), default="")
    webhook_status: Mapped[str] = mapped_column(String(32), default="")  # ""|sent|skipped|error
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EbookProgress(Base):
    __tablename__ = "ebook_progress"
    __table_args__ = (UniqueConstraint("user_id", "ebook_id", name="uq_ebook_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ebook_id: Mapped[int] = mapped_column(ForeignKey("ebooks.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    percent: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MathCalcItem(Base):
    """小学数学计算专项题库。"""

    __tablename__ = "math_calc_items"
    __table_args__ = (UniqueConstraint("grade", "stem", name="uq_math_calc_grade_stem"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grade: Mapped[int] = mapped_column(Integer, index=True)
    topic: Mapped[str] = mapped_column(String(120), default="")
    stem: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(String(64), default="")
    answer_kind: Mapped[str] = mapped_column(String(32), default="number")  # number|compare|fraction
    source: Mapped[str] = mapped_column(String(16), default="gen")  # gen|pdf
    # 同步到全局错题本时关联的 questions.id
    question_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)


class MathCalcDaily(Base):
    """每日一页计算练习。"""

    __tablename__ = "math_calc_dailies"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_math_calc_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM-DD
    grade: Mapped[int] = mapped_column(Integer, default=1)
    topic: Mapped[str] = mapped_column(String(120), default="")
    item_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    results_json: Mapped[str] = mapped_column(Text, default="{}")
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkflowRule(Base):
    """固定流水线规则：事件 → 动作。"""

    __tablename__ = "workflow_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # grade.ai_done | grade.reviewed | feedback.created | check.pending_grades
    event: Mapped[str] = mapped_column(String(64), index=True)
    # notify_staff | notify_user | noop
    action: Mapped[str] = mapped_column(String(64), default="notify_staff")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkflowRun(Base):
    """规则执行日志。"""

    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="ok")  # ok|skipped|error
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tenant(Base):
    """租户（学校/机构）。"""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|suspended
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsagePack(Base):
    """AI 用量包。"""

    __tablename__ = "usage_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[float] = mapped_column(Float, default=0)
    days: Mapped[int] = mapped_column(Integer, default=30)
    token_quota: Mapped[int] = mapped_column(Integer, default=200000)
    request_quota: Mapped[int] = mapped_column(Integer, default=2000)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class TenantSubscription(Base):
    """租户当前订阅与用量。"""

    __tablename__ = "tenant_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("usage_packs.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|expired|cancelled
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    requests_used: Mapped[int] = mapped_column(Integer, default=0)
    token_quota: Mapped[int] = mapped_column(Integer, default=0)
    request_quota: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[str] = mapped_column(String(16), default="")  # YYYY-MM-DD
    ends_at: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
