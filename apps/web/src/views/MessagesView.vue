<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  fetchMyGrades,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../lib/api'
import { gradeStatusLabel } from '../lib/labels'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const notes = ref<any[]>([])
const grades = ref<any[]>([])

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/messages' } })
    return
  }
  ;[notes.value, grades.value] = await Promise.all([fetchNotifications(), fetchMyGrades()])
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header>
      <h1>消息中心</h1>
      <button type="button" @click="markAllNotificationsRead().then(load)">全部已读</button>
    </header>

    <section>
      <h2>通知</h2>
      <ul>
        <li
          v-for="n in notes"
          :key="n.id"
          :class="{ unread: !n.read }"
          role="button"
          tabindex="0"
          @click="markNotificationRead(n.id).then(load)"
          @keydown.enter.prevent="markNotificationRead(n.id).then(load)"
          @keydown.space.prevent="markNotificationRead(n.id).then(load)"
        >
          <strong>{{ n.title }}</strong>
          <p>{{ n.body }}</p>
          <RouterLink v-if="n.link" :to="n.link" @click.stop>查看</RouterLink>
        </li>
      </ul>
      <p v-if="!notes.length" class="muted">暂无通知</p>
    </section>

    <section>
      <h2>主观题批改</h2>
      <ul>
        <li v-for="g in grades" :key="g.id">
          <strong
            >{{ gradeStatusLabel(g.status) }} ·
            {{
              g.status === 'teacher_reviewed' || g.teacher_score != null
                ? `${g.teacher_score ?? g.ai_score ?? '-'}/${g.max_score}`
                : `${g.ai_score ?? '-'}/${g.max_score}（AI）`
            }}</strong
          >
          <p>{{ g.stem }}</p>
          <p class="fb">{{ g.teacher_feedback || g.ai_feedback || '等待评阅' }}</p>
        </li>
      </ul>
      <p v-if="!grades.length" class="muted">
        暂无主观题记录 ·
        <RouterLink to="/practice">去做练习</RouterLink>
      </p>
    </section>
  </div>
</template>

<style scoped>
.page {
  width: min(820px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 0;
}
h2 {
  margin: 24px 0 12px;
  font-size: 1.1rem;
}
button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}
li {
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.1);
  border-radius: 14px;
  padding: 14px;
}
li.unread {
  border-color: rgba(232, 163, 23, 0.55);
  background: linear-gradient(180deg, rgba(232, 163, 23, 0.08), #fff);
}
li[role='button'] {
  cursor: pointer;
}
li[role='button']:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
p {
  margin: 6px 0;
  color: var(--muted);
}
.fb {
  white-space: pre-wrap;
}
.muted {
  color: var(--muted);
}
a {
  color: var(--brand);
}
</style>
