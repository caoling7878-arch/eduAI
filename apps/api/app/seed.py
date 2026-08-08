from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    AiAssistant,
    Announcement,
    Chapter,
    ClassMember,
    ClassRoom,
    Course,
    DailyArticle,
    Ebook,
    EbookChapter,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDoc,
    LabPage,
    LabPageQuestion,
    Lesson,
    LlmProvider,
    MembershipPlan,
    Notification,
    Paper,
    PaperTemplate,
    PptTemplate,
    PromptTemplate,
    Question,
    SiteSetting,
    TeacherProfile,
    User,
    VocabWord,
)
from .services.llm import resolve_provider_from_env
from .services.rag import reindex_kb
from .services.word_morphology import morph_for, morph_json_dumps


def seed_if_empty(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        return

    admin = User(
        email="admin@edu.ai",
        display_name="系统管理员",
        password_hash=hash_password("admin123"),
        role="admin",
        status="active",
        tags="平台",
    )
    teacher_user = User(
        email="teacher@edu.ai",
        display_name="林老师",
        password_hash=hash_password("teacher123"),
        role="teacher",
        status="active",
        tags="数学",
    )
    student = User(
        email="student@edu.ai",
        display_name="小明",
        password_hash=hash_password("student123"),
        role="student",
        status="active",
        tags="高一",
    )
    db.add_all([admin, teacher_user, student])
    db.flush()

    db.add(
        TeacherProfile(
            user_id=teacher_user.id,
            title="高级数学教师",
            bio="专注立体几何与解析几何可视化教学。",
            subjects="数学,立体几何",
        )
    )

    course = Course(
        title="立体几何可视化入门",
        cover="/covers/geometry.svg",
        summary="通过可交互三维模型理解空间关系。",
        price_type="public",
        price=0,
        status="published",
        sort_order=1,
        student_count=128,
    )
    db.add(course)
    db.flush()
    ch = Chapter(course_id=course.id, title="第一章 空间几何体", sort_order=1)
    db.add(ch)
    db.flush()
    db.add_all(
        [
            Lesson(
                chapter_id=ch.id,
                title="正方体认识",
                content_type="interactive_lab",
                content="cube",
                sort_order=1,
            ),
            Lesson(
                chapter_id=ch.id,
                title="线面角演示",
                content_type="interactive_lab",
                content="line-plane-angle",
                sort_order=2,
            ),
        ]
    )

    eng = Course(
        title="英语口语情景教练",
        cover="/covers/english.svg",
        summary="情景对话 + 语音评测。",
        price_type="member",
        price=99,
        status="published",
        sort_order=2,
        student_count=86,
    )
    coding = Course(
        title="青少年 AI 编程启蒙",
        cover="/covers/coding.svg",
        summary="浏览器内写代码，理解 AI 基础概念。",
        price_type="paid",
        price=199,
        status="published",
        sort_order=3,
        student_count=64,
    )
    db.add_all([eng, coding])
    db.flush()

    classroom = ClassRoom(name="高一数学实验班", teacher_id=teacher_user.id, course_id=course.id)
    db.add(classroom)
    db.flush()
    db.add(ClassMember(class_id=classroom.id, user_id=student.id))

    qs = [
        Question(
            type="single",
            stem="正方体有几条棱？",
            options_json=json.dumps(["6", "8", "12", "24"], ensure_ascii=False),
            answer="2",
            analysis="正方体有 12 条棱。",
            knowledge_points="立体几何",
            difficulty=1,
        ),
        Question(
            type="judge",
            stem="线面垂直时，线与面内任意直线垂直。",
            options_json=json.dumps(["正确", "错误"], ensure_ascii=False),
            answer="0",
            analysis="线面垂直判定定理。",
            knowledge_points="线面关系",
            difficulty=2,
        ),
        Question(
            type="blank",
            stem="椭圆标准方程中 a、b 分别表示____、____。",
            options_json="[]",
            answer="长半轴,短半轴",
            analysis="椭圆几何意义。",
            knowledge_points="解析几何",
            difficulty=2,
        ),
    ]
    db.add_all(qs)
    db.flush()
    db.add(
        Paper(
            title="立体几何小测",
            status="published",
            question_ids=json.dumps([q.id for q in qs[:2]]),
        )
    )

    db.add(
        Announcement(
            title="欢迎使用 eduAI 智慧教育云平台",
            body="本平台提供几何实验室、英语口语教练、AI 编程与多智能体互动课堂。",
            published=True,
        )
    )
    db.add(
        Announcement(
            title="本周打卡挑战开启",
            body="连续打卡 7 天可解锁学习徽章（演示）。",
            published=True,
        )
    )

    kb = KnowledgeBase(name="高中数学知识库", description="立体几何与解析几何要点")
    db.add(kb)
    db.flush()
    db.add(
        KnowledgeDoc(
            kb_id=kb.id,
            title="线面角定义",
            content="平面的一条斜线和它在平面上的射影所成的角，叫做这条线和这个平面所成的角。",
            status="ready",
        )
    )
    db.add(
        AiAssistant(
            name="几何助教",
            avatar="几",
            persona="你是耐心的高中数学助教，擅长用直观例子讲解立体几何。",
            system_prompt=(
                "你是高中数学几何助教。用简洁中文分步讲解，优先直观例子与建系/向量思路。"
                "若有知识库资料请优先引用，末尾用「参考：[n]」标注。"
            ),
            suggested_prompts=json.dumps(
                ["线面角怎么定义？", "正方体中如何求直线与平面所成角？", "帮我出一道立体几何练习题"],
                ensure_ascii=False,
            ),
            model="gpt-4o-mini",
            temperature=0.5,
            knowledge_base_id=kb.id,
            enabled=True,
        )
    )
    db.add(
        AiAssistant(
            name="口语陪练",
            avatar="英",
            persona="你是友善的英语口语教练，纠正表达并鼓励学员。",
            system_prompt=(
                "You are a friendly English speaking coach. Reply mostly in English with brief Chinese tips when helpful. "
                "Correct grammar gently and suggest natural alternatives."
            ),
            suggested_prompts=json.dumps(
                [
                    "Help me introduce myself at school",
                    "Correct this sentence: I go to school by foots",
                    "Practice ordering coffee at a cafe",
                ],
                ensure_ascii=False,
            ),
            model="gpt-4o-mini",
            temperature=0.7,
            enabled=True,
        )
    )

    db.add_all(
        [
            MembershipPlan(name="月度会员", price=39, days=30, benefits="全部会员课 + AI 助教"),
            MembershipPlan(name="年度会员", price=299, days=365, benefits="全部会员课 + 优先支持"),
        ]
    )

    for k, v in {
        "site_name": "eduAI 智慧教育云平台",
        "site_tagline": "把任何主题或文档变成一场沉浸式课堂",
        "support_email": "support@edu.ai",
        "member_enabled": "true",
    }.items():
        db.add(SiteSetting(key=k, value=v))

    db.commit()
    seed_ai_defaults(db)
    seed_p1_defaults(db)


def seed_ai_defaults(db: Session) -> None:
    """幂等：补齐 P1 AI Provider / Prompt（已有用户的库也可升级）。"""
    existing_keys = set(db.scalars(select(PromptTemplate.key)).all())
    defaults = [
        (
            "chat_system",
            "学伴系统提示词",
            (
                "你是 eduAI 平台的学习助手。请用简洁、鼓励的中文回答学生问题，"
                "必要时给出步骤拆解。若提供了参考资料，请优先依据资料作答，"
                "并在末尾用「参考：[n]」标注引用。"
            ),
        ),
        (
            "rag_wrap",
            "知识库上下文包装",
            "以下是可参考的知识库片段：\n\n{context}\n\n请结合用户问题作答；若资料不足，请诚实说明并给出学习建议。",
        ),
        (
            "grade_rubric",
            "主观题评分提示词",
            (
                "你是严谨的学科阅卷老师。根据题干、参考答案/评分标准与学生作答，给出 JSON："
                '{"score": number, "confidence": 0到1小数, "feedback": "中文评语"}。'
                "只输出 JSON，不要其他文字。score 不得超过满分。"
            ),
        ),
    ]
    for key, name, content in defaults:
        if key not in existing_keys:
            db.add(PromptTemplate(key=key, name=name, content=content, version=1, active=True))

    if db.scalar(select(func.count()).select_from(LlmProvider)) == 0:
        base, key, model = resolve_provider_from_env()
        db.add(
            LlmProvider(
                name="默认 OpenAI 兼容",
                base_url=base or "https://api.openai.com/v1",
                api_key=key or "",
                default_model=model or "gpt-4o-mini",
                enabled=True,
                is_default=True,
            )
        )

    # 幂等补齐助手 system_prompt / suggested_prompts
    presets = {
        "几何助教": {
            "system_prompt": (
                "你是高中数学几何助教。用简洁中文分步讲解，优先直观例子与建系/向量思路。"
                "若有知识库资料请优先引用，末尾用「参考：[n]」标注。"
            ),
            "suggested_prompts": [
                "线面角怎么定义？",
                "正方体中如何求直线与平面所成角？",
                "帮我出一道立体几何练习题",
            ],
        },
        "口语陪练": {
            "system_prompt": (
                "You are a friendly English speaking coach. Reply mostly in English with brief Chinese tips when helpful. "
                "Correct grammar gently and suggest natural alternatives."
            ),
            "suggested_prompts": [
                "Help me introduce myself at school",
                "Correct this sentence: I go to school by foots",
                "Practice ordering coffee at a cafe",
            ],
        },
    }
    for a in db.scalars(select(AiAssistant)):
        preset = presets.get(a.name)
        if not preset:
            continue
        if not (getattr(a, "system_prompt", None) or "").strip():
            a.system_prompt = preset["system_prompt"]
        raw = getattr(a, "suggested_prompts", None) or ""
        empty = (not raw) or raw.strip() in ("", "[]")
        if empty:
            a.suggested_prompts = json.dumps(preset["suggested_prompts"], ensure_ascii=False)

    db.commit()


def seed_p1_defaults(db: Session) -> None:
    """幂等：主观题样例、电子书、几何课页目录、欢迎消息。"""
    essay = db.scalar(select(Question).where(Question.type == "essay"))
    if not essay:
        essay = Question(
            type="essay",
            stem="请用自己的话解释什么是线面角，并举一个生活中的例子。",
            options_json="[]",
            answer="线面角是平面的斜线与它在平面上射影所成的角；例如旗杆与地面影子的夹角。",
            analysis="要点：定义准确 4 分；射影概念 3 分；举例恰当 3 分。",
            knowledge_points="线面关系",
            difficulty=3,
        )
        db.add(essay)
        db.flush()
        paper = db.scalar(select(Paper).where(Paper.title == "立体几何小测"))
        if paper:
            try:
                ids = json.loads(paper.question_ids or "[]")
            except json.JSONDecodeError:
                ids = []
            if essay.id not in ids:
                ids.append(essay.id)
                paper.question_ids = json.dumps(ids)

    lab_defaults = [
        ("cube", "正方体", "solid", "认识正方体棱面关系", "立体几何"),
        ("box", "长方体", "solid", "长方体空间结构", "立体几何"),
        ("pyramid", "棱锥", "solid", "棱锥顶点与底面", "立体几何"),
        ("random-7", "随机变式题", "solid", "种子随机出题巩固解题范式", "立体几何"),
        ("ellipse_dot_range", "椭圆焦点弦", "analytic", "解析几何参数探究", "解析几何"),
        ("ellipse_chord_range", "椭圆弦长范围", "analytic", "参数直线扫过圆锥曲线", "解析几何"),
        ("ellipse_area_max", "椭圆面积最大", "analytic", "面积极值探究", "解析几何"),
        ("ellipse_slopeprod_const", "椭圆斜率积恒定", "analytic", "斜率积性质", "解析几何"),
        ("parabola_dot_const", "抛物线焦点弦", "analytic", "焦点弦数量积", "解析几何"),
        ("hyperbola_ecc_range", "双曲线离心率", "analytic", "离心率取值范围", "解析几何"),
        ("combustion_ch4", "甲烷燃烧微观", "chem", "CH₄ 燃烧微观粒子过程", "化学反应"),
        ("esterification", "酯化反应微观", "chem", "乙酸乙醇酯化微观演示", "化学反应"),
    ]
    for key, title, category, desc, kp in lab_defaults:
        page = db.scalar(select(LabPage).where(LabPage.page_key == key))
        if not page:
            db.add(
                LabPage(
                    page_key=key,
                    title=title,
                    category=category,
                    description=desc,
                    preview_path=f"/courses/geometry-lab/{key}",
                    knowledge_points=kp,
                )
            )
        elif not (page.knowledge_points or "").strip():
            page.knowledge_points = kp

    # 化学反应客观题（幂等）
    chem_q = db.scalar(select(Question).where(Question.stem.contains("甲烷完全燃烧")))
    if not chem_q:
        db.add_all(
            [
                Question(
                    type="single",
                    stem="甲烷完全燃烧的化学方程式中，产物是？",
                    options_json=json.dumps(["CO 和 H₂O", "CO₂ 和 H₂O", "C 和 H₂O", "CO₂ 和 H₂"], ensure_ascii=False),
                    answer="1",
                    analysis="CH₄ + 2O₂ → CO₂ + 2H₂O",
                    knowledge_points="化学反应",
                    difficulty=1,
                ),
                Question(
                    type="judge",
                    stem="酯化反应是酸与醇生成酯和水的反应。",
                    options_json=json.dumps(["正确", "错误"], ensure_ascii=False),
                    answer="0",
                    analysis="羧酸与醇在酸催化下发生酯化。",
                    knowledge_points="化学反应",
                    difficulty=1,
                ),
            ]
        )
        db.flush()

    # 立体几何变式巩固题
    variant = db.scalar(select(Question).where(Question.stem.contains("正方体一条面对角线")))
    if not variant:
        db.add(
            Question(
                type="single",
                stem="正方体一条面对角线与异面的棱所成角的余弦值为？",
                options_json=json.dumps(["1/2", "√2/2", "√3/3", "√6/3"], ensure_ascii=False),
                answer="2",
                analysis="建系后可用向量夹角公式计算，常见结果为 √3/3。",
                knowledge_points="立体几何",
                difficulty=3,
            )
        )
        db.flush()

    # 课页 ↔ 题目显式关联（按知识点各挂最多 4 题，幂等；放在题目种子之后）
    for page in db.scalars(select(LabPage)):
        existing = list(
            db.scalars(select(LabPageQuestion).where(LabPageQuestion.page_key == page.page_key))
        )
        if existing:
            continue
        kps = [p.strip() for p in (page.knowledge_points or "").split(",") if p.strip()]
        qids: list[int] = []
        for kp in kps or ["立体几何"]:
            rows = list(
                db.scalars(
                    select(Question)
                    .where(Question.knowledge_points.contains(kp), Question.type != "essay")
                    .order_by(Question.id)
                    .limit(4)
                )
            )
            for q in rows:
                if q.id not in qids:
                    qids.append(q.id)
        for i, qid in enumerate(qids[:6]):
            db.add(LabPageQuestion(page_key=page.page_key, question_id=qid, sort_order=i))
        if qids:
            page.question_ids = ",".join(str(i) for i in qids[:6])

    if db.scalar(select(func.count()).select_from(Ebook)) == 0:
        book = Ebook(
            title="立体几何入门读本",
            cover="",
            summary="从空间几何体到线面关系的简明读物。",
            status="published",
        )
        db.add(book)
        db.flush()
        db.add_all(
            [
                EbookChapter(
                    ebook_id=book.id,
                    title="第一章 空间几何体",
                    content="空间几何体包括柱、锥、台、球等。观察时注意顶点、棱与面的位置关系。",
                    sort_order=1,
                ),
                EbookChapter(
                    ebook_id=book.id,
                    title="第二章 线面角",
                    content="平面的一条斜线和它在平面上的射影所成的角，叫做这条线和这个平面所成的角。",
                    sort_order=2,
                ),
            ]
        )

    student = db.scalar(select(User).where(User.email == "student@edu.ai"))
    if student and db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == student.id)) == 0:
        db.add(
            Notification(
                user_id=student.id,
                title="欢迎来到学习中心",
                body="可以查看错题本、学情简报，并完成主观题练习等待教师复核。",
                link="/me",
                kind="system",
            )
        )

    vocab_seed = [
        ("unhappy", "/ʌnˈhæpi/", "不开心的；不快乐的", "She looked unhappy after the exam.", "A2"),
        ("telephone", "/ˈtelɪfəʊn/", "电话；通话", "Please answer the telephone.", "A2"),
        ("angle", "/ˈæŋɡl/", "角；角度", "The angle between the line and the plane.", "B1"),
        ("plane", "/pleɪn/", "平面", "A line intersects a plane.", "B1"),
        ("projection", "/prəˈdʒekʃn/", "射影；投影", "the projection of a line on a plane", "B2"),
        ("geometry", "/dʒiˈɒmətri/", "几何", "Solid geometry is fascinating.", "A2"),
        ("vertical", "/ˈvɜːtɪkl/", "垂直的", "The flagpole is vertical to the ground.", "A2"),
        ("intersect", "/ˌɪntəˈsekt/", "相交", "Two lines intersect at one point.", "B1"),
        ("demonstrate", "/ˈdemənstreɪt/", "证明；演示", "Please demonstrate your reasoning.", "B1"),
        ("accurate", "/ˈækjərət/", "准确的", "Give an accurate definition.", "B1"),
    ]
    if db.scalar(select(func.count()).select_from(VocabWord)) == 0:
        for word, phonetic, meaning, example, level in vocab_seed:
            morph = morph_for(word)
            db.add(
                VocabWord(
                    word=word,
                    phonetic=phonetic,
                    meaning=meaning,
                    example=example,
                    level=level,
                    morphology_json=morph_json_dumps(morph),
                    image_key=str(morph.get("image_key") or word),
                )
            )
    else:
        # 幂等升级：补词根词缀 / 配图键，并加入示范长单词
        existing = {w.word.lower(): w for w in db.scalars(select(VocabWord))}
        for word, phonetic, meaning, example, level in vocab_seed:
            morph = morph_for(word)
            row = existing.get(word.lower())
            if not row:
                db.add(
                    VocabWord(
                        word=word,
                        phonetic=phonetic,
                        meaning=meaning,
                        example=example,
                        level=level,
                        morphology_json=morph_json_dumps(morph),
                        image_key=str(morph.get("image_key") or word),
                    )
                )
                continue
            if not (row.morphology_json or "").strip():
                row.morphology_json = morph_json_dumps(morph)
            if not (row.image_key or "").strip():
                row.image_key = str(morph.get("image_key") or word)

    if db.scalar(select(func.count()).select_from(DailyArticle)) == 0:
        db.add_all(
            [
                DailyArticle(
                    title="如何建立空间想象",
                    summary="从实物观察走到抽象模型。",
                    body=(
                        "学习立体几何时，先拿笔帽、书本等实物比划线面关系，"
                        "再对照三维模型旋转观察。把「看得见」变成「说得清」，"
                        "是空间想象的第一步。"
                    ),
                    lang="zh",
                    published=True,
                ),
                DailyArticle(
                    title="A Short Note on Angles",
                    summary="A gentle English reading for geometry learners.",
                    body=(
                        "An angle measures how two lines or a line and a plane meet. "
                        "In space, the angle between a line and a plane is formed by "
                        "the line and its projection on the plane. Try saying this aloud."
                    ),
                    lang="en",
                    published=True,
                ),
            ]
        )

    if db.scalar(select(func.count()).select_from(PaperTemplate)) == 0:
        db.add(
            PaperTemplate(
                name="立体几何小测模板",
                description="单选+判断+主观，适合随堂检测",
                question_types="single,judge,essay",
                default_count=6,
            )
        )
    if db.scalar(select(func.count()).select_from(PptTemplate)) == 0:
        db.add(
            PptTemplate(
                name="概念课标准版",
                theme="teal",
                outline_hint="导入\n核心概念\n例题精讲\n课堂练习\n小结作业",
            )
        )

    # 向量索引：已有文档但无切片时自动建索引
    for kb in db.scalars(select(KnowledgeBase)):
        chunk_n = db.scalar(
            select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.kb_id == kb.id)
        ) or 0
        if chunk_n == 0:
            reindex_kb(db, kb.id)

    db.commit()
