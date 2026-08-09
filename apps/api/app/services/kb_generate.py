from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AiAssistant,
    Chapter,
    Course,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDoc,
    Lesson,
    Question,
    User,
)
from .llm import (
    chat_completion,
    get_default_provider,
    log_usage,
    resolve_provider_from_env,
)
from .rag import retrieve_docs


def gather_kb_context(
    db: Session,
    kb_id: int,
    *,
    query: str = "",
    max_chars: int = 14000,
) -> Tuple[str, List[dict]]:
    """拼装知识库上下文：优先检索，否则按文档顺序取样。"""
    citations: List[dict] = []
    q = (query or "").strip() or "课程大纲 知识点 重点 概念 定义"
    citations = retrieve_docs(db, kb_id, q, top_k=10)
    blocks: List[str] = []
    used = 0
    for c in citations:
        piece = f"【{c.get('title') or '文档'}】\n{c.get('snippet') or ''}".strip()
        if used + len(piece) > max_chars:
            break
        blocks.append(piece)
        used += len(piece)

    if used < max_chars // 2:
        chunks = list(
            db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.kb_id == kb_id)
                .order_by(KnowledgeChunk.doc_id, KnowledgeChunk.chunk_index)
                .limit(40)
            )
        )
        if not chunks:
            docs = list(db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.kb_id == kb_id)))
            for d in docs:
                piece = f"【{d.title}】\n{(d.content or '')[:2000]}"
                if used + len(piece) > max_chars:
                    break
                blocks.append(piece)
                used += len(piece)
                citations.append(
                    {
                        "doc_id": d.id,
                        "title": d.title,
                        "snippet": (d.content or "")[:360],
                        "score": 0,
                    }
                )
        else:
            seen_docs: set[int] = set()
            for c in chunks:
                if used >= max_chars:
                    break
                piece = (c.content or "").strip()
                if not piece:
                    continue
                title = ""
                if c.doc_id not in seen_docs:
                    doc = db.get(KnowledgeDoc, c.doc_id)
                    title = doc.title if doc else f"文档#{c.doc_id}"
                    seen_docs.add(c.doc_id)
                    citations.append(
                        {
                            "doc_id": c.doc_id,
                            "title": title,
                            "snippet": piece[:360],
                            "score": 0,
                        }
                    )
                block = f"【{title or '续'}】\n{piece}" if title else piece
                if used + len(block) > max_chars:
                    block = block[: max_chars - used]
                blocks.append(block)
                used += len(block)

    return "\n\n".join(blocks).strip(), citations


def _extract_json(raw: str) -> Any:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("模型返回为空")
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m_obj = re.search(r"\{[\s\S]*\}", raw)
    if m_obj:
        return json.loads(m_obj.group(0))
    m_arr = re.search(r"\[[\s\S]*\]", raw)
    if m_arr:
        return json.loads(m_arr.group(0))
    raise ValueError("无法解析模型 JSON")


async def _llm_json(
    db: Session,
    *,
    user: Optional[User],
    purpose: str,
    system: str,
    user_prompt: str,
    max_tokens: int = 2400,
    temperature: float = 0.35,
) -> Tuple[Any, str]:
    """返回 (parsed, source)。source 以 llm 或 local 开头。"""
    provider = get_default_provider(db)
    base = (provider.base_url if provider else None) or ""
    key = (provider.api_key if provider else None) or ""
    model = (provider.default_model if provider else None) or "gpt-4o-mini"
    if not (base and key):
        env_base, env_key, env_model = resolve_provider_from_env()
        base, key, model = env_base or "", env_key or "", env_model
    if not (base and key):
        return None, "local"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]
    t0 = time.time()
    try:
        raw = await chat_completion(
            base_url=base,
            api_key=key,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = int((time.time() - t0) * 1000)
        parsed = _extract_json(raw)
        log_usage(
            db,
            user=user,
            provider_id=provider.id if provider else None,
            model=model,
            purpose=purpose,
            latency_ms=latency,
            success=True,
        )
        return parsed, "llm"
    except Exception as e:
        log_usage(
            db,
            user=user,
            provider_id=provider.id if provider else None,
            model=model,
            purpose=purpose,
            latency_ms=int((time.time() - t0) * 1000),
            success=False,
            error=str(e),
        )
        return None, f"local:{e}"


def _heuristic_questions(context: str, count: int, difficulty: int, topic: str) -> List[dict]:
    lines = [ln.strip() for ln in re.split(r"[\n。！？；]", context) if 12 <= len(ln.strip()) <= 80]
    if not lines:
        lines = [
            "本教材强调理解核心概念并掌握基本方法。",
            "学习时应先明确定义，再结合例题巩固。",
            "复习阶段建议对照知识点做变式练习。",
        ]
    out: List[dict] = []
    topic_tag = topic.strip() or "教材知识点"
    for i in range(count):
        base = lines[i % len(lines)]
        stem_core = base[:48]
        if i % 3 == 0:
            out.append(
                {
                    "type": "single",
                    "stem": f"根据教材内容，「{stem_core}」主要说明了什么？",
                    "options": [
                        "对相关概念与方法的正确理解",
                        "与教材无关的闲谈内容",
                        "仅用于娱乐的扩展阅读",
                        "无需掌握的过时知识",
                    ],
                    "answer": "对相关概念与方法的正确理解",
                    "analysis": f"原文要点：{base}",
                    "knowledge_points": topic_tag,
                    "difficulty": difficulty,
                }
            )
        elif i % 3 == 1:
            out.append(
                {
                    "type": "judge",
                    "stem": f"判断：{stem_core}（依据教材表述）",
                    "options": ["正确", "错误"],
                    "answer": "正确",
                    "analysis": f"教材表述支持该说法：{base}",
                    "knowledge_points": topic_tag,
                    "difficulty": difficulty,
                }
            )
        else:
            key = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,8}", base)
            blank = key[min(1, len(key) - 1)] if key else "概念"
            if blank in base:
                stem = base.replace(blank, "______", 1)
            else:
                stem = f"填空：教材提到的要点是 ______。原文：{stem_core}"
            out.append(
                {
                    "type": "blank",
                    "stem": stem if "______" in stem else f"填空：{stem_core} 中的关键词是 ______。",
                    "options": [],
                    "answer": blank,
                    "analysis": f"原文：{base}",
                    "knowledge_points": topic_tag,
                    "difficulty": difficulty,
                }
            )
    return out


def _heuristic_course(kb_name: str, context: str, chapter_count: int, title: str) -> dict:
    paras = [p.strip() for p in re.split(r"\n{2,}", context) if len(p.strip()) >= 40]
    if not paras:
        paras = [context[i : i + 400] for i in range(0, min(len(context), 2000), 400)] or [
            "暂无正文，请补充教材后重新生成。"
        ]
    chapter_count = max(1, min(chapter_count, 8))
    chapters = []
    for i in range(chapter_count):
        chunk = paras[i % len(paras)]
        mid_title = "核心概念" if i == 0 else ("应用与巩固" if i == chapter_count - 1 else f"要点 {i + 1}")
        chapters.append(
            {
                "title": f"第{i + 1}章　{mid_title}",
                "lessons": [
                    {
                        "title": f"{i + 1}.1 精读导学",
                        "content_type": "richtext",
                        "content": (
                            "<p><strong>学习目标</strong></p>"
                            "<p>理解并掌握本节教材要点。</p>"
                            "<p><strong>教材节选</strong></p>"
                            f"<p>{chunk[:900]}</p>"
                            "<p><strong>练习建议</strong></p>"
                            "<p>完成对应题库练习，并用 AI 学伴提问薄弱点。</p>"
                        ),
                    },
                    {
                        "title": f"{i + 1}.2 小结与自测",
                        "content_type": "richtext",
                        "content": (
                            "<p>回顾本章关键词，尝试用自己的话复述：</p>"
                            f"<p>{chunk[:280]}…</p>"
                        ),
                    },
                ],
            }
        )
    course_title = title.strip() or f"「{kb_name}」AI 课程"
    return {
        "title": course_title,
        "summary": f"基于知识库「{kb_name}」自动生成的课程大纲与课时讲义，可在管理端继续编辑后发布。",
        "chapters": chapters,
    }


def _normalize_question_items(data: Any, count: int, difficulty: int, topic: str) -> List[dict]:
    items = data
    if isinstance(data, dict):
        items = data.get("questions") or data.get("items") or []
    if not isinstance(items, list):
        raise ValueError("题目 JSON 格式不正确")
    out: List[dict] = []
    for raw in items[:count]:
        if not isinstance(raw, dict):
            continue
        qtype = str(raw.get("type") or "single").strip()
        if qtype not in {"single", "multi", "judge", "blank"}:
            qtype = "single"
        options = raw.get("options") or []
        if isinstance(options, str):
            options = [options]
        if not isinstance(options, list):
            options = []
        options = [str(o) for o in options][:8]
        stem = str(raw.get("stem") or "").strip()
        if not stem:
            continue
        ans = str(raw.get("answer") or "").strip()
        if qtype == "judge" and not options:
            options = ["正确", "错误"]
        if qtype == "single" and len(options) < 2:
            options = options + ["以上都不对", "无法判断"]
        out.append(
            {
                "type": qtype,
                "stem": stem,
                "options": options,
                "answer": ans or (options[0] if options else ""),
                "analysis": str(raw.get("analysis") or ""),
                "knowledge_points": str(raw.get("knowledge_points") or topic or "教材知识点"),
                "difficulty": int(raw.get("difficulty") or difficulty),
            }
        )
    return out


def _normalize_course_payload(data: Any, kb_name: str, title: str, chapter_count: int, context: str) -> dict:
    if not isinstance(data, dict):
        return _heuristic_course(kb_name, context, chapter_count, title)
    chapters_in = data.get("chapters") or []
    if not isinstance(chapters_in, list) or not chapters_in:
        return _heuristic_course(kb_name, context, chapter_count, title)
    chapters = []
    for i, ch in enumerate(chapters_in[:8]):
        if not isinstance(ch, dict):
            continue
        lessons_in = ch.get("lessons") or []
        lessons = []
        if isinstance(lessons_in, list):
            for j, les in enumerate(lessons_in[:6]):
                if not isinstance(les, dict):
                    continue
                lessons.append(
                    {
                        "title": str(les.get("title") or f"{i + 1}.{j + 1} 课时").strip(),
                        "content_type": str(les.get("content_type") or "richtext"),
                        "content": str(les.get("content") or "").strip()
                        or f"<p>{str(les.get('summary') or '请结合教材自学本课时。')}</p>",
                    }
                )
        if not lessons:
            lessons = [
                {
                    "title": f"{i + 1}.1 导学",
                    "content_type": "richtext",
                    "content": f"<p>{str(ch.get('summary') or '结合知识库内容完成本章学习。')}</p>",
                }
            ]
        chapters.append(
            {
                "title": str(ch.get("title") or f"第{i + 1}章").strip(),
                "lessons": lessons,
            }
        )
    if not chapters:
        return _heuristic_course(kb_name, context, chapter_count, title)
    return {
        "title": str(data.get("title") or title or f"「{kb_name}」AI 课程").strip(),
        "summary": str(data.get("summary") or f"基于知识库「{kb_name}」生成").strip(),
        "chapters": chapters,
    }


async def generate_questions_from_kb(
    db: Session,
    *,
    kb_id: int,
    user: User,
    count: int = 5,
    difficulty: int = 2,
    topic: str = "",
    query: str = "",
) -> Dict[str, Any]:
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise ValueError("知识库不存在")
    count = max(1, min(int(count), 20))
    difficulty = max(1, min(int(difficulty), 5))
    context, citations = gather_kb_context(db, kb_id, query=query or topic)
    if not context:
        raise ValueError("知识库尚无可用内容，请先上传教材文档")

    prompt = (
        f"请根据下列教材摘录，生成 {count} 道练习题。"
        f"题型可混合 single/multi/judge/blank；难度约 {difficulty}/5；"
        f"主题侧重：{topic or '教材重点'}。\n"
        "严格输出 JSON：{\"questions\":[{\"type\":\"single\",\"stem\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],"
        "\"answer\":\"...\",\"analysis\":\"...\",\"knowledge_points\":\"...\",\"difficulty\":2}]}\n\n"
        f"教材摘录：\n{context[:12000]}"
    )
    parsed, source = await _llm_json(
        db,
        user=user,
        purpose="kb_gen_questions",
        system="你是教研出题助手。只输出合法 JSON，不要 Markdown 说明。",
        user_prompt=prompt,
        max_tokens=2800,
    )
    items: List[dict] = []
    if parsed is not None:
        try:
            items = _normalize_question_items(parsed, count, difficulty, topic)
        except Exception:
            items = []
    if len(items) < count:
        items = _heuristic_questions(context, count, difficulty, topic or kb.name)
        if not source.startswith("local"):
            source = "local:fallback"

    created = []
    for it in items:
        row = Question(
            type=it["type"],
            stem=it["stem"],
            options_json=json.dumps(it["options"], ensure_ascii=False),
            answer=it["answer"],
            analysis=it["analysis"],
            knowledge_points=it["knowledge_points"],
            difficulty=it["difficulty"],
        )
        db.add(row)
        db.flush()
        created.append(
            {
                "id": row.id,
                "type": row.type,
                "stem": row.stem,
                "options": it["options"],
                "answer": row.answer,
                "analysis": row.analysis,
                "knowledge_points": row.knowledge_points,
                "difficulty": row.difficulty,
            }
        )
    db.commit()
    return {
        "source": source if source.startswith("llm") else "local",
        "count": len(created),
        "questions": created,
        "citations": citations[:5],
        "kb_id": kb_id,
        "kb_name": kb.name,
    }


async def generate_course_from_kb(
    db: Session,
    *,
    kb_id: int,
    user: User,
    title: str = "",
    chapter_count: int = 3,
    query: str = "",
    create_assistant: bool = True,
) -> Dict[str, Any]:
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise ValueError("知识库不存在")
    chapter_count = max(1, min(int(chapter_count), 8))
    context, citations = gather_kb_context(db, kb_id, query=query or title)
    if not context:
        raise ValueError("知识库尚无可用内容，请先上传教材文档")

    prompt = (
        f"请根据教材摘录设计一门在线课程，约 {chapter_count} 章，每章 2 个课时。"
        f"课程建议标题：{title or kb.name}。\n"
        "课时 content 用简洁 HTML（p/strong/ul/li）。严格输出 JSON：\n"
        "{\"title\":\"...\",\"summary\":\"...\","
        "\"chapters\":[{\"title\":\"...\",\"lessons\":[{\"title\":\"...\",\"content_type\":\"richtext\",\"content\":\"<p>...</p>\"}]}]}\n\n"
        f"教材摘录：\n{context[:12000]}"
    )
    parsed, source = await _llm_json(
        db,
        user=user,
        purpose="kb_gen_course",
        system="你是课程设计师。只输出合法 JSON，不要 Markdown 说明。",
        user_prompt=prompt,
        max_tokens=3200,
    )
    payload = _normalize_course_payload(parsed, kb.name, title, chapter_count, context)
    if parsed is None or not source.startswith("llm"):
        source = "local"

    course = Course(
        title=payload["title"],
        summary=payload["summary"],
        cover="",
        price_type="public",
        price=0,
        status="draft",
        sort_order=0,
    )
    db.add(course)
    db.flush()
    for ci, ch in enumerate(payload["chapters"]):
        chapter = Chapter(course_id=course.id, title=ch["title"], sort_order=ci)
        db.add(chapter)
        db.flush()
        for li, les in enumerate(ch["lessons"]):
            db.add(
                Lesson(
                    chapter_id=chapter.id,
                    title=les["title"],
                    content_type=les.get("content_type") or "richtext",
                    content=les.get("content") or "",
                    sort_order=li,
                )
            )

    assistant_out = None
    if create_assistant:
        existing = db.scalar(
            select(AiAssistant).where(
                AiAssistant.knowledge_base_id == kb_id,
                AiAssistant.name == f"{kb.name} 助教",
            )
        )
        if existing:
            assistant_out = {
                "id": existing.id,
                "name": existing.name,
                "knowledge_base_id": existing.knowledge_base_id,
                "created": False,
            }
        else:
            a = AiAssistant(
                name=f"{kb.name} 助教",
                avatar="",
                persona=f"你是「{kb.name}」课程助教，回答须依据绑定知识库，引用教材要点，讲解清晰并鼓励学员练习。",
                system_prompt=(
                    f"你服务于课程《{course.title}》。优先依据知识库内容作答；"
                    "不确定时说明并引导学生回到教材相关章节。"
                ),
                model="",
                temperature=0.5,
                knowledge_base_id=kb_id,
                enabled=True,
                suggested_prompts=json.dumps(
                    ["本章重点是什么？", "给我一道练习题并讲解", "用更简单的例子说明刚才的概念"],
                    ensure_ascii=False,
                ),
            )
            db.add(a)
            db.flush()
            assistant_out = {
                "id": a.id,
                "name": a.name,
                "knowledge_base_id": a.knowledge_base_id,
                "created": True,
            }

    db.commit()
    return {
        "source": source if source.startswith("llm") else "local",
        "course_id": course.id,
        "title": course.title,
        "summary": course.summary,
        "status": course.status,
        "chapter_count": len(payload["chapters"]),
        "assistant": assistant_out,
        "citations": citations[:5],
        "kb_id": kb_id,
        "kb_name": kb.name,
    }
