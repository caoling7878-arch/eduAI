<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { fetchPapers, fetchQuiz, submitPaper, type Paper } from '../lib/api'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const papers = ref<Paper[]>([])
const quiz = ref<{ paper: Paper; questions: any[] } | null>(null)
const answers = reactive<Record<string, string>>({})
const multiPicks = reactive<Record<string, string[]>>({})
const result = ref<{ score: number; total: number; grade_task_ids?: number[] } | null>(null)
const err = ref('')
const submitting = ref(false)
const draftTip = ref('')
let draftTimer: ReturnType<typeof setTimeout> | null = null

function draftKey(paperId: number) {
  return `eduai_practice_draft_${paperId}`
}

function saveDraftLocal() {
  if (!quiz.value || result.value) return
  const paperId = quiz.value.paper.id
  // sync multi picks into answers
  for (const [qid, picks] of Object.entries(multiPicks)) {
    answers[qid] = [...picks].sort((a, b) => Number(a) - Number(b)).join(',')
  }
  try {
    localStorage.setItem(
      draftKey(paperId),
      JSON.stringify({ answers: { ...answers }, savedAt: Date.now() }),
    )
    draftTip.value = '草稿已自动保存'
    setTimeout(() => {
      if (draftTip.value === '草稿已自动保存') draftTip.value = ''
    }, 1500)
  } catch {
    /* ignore quota */
  }
}

function scheduleDraft() {
  if (!quiz.value || result.value) return
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(saveDraftLocal, 800)
}

function restoreDraft(paperId: number) {
  try {
    const raw = localStorage.getItem(draftKey(paperId))
    if (!raw) return false
    const data = JSON.parse(raw) as { answers?: Record<string, string> }
    if (!data.answers) return false
    Object.keys(answers).forEach((k) => delete answers[k])
    Object.keys(multiPicks).forEach((k) => delete multiPicks[k])
    Object.assign(answers, data.answers)
    for (const [qid, val] of Object.entries(data.answers)) {
      const q = quiz.value?.questions.find((x) => String(x.id) === qid)
      if (q?.type === 'multi' && val) {
        multiPicks[qid] = val.split(',').map((s) => s.trim()).filter(Boolean)
      }
    }
    draftTip.value = '已恢复未提交草稿'
    return true
  } catch {
    return false
  }
}

function clearDraft(paperId: number) {
  localStorage.removeItem(draftKey(paperId))
}

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/practice' } })
    return
  }
  const all = await fetchPapers()
  papers.value = all.filter((p) => p.status === 'published')
}

async function open(p: Paper) {
  result.value = null
  err.value = ''
  draftTip.value = ''
  Object.keys(answers).forEach((k) => delete answers[k])
  Object.keys(multiPicks).forEach((k) => delete multiPicks[k])
  quiz.value = await fetchQuiz(p.id)
  for (const q of quiz.value.questions) {
    if (q.type === 'multi') multiPicks[String(q.id)] = multiPicks[String(q.id)] || []
  }
  restoreDraft(p.id)
}

function backToList() {
  if (quiz.value && !result.value) saveDraftLocal()
  quiz.value = null
  result.value = null
}

async function submit() {
  if (!quiz.value || submitting.value) return
  submitting.value = true
  err.value = ''
  try {
    for (const [qid, picks] of Object.entries(multiPicks)) {
      answers[qid] = [...picks].sort((a, b) => Number(a) - Number(b)).join(',')
    }
    const paperId = quiz.value.paper.id
    result.value = await submitPaper(paperId, { ...answers })
    clearDraft(paperId)
    draftTip.value = ''
  } catch (e) {
    err.value = e instanceof Error ? e.message : '提交失败'
  } finally {
    submitting.value = false
  }
}

watch(answers, () => scheduleDraft(), { deep: true })
watch(multiPicks, () => scheduleDraft(), { deep: true })

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>练习与测验</h1>
    <p class="sub">客观题即时批改；主观题进入 AI 初评并等待教师复核，错题自动收入错题本。作答会自动保存草稿。</p>
    <p v-if="err" class="err">{{ err }}</p>
    <p v-else-if="draftTip" class="draft">{{ draftTip }}</p>

    <div v-if="!quiz" class="list">
      <button v-for="p in papers" :key="p.id" type="button" class="paper" @click="open(p)">
        <strong>{{ p.title }}</strong>
        <span>{{ p.question_ids.length }} 题</span>
      </button>
      <p v-if="!papers.length" class="muted">暂无已发布试卷</p>
    </div>

    <div v-else class="quiz">
      <div class="quiz-head">
        <h2>{{ quiz.paper.title }}</h2>
        <button type="button" class="ghost" @click="backToList">返回试卷列表</button>
      </div>
      <article v-for="(q, idx) in quiz.questions" :key="q.id" class="q">
        <h3>
          {{ idx + 1 }}. {{ q.stem }}
          <em v-if="q.type === 'essay' || q.type === 'subjective'">主观题</em>
          <em v-else-if="q.type === 'multi'">多选</em>
        </h3>
        <div v-if="q.type === 'blank'" class="blank">
          <input v-model="answers[String(q.id)]" placeholder="填写答案，多项用逗号分隔" />
        </div>
        <div v-else-if="q.type === 'essay' || q.type === 'subjective'" class="blank">
          <textarea v-model="answers[String(q.id)]" rows="5" placeholder="请写下你的解答…" />
        </div>
        <div v-else-if="q.type === 'multi'" class="opts">
          <label v-for="(opt, oi) in q.options" :key="oi">
            <input v-model="multiPicks[String(q.id)]" type="checkbox" :value="String(oi)" />
            <span>{{ opt }}</span>
          </label>
        </div>
        <div v-else class="opts">
          <label v-for="(opt, oi) in q.options" :key="oi">
            <input v-model="answers[String(q.id)]" type="radio" :value="String(oi)" :name="'q' + q.id" />
            <span>{{ opt }}</span>
          </label>
        </div>
      </article>
      <button type="button" class="submit" :disabled="submitting || !!result" @click="submit">
        {{ submitting ? '提交中…' : result ? '已提交' : '提交批改' }}
      </button>
      <div v-if="result" class="result-box">
        <p class="result">客观题得分：{{ result.score }} / {{ result.total }}</p>
        <p class="muted">主观题请到消息中心查看 AI 初评 / 教师复核；错题已同步错题本。</p>
        <div class="cta">
          <RouterLink to="/messages">消息中心</RouterLink>
          <RouterLink to="/wrongbook">错题本</RouterLink>
          <RouterLink to="/recommend">薄弱推荐</RouterLink>
          <button type="button" class="ghost" @click="backToList">再做一套</button>
        </div>
      </div>
    </div>
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
  margin: 0 0 8px;
}
.sub,
.muted {
  color: var(--muted);
}
.err {
  color: #a35;
}
.draft {
  color: #0f6b5c;
  background: #eef8f4;
  padding: 8px 12px;
  border-radius: 10px;
}
.list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}
.paper {
  display: flex;
  justify-content: space-between;
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  background: #fff;
  cursor: pointer;
  text-align: left;
}
.quiz-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.q {
  margin: 14px 0;
  padding: 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
.q h3 {
  margin: 0 0 12px;
  font-size: 1.05rem;
}
.q h3 em {
  margin-left: 8px;
  font-style: normal;
  font-size: 0.75rem;
  color: var(--brand);
  border: 1px solid rgba(15, 107, 92, 0.3);
  border-radius: 999px;
  padding: 2px 8px;
}
.blank textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 107, 92, 0.2);
  font: inherit;
  resize: vertical;
}
.opts {
  display: grid;
  gap: 8px;
}
.opts label {
  display: flex;
  gap: 8px;
  align-items: center;
}
.blank input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 107, 92, 0.2);
}
.submit {
  margin-top: 8px;
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 12px 20px;
  cursor: pointer;
}
.submit:disabled {
  opacity: 0.55;
  cursor: default;
}
.ghost {
  border: 1px solid rgba(15, 107, 92, 0.25);
  background: transparent;
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
}
.result-box {
  margin-top: 16px;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(180deg, #f3faf7, #fff);
  border: 1px solid rgba(15, 107, 92, 0.12);
}
.result {
  margin: 0 0 8px;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--brand);
}
.cta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
  align-items: center;
}
.cta a {
  color: var(--brand);
  font-weight: 600;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(15, 107, 92, 0.25);
}
</style>
