from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit_util import write_audit
from ..db import get_db
from ..models import Chapter, Course, Lesson, User
from ..rbac import require_admin, require_staff
from ..schemas import ChapterIn, CourseIn, CourseOut, LessonIn

router = APIRouter(prefix="/courses", tags=["courses"])


def _load(db: Session, course_id: int):
    return db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.chapters).selectinload(Chapter.lessons))
    )


@router.get("", response_model=list[CourseOut])
def list_courses(
    published_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[Course]:
    stmt = (
        select(Course)
        .options(selectinload(Course.chapters).selectinload(Chapter.lessons))
        .order_by(Course.sort_order, Course.id.desc())
    )
    if published_only:
        stmt = stmt.where(Course.status == "published")
    return list(db.scalars(stmt))


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)) -> Course:
    c = _load(db, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="课程不存在")
    return c


@router.post("", response_model=CourseOut)
def create_course(
    body: CourseIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Course:
    c = Course(**body.model_dump())
    db.add(c)
    write_audit(db, user=admin, action="course.create", resource=body.title)
    db.commit()
    db.refresh(c)
    return _load(db, c.id)  # type: ignore[return-value]


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    body: CourseIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Course:
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="课程不存在")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    write_audit(db, user=admin, action="course.update", resource=str(course_id))
    db.commit()
    return _load(db, course_id)  # type: ignore[return-value]


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="课程不存在")
    db.delete(c)
    write_audit(db, user=admin, action="course.delete", resource=str(course_id))
    db.commit()
    return {"status": "ok"}


@router.post("/{course_id}/chapters", response_model=CourseOut)
def add_chapter(
    course_id: int,
    body: ChapterIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Course:
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="课程不存在")
    ch = Chapter(course_id=course_id, title=body.title, sort_order=body.sort_order)
    db.add(ch)
    db.flush()
    for i, les in enumerate(body.lessons):
        db.add(
            Lesson(
                chapter_id=ch.id,
                title=les.title,
                content_type=les.content_type,
                content=les.content,
                sort_order=les.sort_order or i,
            )
        )
    write_audit(db, user=admin, action="chapter.create", resource=str(course_id))
    db.commit()
    return _load(db, course_id)  # type: ignore[return-value]


@router.post("/chapters/{chapter_id}/lessons", response_model=CourseOut)
def add_lesson(
    chapter_id: int,
    body: LessonIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Course:
    ch = db.get(Chapter, chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail="章节不存在")
    db.add(
        Lesson(
            chapter_id=chapter_id,
            title=body.title,
            content_type=body.content_type,
            content=body.content,
            sort_order=body.sort_order,
        )
    )
    write_audit(db, user=admin, action="lesson.create", resource=str(chapter_id))
    db.commit()
    return _load(db, ch.course_id)  # type: ignore[return-value]
