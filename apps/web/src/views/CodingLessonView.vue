<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { codingLessons } from '../data/courses'
import { useAuth } from '../stores/auth'

const props = defineProps<{ lessonId: string }>()
const auth = useAuth()

const lesson = computed(() => codingLessons.find((l) => l.id === props.lessonId))
const code = ref('')
const output = ref('')
const ran = ref(false)
const markedDone = ref(false)

const lessonIndex = computed(() =>
  lesson.value ? codingLessons.findIndex((l) => l.id === lesson.value!.id) : -1,
)
const prev = computed(() =>
  lessonIndex.value > 0 ? codingLessons[lessonIndex.value - 1] : null,
)
const next = computed(() =>
  lessonIndex.value >= 0 && lessonIndex.value < codingLessons.length - 1
    ? codingLessons[lessonIndex.value + 1]
    : null,
)

function reset() {
  if (lesson.value) {
    code.value = lesson.value.starterCode
    output.value = ''
    ran.value = false
    markedDone.value = auth.isCompleted('ai-coding', lesson.value.id)
    void auth.track('ai-coding', lesson.value.id, 'started', { title: lesson.value.title })
  }
}

watch(
  () => props.lessonId,
  () => reset(),
  { immediate: true },
)

async function run() {
  const logs: string[] = []
  const fakeConsole = {
    log: (...args: unknown[]) => {
      logs.push(args.map(String).join(' '))
    },
  }
  try {
    const fn = new Function('console', code.value)
    fn(fakeConsole)
    output.value = logs.join('\n') || '（程序已运行，无输出）'
    // 运行成功只记「已开始」，不自动标完成，避免未对照检查点就 100%
    if (lesson.value) {
      await auth.track('ai-coding', lesson.value.id, 'started', {
        title: lesson.value.title,
        ran: true,
      })
    }
  } catch (err) {
    output.value = `出错了：${err instanceof Error ? err.message : String(err)}`
  }
  ran.value = true
}

async function markComplete() {
  if (!lesson.value) return
  await auth.track(
    'ai-coding',
    lesson.value.id,
    'completed',
    { title: lesson.value.title, checkpoint: true },
    100,
  )
  markedDone.value = true
}
</script>

<template>
  <div v-if="lesson" class="page fade-up">
    <RouterLink class="back" to="/courses/ai-coding">← 课程目录</RouterLink>
    <div class="title-row">
      <div>
        <p class="eyebrow">第 {{ lesson.index }} 课 · 约 {{ lesson.minutes }} 分钟</p>
        <h1 class="page-title">{{ lesson.title }}</h1>
      </div>
      <div class="nav-btns">
        <RouterLink v-if="prev" class="btn btn-ghost" :to="`/courses/ai-coding/${prev.id}`">
          上一课
        </RouterLink>
        <RouterLink v-if="next" class="btn btn-primary" :to="`/courses/ai-coding/${next.id}`">
          下一课
        </RouterLink>
      </div>
    </div>

    <div class="grid">
      <article class="panel teach">
        <h2>今天学什么</h2>
        <p>{{ lesson.concept }}</p>
        <div class="callout">
          <strong>通关检查</strong>
          <span>{{ lesson.checkpoint }}</span>
        </div>
        <div class="hint">
          <strong>试一试</strong>
          <span>{{ lesson.hint }}</span>
        </div>
      </article>

      <section class="panel studio">
        <div class="studio-head">
          <h2>练习场</h2>
          <div class="actions">
            <button class="btn btn-ghost" type="button" @click="reset">重置代码</button>
            <button class="btn btn-accent" type="button" @click="run">运行</button>
          </div>
        </div>
        <textarea v-model="code" class="editor" spellcheck="false" />
        <div class="out">
          <div class="out-label">输出</div>
          <pre>{{ output || '点击「运行」查看结果' }}</pre>
        </div>
        <p v-if="ran" class="ok">已运行。对照左侧检查点，确认达标后再标记完成。</p>
        <div class="done-row">
          <button
            v-if="!markedDone"
            class="btn btn-primary"
            type="button"
            :disabled="!auth.isLoggedIn.value"
            @click="markComplete"
          >
            {{ auth.isLoggedIn.value ? '我已完成检查点' : '登录后可标记完成' }}
          </button>
          <p v-else class="ok">本课已标记完成 ✓</p>
        </div>
      </section>
    </div>
  </div>
  <div v-else class="page">
    <p>未找到该课时。</p>
    <RouterLink to="/courses/ai-coding">返回目录</RouterLink>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  color: var(--muted);
  margin-bottom: 18px;
  font-size: 0.92rem;
}

.title-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.nav-btns {
  display: flex;
  gap: 8px;
}

.grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 16px;
}

.teach,
.studio {
  padding: 20px;
}

h2 {
  margin: 0 0 12px;
  font-size: 1rem;
  color: var(--brand-deep);
}

.teach p {
  margin: 0 0 16px;
  line-height: 1.7;
  color: var(--ink);
}

.callout,
.hint {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 12px;
  margin-bottom: 10px;
}

.callout {
  background: var(--brand-soft);
}

.hint {
  background: var(--accent-soft);
}

.studio-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.actions {
  display: flex;
  gap: 8px;
}

.editor {
  width: 100%;
  min-height: 280px;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88rem;
  line-height: 1.5;
  background: #14212b;
  color: #e7eef5;
  resize: vertical;
}

.out {
  margin-top: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: #f7faf8;
}

.out-label {
  padding: 8px 12px;
  font-size: 0.78rem;
  color: var(--muted);
  border-bottom: 1px solid var(--line);
}

.out pre {
  margin: 0;
  padding: 12px;
  min-height: 88px;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.86rem;
}

.ok {
  margin: 10px 0 0;
  color: var(--brand);
  font-size: 0.9rem;
}
.done-row {
  margin-top: 12px;
}
.done-row .btn:disabled {
  opacity: 0.55;
  cursor: default;
}

@media (max-width: 900px) {
  .grid,
  .title-row {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
