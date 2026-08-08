import type { ClassroomLesson, ClassroomScene } from '../data/classroom'

/**
 * AI 统筹编排（本地可演示版）：
 * 主题 → 大纲 → 四类场景：幻灯 → 测验 → 模拟 → PBL
 * 若配置了 LLM，可走云端增强；否则用结构化模板即时成课。
 */
export async function orchestrateClassroom(topic: string): Promise<ClassroomLesson> {
  const clean = topic.trim() || '未命名主题'
  const base = import.meta.env.VITE_LLM_BASE_URL as string | undefined
  const key = import.meta.env.VITE_LLM_API_KEY as string | undefined

  if (base && key) {
    try {
      const cloud = await orchestrateViaLLM(clean, base, key)
      if (cloud) return cloud
    } catch {
      /* fallback */
    }
  }
  return buildLocalClassroom(clean)
}

async function orchestrateViaLLM(
  topic: string,
  base: string,
  key: string,
): Promise<ClassroomLesson | null> {
  const model = (import.meta.env.VITE_LLM_MODEL as string | undefined) || 'gpt-4o-mini'
  const system = `你是课程编排 AI。根据主题输出 JSON（不要 markdown），结构：
{"title":"...","durationMin":25,"scenes":[
{"type":"slide","title":"...","bullets":["..."],"narrate":"..."},
{"type":"slide","title":"...","bullets":["..."],"narrate":"..."},
{"type":"quiz","title":"...","questions":[{"stem":"...","options":["A","B","C","D"],"answerIndex":0,"explain":"..."}]},
{"type":"sim","title":"...","blurb":"...","task":"..."},
{"type":"pbl","title":"...","brief":"...","roles":["..."],"milestones":[{"title":"...","doneHint":"..."}],"deliverable":"..."}
]}
必须包含 slide、quiz、sim、pbl 四类；quiz 至少 2 题。中文输出。`

  const res = await fetch(`${base.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model,
      temperature: 0.4,
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: `主题：${topic}` },
      ],
    }),
  })
  if (!res.ok) return null
  const data = (await res.json()) as {
    choices?: Array<{ message?: { content?: string } }>
  }
  const raw = data.choices?.[0]?.message?.content?.trim()
  if (!raw) return null
  const jsonText = raw.replace(/^```json\s*/i, '').replace(/```$/i, '').trim()
  const parsed = JSON.parse(jsonText) as {
    title?: string
    durationMin?: number
    scenes?: Array<Record<string, unknown>>
  }
  return normalizeCloudLesson(topic, parsed)
}

function normalizeCloudLesson(
  topic: string,
  parsed: {
    title?: string
    durationMin?: number
    scenes?: Array<Record<string, unknown>>
  },
): ClassroomLesson {
  const scenes: ClassroomScene[] = []
  let i = 0
  for (const s of parsed.scenes || []) {
    i += 1
    const type = String(s.type || '')
    if (type === 'slide') {
      scenes.push({
        type: 'slide',
        id: `slide-${i}`,
        title: String(s.title || `讲解 ${i}`),
        bullets: Array.isArray(s.bullets) ? s.bullets.map(String) : [],
        narrate: String(s.narrate || ''),
        spotlight: s.spotlight ? String(s.spotlight) : undefined,
      })
    } else if (type === 'quiz') {
      const qs = Array.isArray(s.questions) ? s.questions : []
      scenes.push({
        type: 'quiz',
        id: `quiz-${i}`,
        title: String(s.title || '测验'),
        questions: qs.map((q: Record<string, unknown>, qi: number) => ({
          id: `q-${i}-${qi}`,
          stem: String(q.stem || ''),
          options: Array.isArray(q.options) ? q.options.map(String) : [],
          answerIndex: Number(q.answerIndex ?? 0),
          explain: String(q.explain || ''),
        })),
      })
    } else if (type === 'sim') {
      scenes.push({
        type: 'sim',
        id: `sim-${i}`,
        title: String(s.title || '动手模拟'),
        blurb: String(s.blurb || ''),
        kind: 'widget',
        widgetId: 'generic',
        task: String(s.task || '完成一次动手操作并记录观察。'),
      })
    } else if (type === 'pbl') {
      const ms = Array.isArray(s.milestones) ? s.milestones : []
      scenes.push({
        type: 'pbl',
        id: `pbl-${i}`,
        title: String(s.title || '项目创造'),
        brief: String(s.brief || ''),
        roles: Array.isArray(s.roles) ? s.roles.map(String) : ['研究员', '讲解员'],
        milestones: ms.map((m: Record<string, unknown>, mi: number) => ({
          id: `m-${i}-${mi}`,
          title: String(m.title || `里程碑 ${mi + 1}`),
          doneHint: String(m.doneHint || '完成即可勾选'),
        })),
        deliverable: String(s.deliverable || '一份可展示的作品'),
      })
    }
  }

  if (!scenes.some((x) => x.type === 'slide')) {
    return buildLocalClassroom(topic)
  }

  return {
    id: `gen-${Date.now()}`,
    title: parsed.title || `${topic} · 互动课堂`,
    topic,
    durationMin: parsed.durationMin || 25,
    tag: 'AI 编排课堂',
    orchestrationNote: 'AI 统筹：幻灯讲解 → 测验检验 → 模拟动手 → PBL 创造。',
    agents: defaultAgents(),
    scenes: ensureFourTypes(scenes, topic),
  }
}

function defaultAgents() {
  return [
    {
      id: 't1',
      name: '林老师',
      role: 'teacher' as const,
      persona: '主讲教师，负责幻灯讲解与节奏把控。',
    },
    {
      id: 'p1',
      name: '安安',
      role: 'peer' as const,
      persona: '同伴学员，提出典型疑问。',
    },
    {
      id: 'm1',
      name: '凯凯',
      role: 'mentor' as const,
      persona: '项目导师，陪伴 PBL 交付。',
    },
  ]
}

function ensureFourTypes(scenes: ClassroomScene[], topic: string): ClassroomScene[] {
  const has = (t: ClassroomScene['type']) => scenes.some((s) => s.type === t)
  const local = buildLocalClassroom(topic)
  const out = [...scenes]
  for (const t of ['quiz', 'sim', 'pbl'] as const) {
    if (!has(t)) {
      const fill = local.scenes.find((s) => s.type === t)
      if (fill) out.push(fill)
    }
  }
  return out
}

export function buildLocalClassroom(topic: string): ClassroomLesson {
  const short = topic.length > 18 ? `${topic.slice(0, 18)}…` : topic
  return {
    id: `local-${Date.now()}`,
    title: `${short} · 四场景好课`,
    topic,
    durationMin: 20,
    tag: 'AI 编排课堂',
    orchestrationNote:
      'AI 统筹编排：幻灯讲解建立图式 → 测验检验掌握度 → 模拟让你动手 → PBL 让你创造。',
    agents: defaultAgents(),
    scenes: [
      {
        type: 'slide',
        id: 'ls1',
        title: `认识：${short}`,
        bullets: [
          `今天的主题是「${topic}」`,
          '先建立核心概念与关键词',
          '再通过练习与项目把知识用起来',
        ],
        narrate: `同学们好。这一课我们围绕「${topic}」展开：先听懂，再检验，然后动手，最后创造。`,
        spotlight: topic,
      },
      {
        type: 'slide',
        id: 'ls2',
        title: '学习路径',
        bullets: [
          '幻灯：抓住定义与关键例子',
          '测验：暴露盲点',
          '模拟：在交互环境中试错',
          'PBL：产出可展示的小作品',
        ],
        narrate: '四种场景不是堆砌，而是一条完整学习闭环——这正是好课的结构。',
      },
      {
        type: 'quiz',
        id: 'lq1',
        title: '入口测验',
        questions: [
          {
            id: 'lq1-1',
            stem: `学习「${short}」时，更有效的第一步通常是？`,
            options: ['直接做难题', '先明确核心概念', '跳过练习', '只看答案'],
            answerIndex: 1,
            explain: '先建立概念图式，再练习与迁移，效率更高。',
          },
          {
            id: 'lq1-2',
            stem: '「模拟动手」场景的主要目的是？',
            options: ['代替思考', '通过交互内化原理', '增加娱乐', '取消测验'],
            answerIndex: 1,
            explain: '动手模拟帮助把抽象原理变成可操作的经验。',
          },
        ],
      },
      {
        type: 'sim',
        id: 'lsim',
        title: '动手工作台',
        blurb: '用简易交互完成一次「观察 → 记录」练习。',
        kind: 'widget',
        widgetId: ' contr-counter',
        task: `围绕「${topic}」完成 3 次尝试，并写下你发现的规律。`,
      },
      {
        type: 'pbl',
        id: 'lpbl',
        title: '迷你项目：主题表达卡',
        brief: `把「${topic}」讲给他人听：用三句话 + 一个例子 + 一个待解决问题。`,
        roles: ['主笔', '举例官', '提问官'],
        milestones: [
          { id: 'lm1', title: '写出三句核心解释', doneHint: '每句不超过 20 字' },
          { id: 'lm2', title: '补充一个生活/学科例子', doneHint: '具体可感知' },
          { id: 'lm3', title: '提出一个延伸问题', doneHint: '值得继续探索' },
        ],
        deliverable: '一张主题表达卡',
      },
    ],
  }
}
