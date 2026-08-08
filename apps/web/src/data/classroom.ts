/** AI多智能体互动课堂：幻灯 / 测验 / 模拟 / PBL */

export type SceneType = 'slide' | 'quiz' | 'sim' | 'pbl'

export interface ClassroomAgent {
  id: string
  name: string
  role: 'teacher' | 'peer' | 'mentor'
  persona: string
}

export interface SlideScene {
  type: 'slide'
  id: string
  title: string
  bullets: string[]
  narrate: string
  spotlight?: string
}

export interface QuizQuestion {
  id: string
  stem: string
  options: string[]
  answerIndex: number
  explain: string
}

export interface QuizScene {
  type: 'quiz'
  id: string
  title: string
  questions: QuizQuestion[]
}

export interface SimScene {
  type: 'sim'
  id: string
  title: string
  blurb: string
  /** 内嵌交互：geometry iframe / coding playground / custom */
  kind: 'geometry' | 'coding' | 'widget'
  href?: string
  widgetId?: string
  task: string
}

export interface PblMilestone {
  id: string
  title: string
  doneHint: string
}

export interface PblScene {
  type: 'pbl'
  id: string
  title: string
  brief: string
  roles: string[]
  milestones: PblMilestone[]
  deliverable: string
}

export type ClassroomScene = SlideScene | QuizScene | SimScene | PblScene

export interface ClassroomLesson {
  id: string
  title: string
  topic: string
  durationMin: number
  tag: string
  agents: ClassroomAgent[]
  scenes: ClassroomScene[]
  orchestrationNote: string
}

export const sceneMeta: Record<
  SceneType,
  { label: string; verb: string; color: string }
> = {
  slide: { label: '幻灯讲解', verb: '听懂', color: '#0F6B5C' },
  quiz: { label: '测验检验', verb: '检验', color: '#C48912' },
  sim: { label: '模拟动手', verb: '动手', color: '#243642' },
  pbl: { label: 'PBL 创造', verb: '创造', color: '#0A4F44' },
}

/** 示例课：把几何动图能力编进四场景课堂 */
export const demoClassroom: ClassroomLesson = {
  id: 'line-plane-angle',
  title: '线面角：从看到懂',
  topic: '立体几何 · 直线与平面所成角',
  durationMin: 25,
  tag: 'AI 编排课堂',
  orchestrationNote:
    'AI 统筹：先建立概念（幻灯）→ 快速检验（测验）→ 拖动模型内化（模拟）→ 小组项目创造（PBL）。',
  agents: [
    {
      id: 't-lin',
      name: '林老师',
      role: 'teacher',
      persona: '条理清晰的几何老师，擅长用向量法拆解空间问题。',
    },
    {
      id: 'p-an',
      name: '安安',
      role: 'peer',
      persona: '爱提问的同学，会把你卡住的地方说出来。',
    },
    {
      id: 'm-kai',
      name: '凯凯',
      role: 'mentor',
      persona: '项目导师，帮你把知识变成可交付作品。',
    },
  ],
  scenes: [
    {
      type: 'slide',
      id: 's1',
      title: '什么是线面角？',
      bullets: [
        '直线与平面所成角：直线与它在平面上的射影所成的锐角（或直角）',
        '取值范围：θ ∈ [0°, 90°]',
        '常用解法：建系 + 方向向量与法向量 → sinθ = |d·n| / (|d||n|)',
      ],
      narrate:
        '先抓住定义：线面角是直线和它在平面上射影的夹角。别急着套公式，先想清楚「射影」在哪里。',
      spotlight: 'sinθ = |d·n| / (|d||n|)',
    },
    {
      type: 'slide',
      id: 's2',
      title: '正方体里的经典模型',
      bullets: [
        '正方体 ABCD-A₁B₁C₁D₁，棱长为 1',
        '求直线 A₁C 与底面 ABCD 所成角的正弦值',
        '建系后，方向向量与法向量立刻可算',
      ],
      narrate:
        '把问题放进正方体。底面法向量竖直向上，斜线 A₁C 的方向一目了然——这就是今天动手模拟的原型。',
    },
    {
      type: 'quiz',
      id: 'q1',
      title: '概念快检',
      questions: [
        {
          id: 'q1-1',
          stem: '线面角 θ 的取值范围是？',
          options: ['(0°, 90°)', '[0°, 90°]', '[0°, 180°]', '(0°, 180°)'],
          answerIndex: 1,
          explain: '线面角取锐角或直角，故为闭区间 [0°, 90°]。',
        },
        {
          id: 'q1-2',
          stem: '已知直线方向向量 d 与平面法向量 n，求线面角正弦值应使用？',
          options: [
            'cosθ = |d·n| / (|d||n|)',
            'sinθ = |d·n| / (|d||n|)',
            'tanθ = |d·n| / (|d||n|)',
            'θ = d·n',
          ],
          answerIndex: 1,
          explain: '直线与法向量夹角的余弦，对应线面角的正弦：sinθ = |d·n|/(|d||n|)。',
        },
        {
          id: 'q1-3',
          stem: '正方体中求 A₁C 与底面夹角，底面法向量通常取？',
          options: ['(1,0,0)', '(0,1,0)', '(0,0,1)', '(1,1,0)'],
          answerIndex: 2,
          explain: '底面水平时，法向量取竖直方向 (0,0,1)（坐标系取向可等价）。',
        },
      ],
    },
    {
      type: 'sim',
      id: 'sim1',
      title: '拖动正方体，看清线面角',
      blurb: '打开几何动图课页：旋转模型、分步高亮，把公式和空间位置对齐。',
      kind: 'geometry',
      href: '/geometry-lab/solid/cube.html',
      task: '完成「建立坐标系 → 写出向量 → 代入公式」三步，并记下正弦值。',
    },
    {
      type: 'pbl',
      id: 'pbl1',
      title: '项目：做一页「线面角讲解卡」',
      brief:
        '用今天的模型，为同学制作一张讲解卡：定义 + 一例题 + 一张草图说明。可与 AI 同伴分工。',
      roles: ['讲解员（写定义）', '例题官（选题与解答）', '可视化（画/截图标注）'],
      milestones: [
        { id: 'm1', title: '选定一例（正方体或棱锥）', doneHint: '写下题干一句话' },
        { id: 'm2', title: '写出向量解法要点', doneHint: '不超过 5 行' },
        { id: 'm3', title: '配一张图或截图标注', doneHint: '标出直线与平面' },
      ],
      deliverable: '一张可分享的讲解卡（文字 + 图）',
    },
  ],
}

export const classroomCatalog: ClassroomLesson[] = [demoClassroom]
