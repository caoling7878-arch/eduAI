<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { fetchMyGrades, fetchMyReport, fetchProgress } from '../lib/api'
import { courseLabel, courseRoute } from '../lib/courseLabels'
import { gradeStatusLabel } from '../lib/labels'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const report = ref<any>(null)
const grades = ref<any[]>([])
const courses = ref<any[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/learning' } })
    return
  }
  loading.value = true
  error.value = ''
  try {
    ;[report.value, grades.value] = await Promise.all([fetchMyReport(), fetchMyGrades()])
    try {
      const p = await fetchProgress()
      courses.value = p.courses || []
    } catch {
      courses.value = []
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>我的学情</h1>
    <p v-if="loading" class="sub">加载学情中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <template v-else-if="report">
      <p class="sub">根据练习、错题、打卡与批改自动汇总。</p>
      <div class="stats">
        <div><b>{{ report.avg_score_rate }}%</b><span>平均得分率</span></div>
        <div><b>{{ report.submissions }}</b><span>交卷次数</span></div>
        <div><b>{{ report.wrong_open }}</b><span>待攻克错题</span></div>
        <div><b>{{ report.checkins }}</b><span>累计打卡</span></div>
      </div>

      <section>
        <h2>薄弱知识点</h2>
        <ul>
          <li v-for="w in report.weak_points" :key="w.knowledge_point">
            <span>{{ w.knowledge_point }}</span>
            <em>{{ w.wrong_count }} 题</em>
          </li>
          <li v-if="!report.weak_points.length" class="muted">
            暂无明显薄弱点，
            <RouterLink to="/recommend">去做推荐练习</RouterLink>
          </li>
        </ul>
      </section>

      <section v-if="courses.length">
        <h2>课程进度</h2>
        <ul class="courses">
          <li v-for="c in courses" :key="c.course_id">
            <div>
              <RouterLink class="cname" :to="courseRoute(c.course_id)">{{ courseLabel(c.course_id) }}</RouterLink>
              <span>{{ c.completed }}/{{ c.total_items }} 完成</span>
            </div>
            <div class="bar"><i :style="{ width: c.percent + '%' }" /></div>
          </li>
        </ul>
      </section>

      <section>
        <h2>主观题批改</h2>
        <ul>
          <li v-for="g in grades.slice(0, 5)" :key="g.id">
            <span>{{ g.stem?.slice(0, 36) || `题目 #${g.question_id}` }}…</span>
            <em>
              {{
                g.status === 'teacher_reviewed'
                  ? `${g.teacher_score}/${g.max_score}`
                  : gradeStatusLabel(g.status)
              }}
            </em>
          </li>
          <li v-if="!grades.length" class="muted">暂无主观题批改记录</li>
        </ul>
      </section>

      <div class="links">
        <RouterLink to="/path">今日学习路径</RouterLink>
        <RouterLink to="/recommend">薄弱推荐作答</RouterLink>
        <RouterLink to="/wrongbook">去错题本</RouterLink>
        <RouterLink to="/practice">继续练习</RouterLink>
        <RouterLink to="/messages">消息与批改</RouterLink>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  width: min(820px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 0 0 6px;
}
.sub {
  color: var(--muted);
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 20px 0;
}
.stats div {
  background: #fff;
  border-radius: 14px;
  padding: 14px;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
.stats b {
  display: block;
  font-size: 1.5rem;
  color: var(--brand);
}
.stats span {
  color: var(--muted);
  font-size: 0.85rem;
}
section {
  margin-top: 22px;
}
h2 {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.15rem;
  margin: 0 0 8px;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(15, 107, 92, 0.08);
}
.muted {
  color: var(--muted);
}
.courses li {
  display: block;
}
.courses li > div:first-child {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.cname {
  color: var(--brand-deep);
  font-weight: 600;
}
.bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.1);
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  background: var(--brand);
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 20px;
}
.links a {
  color: var(--brand);
  font-weight: 600;
}
.err {
  color: #a35;
}
.retry {
  margin-left: 10px;
  border: 1px solid rgba(15, 107, 92, 0.3);
  background: #fff;
  color: var(--brand);
  border-radius: 999px;
  padding: 4px 12px;
  cursor: pointer;
}
.muted a {
  color: var(--brand);
  font-weight: 600;
}
@media (max-width: 720px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
