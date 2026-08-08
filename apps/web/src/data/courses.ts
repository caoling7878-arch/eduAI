export type CourseId =
  | 'geometry-lab'
  | 'english-coach'
  | 'ai-coding'
  | 'classroom'
  | 'love-words'
  | 'math-calc'

export interface CourseMeta {
  id: CourseId
  title: string
  subtitle: string
  tag: string
  audience: string
  duration: string
  lessons: number
  route: string
  coverTone: 'forest' | 'amber' | 'slate'
  highlights: string[]
}

export const hotCourses: CourseMeta[] = [
  {
    id: 'love-words',
    title: '我爱背单词',
    subtitle: '中考 800 核心词 · 艾宾浩斯复习 · 拆解配图 · 每日测验打卡得星',
    tag: '词汇课程',
    audience: '中学生',
    duration: '每日 5–100 词',
    lessons: 800,
    route: '/courses/love-words',
    coverTone: 'amber',
    highlights: ['中学生必背词库', '艾宾浩斯复习', '测验打卡兑会员'],
  },
  {
    id: 'math-calc',
    title: '小学数学计算专项练习',
    subtitle: '1–6 年级计算题库 · 每日一页随机练习 · 提交判分 · 错题订正',
    tag: '数学专项',
    audience: '小学 1–6 年级',
    duration: '每日 10–100 题',
    lessons: 6,
    route: '/courses/math-calc',
    coverTone: 'forest',
    highlights: ['分年级选题', '随机每日练习', '错题本同步'],
  },
  {
    id: 'geometry-lab',
    title: '几何动图实验室',
    subtitle: '立体几何与圆锥曲线，拖一拖就能看懂的交互课页',
    tag: '数学可视化',
    audience: '初高中',
    duration: '随练随开',
    lessons: 10,
    route: '/courses/geometry-lab',
    coverTone: 'forest',
    highlights: ['Three.js 立体几何', 'Canvas 解析几何', 'sympy 精确答案'],
  },
  {
    id: 'english-coach',
    title: '英语陪练',
    subtitle: '情景口语对话，纠音建议与表达升级，随时开练',
    tag: 'AI 口语',
    audience: '全年龄',
    duration: '15 分钟/场',
    lessons: 8,
    route: '/courses/english-coach',
    coverTone: 'amber',
    highlights: ['情景角色扮演', '即时反馈', '表达润色'],
  },
  {
    id: 'ai-coding',
    title: '青少年 AI 编程入门',
    subtitle: '从零认识 AI，用代码画图、做对话小助手',
    tag: '编程启蒙',
    audience: '10–16 岁',
    duration: '6 课时',
    lessons: 6,
    route: '/courses/ai-coding',
    coverTone: 'slate',
    highlights: ['可视化练习', '浏览器直接跑', 'AI 思维入门'],
  },
  {
    id: 'classroom',
    title: 'AI 互动课堂',
    subtitle: '把任何主题或文档变成一场沉浸式课堂',
    tag: 'AI多智能体',
    audience: '全学段',
    duration: '20–30 分钟',
    lessons: 4,
    route: '/classroom',
    coverTone: 'forest',
    highlights: ['幻灯讲解', '测验检验', '模拟动手', 'PBL 创造'],
  },
]

export interface GeometryLesson {
  id: string
  title: string
  category: 'solid' | 'analytic' | 'chem'
  path: string
  blurb: string
}

export const geometryLessons: GeometryLesson[] = [
  {
    id: 'cube',
    title: '正方体 · 线面角',
    category: 'solid',
    path: '/geometry-lab/solid/cube.html',
    blurb: '建系 + 向量法，旋转模型看直线与底面所成角',
  },
  {
    id: 'box',
    title: '长方体 · 体积',
    category: 'solid',
    path: '/geometry-lab/solid/box.html',
    blurb: '长宽高可视化，分步推导体积公式',
  },
  {
    id: 'pyramid',
    title: '正四棱锥 · 线面角',
    category: 'solid',
    path: '/geometry-lab/solid/pyramid.html',
    blurb: '侧棱与底面关系，3D 高亮关键元素',
  },
  {
    id: 'random-7',
    title: '随机变式题',
    category: 'solid',
    path: '/geometry-lab/solid/random-7.html',
    blurb: '种子随机出题，学完可进入巩固练习',
  },
  {
    id: 'ellipse_dot_range',
    title: '椭圆 · 数量积取值范围',
    category: 'analytic',
    path: '/geometry-lab/analytic/ellipse_dot_range.html',
    blurb: '拖动 θ，观察 MA·MB 与理论范围条对齐',
  },
  {
    id: 'ellipse_chord_range',
    title: '椭圆 · 弦长范围',
    category: 'analytic',
    path: '/geometry-lab/analytic/ellipse_chord_range.html',
    blurb: '参数直线扫过圆锥曲线，读出弦长变化',
  },
  {
    id: 'ellipse_area_max',
    title: '椭圆 · 三角形面积最值',
    category: 'analytic',
    path: '/geometry-lab/analytic/ellipse_area_max.html',
    blurb: '面积随参数变化，找极值位置',
  },
  {
    id: 'ellipse_slopeprod_const',
    title: '椭圆 · 斜率之积定值',
    category: 'analytic',
    path: '/geometry-lab/analytic/ellipse_slopeprod_const.html',
    blurb: '定值问题：交互验证斜率乘积恒定',
  },
  {
    id: 'parabola_dot_const',
    title: '抛物线 · 焦点弦定值',
    category: 'analytic',
    path: '/geometry-lab/analytic/parabola_dot_const.html',
    blurb: '焦点弦上向量数量积恒等于定值',
  },
  {
    id: 'hyperbola_ecc_range',
    title: '双曲线 · 离心率范围',
    category: 'analytic',
    path: '/geometry-lab/analytic/hyperbola_ecc_range.html',
    blurb: '离心率随参数变化的取值范围',
  },
  {
    id: 'combustion_ch4',
    title: '甲烷燃烧 · 微观过程',
    category: 'chem',
    path: '/geometry-lab/chem/combustion_ch4.html',
    blurb: '3D 粒子演示 CH₄ 燃烧键能与产物生成',
  },
  {
    id: 'esterification',
    title: '酯化反应 · 微观过程',
    category: 'chem',
    path: '/geometry-lab/chem/esterification.html',
    blurb: '酸醇酯化的分子碰撞与官能团变化',
  },
]

export interface EnglishScenario {
  id: string
  title: string
  level: 'A2' | 'B1' | 'B2'
  setting: string
  goals: string[]
  starter: string
  coachSystem: string
}

export const englishScenarios: EnglishScenario[] = [
  {
    id: 'cafe',
    title: '咖啡店点单',
    level: 'A2',
    setting: '你在一家街角咖啡店点饮品与轻食',
    goals: ['礼貌点单', '确认杯型与加料', '询问价格或等候时间'],
    starter: "Hi! I'd like to order something. What do you recommend today?",
    coachSystem:
      'You are a warm English speaking coach role-playing as a barista. Keep replies short (2–4 sentences), ask follow-up questions, gently correct major grammar in a tip after your reply, and encourage the learner.',
  },
  {
    id: 'school',
    title: '校园自我介绍',
    level: 'A2',
    setting: '开学第一天，和新同学互相认识',
    goals: ['介绍姓名与爱好', '询问对方信息', '约定一起活动'],
    starter: "Hello! I'm new here. My name is Alex. What's your name?",
    coachSystem:
      'You are a friendly classmate helping a learner practice English self-introduction. Reply naturally, ask simple questions, and give one brief correction tip when needed.',
  },
  {
    id: 'travel',
    title: '机场问路',
    level: 'B1',
    setting: '国际机场转机，询问登机口与安检',
    goals: ['问路', '确认时间', '听懂指示并复述'],
    starter: 'Excuse me, could you tell me how to get to Gate B12?',
    coachSystem:
      'You are an airport information desk staff. Give clear directions in simple English, check understanding, and provide concise language tips.',
  },
  {
    id: 'interview',
    title: '模拟面试',
    level: 'B2',
    setting: '科技公司暑期实习面试',
    goals: ['回答经历问题', '表达动机', '提问岗位'],
    starter: 'Good morning. Thank you for having me. I’m excited about this internship.',
    coachSystem:
      'You are a professional but kind interviewer. Ask one question at a time, respond to answers, and offer a short coaching tip on clearer or more confident phrasing.',
  },
]

export interface CodingLesson {
  id: string
  index: number
  title: string
  minutes: number
  summary: string
  concept: string
  starterCode: string
  hint: string
  checkpoint: string
}

export const codingLessons: CodingLesson[] = [
  {
    id: 'what-is-ai',
    index: 1,
    title: 'AI 是什么？',
    minutes: 12,
    summary: '用生活例子理解「输入 → 模型 → 输出」',
    concept:
      '人工智能（AI）擅长从例子里找规律。你给它输入（文字、图片），它按学过的规律给出输出。今天我们用代码模拟一个「超简单规则机器人」。',
    starterCode: `// 一个超简单的规则机器人
function reply(mood) {
  if (mood === 'happy') return '太好了！要不要学一招新技能？'
  if (mood === 'tired') return '先休息 5 分钟，再继续也不迟。'
  return '告诉我你现在的心情：happy / tired'
}

console.log(reply('happy'))
console.log(reply('tired'))
console.log(reply('curious'))
`,
    hint: '试着新增一种心情，比如 excited，让机器人说出你的句子。',
    checkpoint: '能说清：输入、规则、输出分别是什么。',
  },
  {
    id: 'variables',
    index: 2,
    title: '变量：给想法起名字',
    minutes: 15,
    summary: '用变量保存名字、分数和关卡',
    concept:
      '变量像贴了标签的盒子。把数据放进去，后面就能反复使用。编程里我们常用 const（不改）和 let（会改）。',
    starterCode: `const player = '小树'
let score = 0
let level = 1

score = score + 10
level = level + 1

console.log(player + ' 现在 ' + score + ' 分，第 ' + level + ' 关')
`,
    hint: '把得分再加 5，并打印一句鼓励的话。',
    checkpoint: '能区分什么时候用 const，什么时候用 let。',
  },
  {
    id: 'loops',
    index: 3,
    title: '循环：让计算机帮你重复',
    minutes: 15,
    summary: '用循环画出发光的星星字',
    concept: '循环让同一件事做很多次，又不容易写错。for 循环很适合「数着做」。',
    starterCode: `let sky = ''
for (let i = 0; i < 5; i++) {
  sky = sky + '★ '
}
console.log('夜空：' + sky)

for (let n = 1; n <= 3; n++) {
  console.log('第 ' + n + ' 次练习完成！')
}
`,
    hint: '把星星数量改成 8，并再打印一行月亮 ☾。',
    checkpoint: '能读懂循环变量 i / n 每一步怎么变。',
  },
  {
    id: 'draw',
    index: 4,
    title: '用代码画画',
    minutes: 18,
    summary: '在画布上画出你的第一枚徽章',
    concept:
      '计算机画画靠坐标。我们告诉它「在哪里、画多大、什么颜色」。下面用文字画布模拟像素风图案。',
    starterCode: `function badge(size) {
  const lines = []
  for (let y = 0; y < size; y++) {
    let row = ''
    for (let x = 0; x < size; x++) {
      const edge = x === 0 || y === 0 || x === size - 1 || y === size - 1
      const core = x === Math.floor(size / 2) && y === Math.floor(size / 2)
      row += core ? '◆' : edge ? '□' : '·'
    }
    lines.push(row)
  }
  return lines.join('\\n')
}

console.log(badge(7))
`,
    hint: '把 size 改成 9，或把中心符号换成你喜欢的字。',
    checkpoint: '能解释双重循环如何一行一行拼出图案。',
  },
  {
    id: 'mini-bot',
    index: 5,
    title: '做一个迷你对话助手',
    minutes: 20,
    summary: '关键词匹配 + 默认回复，拼出你的第一位 AI 学伴',
    concept:
      '真正的大模型很复杂，但「助手」的产品形态可以先从规则开始：听关键词 → 选回复。这能帮你理解提示词与对话产品。',
    starterCode: `function tutor(question) {
  const q = question.toLowerCase()
  if (q.includes('ai') || q.includes('人工智能')) {
    return 'AI 是会从数据里学习规律的程序。你可以先从做规则机器人练起！'
  }
  if (q.includes('循环') || q.includes('loop')) {
    return '循环用来重复做事。记住：开始、条件、每一步变化。'
  }
  if (q.includes('你好') || q.includes('hello')) {
    return '你好呀！今天想学变量、循环，还是一起做一个小助手？'
  }
  return '我还在学习中。试试问我：AI / 循环 / 你好'
}

;[
  '你好',
  '什么是 AI？',
  '循环怎么用？',
  '今天天气怎么样？',
].forEach((q) => {
  console.log('你：' + q)
  console.log('助手：' + tutor(q))
  console.log('---')
})
`,
    hint: '给助手增加「画画」关键词的专属回答。',
    checkpoint: '能说明规则助手和大模型助手的差别。',
  },
  {
    id: 'project',
    index: 6,
    title: '小项目：学习打卡机器人',
    minutes: 25,
    summary: '综合变量、循环与函数，完成作品并分享',
    concept:
      '把前面学过的积木拼起来：记录连续打卡天数，并根据天数给出不同鼓励。完成后，你就拥有了第一个可演示的作品。',
    starterCode: `function streakMessage(days) {
  if (days >= 7) return '一周达成！你已经拥有学习节奏感了。'
  if (days >= 3) return '连续三天，状态很稳，继续加油！'
  if (days >= 1) return '好的开始！明天再来打卡吧。'
  return '今天就是 Day 1，打开编辑器写一行代码吧。'
}

const name = '创作者'
let days = 0
const log = []

for (let i = 0; i < 5; i++) {
  days = days + 1
  log.push('Day ' + days + ' · ' + streakMessage(days))
}

console.log(name + ' 的打卡旅程：')
log.forEach((line) => console.log(line))
`,
    hint: '把循环改成 7 天，并在第 7 天打印特别彩蛋。',
    checkpoint: '能向家人演示：输入天数变化时，鼓励语如何变化。',
  },
]
