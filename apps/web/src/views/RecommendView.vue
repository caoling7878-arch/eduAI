<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const route = useRoute()
const data = ref<{ weak_points: string[]; questions: any[] } | null>(null)
const answers = reactive<Record<number, string>>({})
const checks = reactive<Record<number, { correct: boolean; analysis: string; synced_wrongbook?: boolean }>>({})
const done = ref(0)
const fromPush = ref(false)
const loading = ref(false)
const error = ref('')
const checking = ref<number | null>(null)

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: route.fullPath } })
    return
  }
  loading.value = true
  error.value = ''
  try {
    const ids = typeof route.query.ids === 'string' ? route.query.ids : ''
    fromPush.value = route.query.from === 'push' || !!ids
    const qs = ids ? `?limit=10&ids=${encodeURIComponent(ids)}` : '?limit=10'
    data.value = await api(`/practice/recommend${qs}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function check(qid: number) {
  if (checking.value === qid) return
  checking.value = qid
  try {
    const r = await api<{ correct: boolean; analysis: string; synced_wrongbook?: boolean }>(
      '/labs/practice/check',
      {
        method: 'POST',
        body: JSON.stringify({ question_id: qid, answer: answers[qid] || '' }),
      },
    )
    checks[qid] = r
    done.value = data.value?.questions.filter((q) => checks[q.id]?.correct).length || 0
  } catch (e) {
    checks[qid] = {
      correct: false,
      analysis: e instanceof Error ? e.message : '核对失败，请稍后重试',
    }
  } finally {
    checking.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ fromPush ? '推送练习题单' : '薄弱点练习推送' }}</h1>
    <p class="sub">
      {{ fromPush ? '来自教师/系统推送的巩固题，作答会同步错题本。' : '根据错题本知识点自动推荐巩固题，答错写入错题本，答对标记掌握。' }}
    </p>
    <p v-if="loading" class="muted">加载推荐题中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <template v-else-if="data">
      <div v-if="data.weak_points.length" class="tags">
        <span v-for="k in data.weak_points" :key="k">{{ k }}</span>
      </div>
      <p v-else class="muted">{{ fromPush ? '本题单按推送题目加载。' : '暂无明显薄弱点，先为你准备基础巩固题。' }}</p>
      <p v-if="data.questions.length" class="progress">已答对 {{ done }} / {{ data.questions.length }}</p>
      <div v-if="!data.questions.length" class="empty">
        <p>暂时没有可推荐的题目。</p>
        <div class="cta">
          <RouterLink to="/practice">去做试卷</RouterLink>
          <RouterLink to="/wrongbook">看错题本</RouterLink>
        </div>
      </div>
      <ul v-else>
        <li v-for="q in data.questions" :key="q.id">
          <div class="reason">{{ q.reason }}</div>
          <h2>{{ q.stem }}</h2>
          <small>{{ q.type }} · {{ q.knowledge_points }} · 难度 {{ q.difficulty }}</small>
          <div v-if="q.options?.length" class="opts">
            <label v-for="(opt, idx) in q.options" :key="idx">
              <input v-model="answers[q.id]" type="radio" :value="String(idx)" />
              {{ opt }}
            </label>
          </div>
          <input v-else v-model="answers[q.id]" class="blank" placeholder="填写答案" />
          <button type="button" class="check" :disabled="checking === q.id" @click="check(q.id)">
            {{ checking === q.id ? '核对中…' : '核对' }}
          </button>
          <p v-if="checks[q.id]" class="verdict" :class="{ ok: checks[q.id].correct }">
            {{ checks[q.id].correct ? '正确' : '再想想' }} · {{ checks[q.id].analysis }}
            <template v-if="checks[q.id].synced_wrongbook"> · 已同步错题本</template>
          </p>
        </li>
      </ul>
      <RouterLink class="go" to="/path">查看学习路径</RouterLink>
      <RouterLink class="go ghost" to="/practice">去试卷练习</RouterLink>
      <RouterLink class="go ghost" to="/wrongbook">查看错题本</RouterLink>
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
}
.sub,
.muted {
  color: var(--muted);
}
.progress {
  color: var(--brand-deep);
  font-weight: 600;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0;
}
.tags span {
  background: rgba(15, 107, 92, 0.1);
  color: var(--brand-deep);
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.85rem;
}
ul {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 12px;
}
li {
  background: #fff;
  border-radius: 14px;
  padding: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
}
.reason {
  color: var(--brand);
  font-size: 0.85rem;
  margin-bottom: 6px;
}
h2 {
  margin: 0 0 8px;
  font-size: 1.05rem;
}
small {
  color: var(--muted);
}
.opts {
  display: grid;
  gap: 6px;
  margin: 10px 0;
}
.check {
  margin-top: 8px;
  background: var(--brand);
  color: #fff;
  border: 0;
  border-radius: 10px;
  padding: 8px 14px;
  cursor: pointer;
}
.verdict {
  margin: 8px 0 0;
  color: #b45309;
}
.verdict.ok {
  color: var(--brand-deep);
}
.blank {
  display: block;
  width: 100%;
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 107, 92, 0.2);
}
.go {
  display: inline-block;
  margin: 18px 12px 0 0;
  color: var(--brand-deep);
  font-weight: 600;
}
.go.ghost {
  font-weight: 500;
  color: var(--muted);
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
.empty {
  margin: 18px 0;
  padding: 16px;
  border-radius: 14px;
  background: #f7fbfa;
}
.cta {
  display: flex;
  gap: 14px;
  margin-top: 10px;
}
.cta a {
  color: var(--brand);
  font-weight: 600;
}
.check:disabled {
  opacity: 0.6;
}
</style>
