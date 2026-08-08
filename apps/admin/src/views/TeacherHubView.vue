<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchDashboard, fetchGradeQueue, fetchMe, type Dashboard, type User } from '../lib/api'

const router = useRouter()
const me = ref<User | null>(null)
const data = ref<Dashboard | null>(null)
const pendingGrades = ref(0)

const cards = computed(() => {
  const d = data.value
  return [
    {
      title: '我的班级',
      tip: d ? `共 ${d.classes} 个班级` : '管理花名册与课程',
      to: '/classes',
      tone: 'teal',
    },
    {
      title: '批改复核',
      tip: pendingGrades.value ? `${pendingGrades.value} 条待处理` : '主观题队列',
      to: '/grading',
      tone: 'amber',
    },
    {
      title: '学情与推送',
      tip: '薄弱点与练习推送',
      to: '/reports',
      tone: 'blue',
    },
    {
      title: '反馈工单',
      tip: d ? `待处理 ${d.feedback_open ?? 0}` : '处理学员反馈',
      to: '/feedback',
      tone: 'rose',
    },
    {
      title: '课程内容',
      tip: '维护课程与章节',
      to: '/courses',
      tone: 'mint',
    },
    {
      title: '题库试卷',
      tip: '组卷与题目管理',
      to: '/questions',
      tone: 'slate',
    },
  ]
})

onMounted(async () => {
  ;[me.value, data.value] = await Promise.all([fetchMe(), fetchDashboard()])
  try {
    const q = await fetchGradeQueue('')
    pendingGrades.value = q.length
  } catch {
    pendingGrades.value = data.value?.grade_pending ?? 0
  }
})
</script>

<template>
  <div class="hub">
    <header class="hero">
      <div>
        <p class="eyebrow">教师工作台</p>
        <h1>你好，{{ me?.display_name || '老师' }}</h1>
        <p class="sub">今日待办：批改、班级、学情与反馈，一屏直达。</p>
      </div>
      <el-button type="primary" @click="router.push('/grading')">去批改队列</el-button>
    </header>

    <div class="grid">
      <button
        v-for="c in cards"
        :key="c.to"
        type="button"
        class="card"
        :class="c.tone"
        @click="router.push(c.to)"
      >
        <h2>{{ c.title }}</h2>
        <p>{{ c.tip }}</p>
      </button>
    </div>

    <el-card shadow="never" class="tips">
      <template #header>使用提示</template>
      <ul>
        <li>班级管理只显示你任教的班，可直接维护花名册。</li>
        <li>批改页支持「抽样质检」，优先抽低置信度 AI 评分。</li>
        <li>学情页可导出 CSV，并向班级推送薄弱点练习。</li>
      </ul>
    </el-card>
  </div>
</template>

<style scoped>
.hub {
  max-width: 960px;
}
.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 18px;
}
.eyebrow {
  margin: 0;
  color: var(--edu-teal);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 12px;
}
h1 {
  margin: 6px 0 4px;
  font-family: 'Noto Serif SC', serif;
  font-size: 28px;
  color: #14212b;
}
.sub {
  margin: 0;
  color: var(--edu-muted);
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.card {
  border: 0;
  text-align: left;
  border-radius: 14px;
  padding: 18px 16px;
  color: #fff;
  cursor: pointer;
  min-height: 110px;
}
.card h2 {
  margin: 0 0 8px;
  font-size: 18px;
}
.card p {
  margin: 0;
  opacity: 0.92;
  font-size: 13px;
  line-height: 1.45;
}
.teal {
  background: linear-gradient(145deg, #0f6b5c, #148f7a);
}
.amber {
  background: linear-gradient(145deg, #c9840f, #e8a317);
}
.blue {
  background: linear-gradient(145deg, #1f6f9a, #2a8fbd);
}
.rose {
  background: linear-gradient(145deg, #a14a3a, #c45c26);
}
.mint {
  background: linear-gradient(145deg, #3d7a5c, #5b8c5a);
}
.slate {
  background: linear-gradient(145deg, #3d4f5f, #5c6b73);
}
.tips ul {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  line-height: 1.7;
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 560px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
