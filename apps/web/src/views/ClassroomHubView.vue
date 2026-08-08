<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { classroomCatalog, sceneMeta, type SceneType } from '../data/classroom'
import { orchestrateClassroom } from '../lib/classroomOrchestrator'
import { useAuth } from '../stores/auth'

const router = useRouter()
const auth = useAuth()
const topic = ref('30 分钟搞懂勾股定理')
const busy = ref(false)
const error = ref('')

const pillars: { type: SceneType; desc: string }[] = [
  { type: 'slide', desc: '建立概念与关键例子' },
  { type: 'quiz', desc: '即时反馈，暴露盲点' },
  { type: 'sim', desc: '交互试错，内化原理' },
  { type: 'pbl', desc: '角色协作，交付作品' },
]

async function generate() {
  error.value = ''
  busy.value = true
  try {
    const lesson = await orchestrateClassroom(topic.value)
    sessionStorage.setItem(`classroom:${lesson.id}`, JSON.stringify(lesson))
    await auth.track('classroom', lesson.id, 'started', { title: lesson.title })
    await router.push(`/classroom/${lesson.id}`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '成课失败'
  } finally {
    busy.value = false
  }
}

function openDemo(id: string) {
  void auth.track('classroom', id, 'started')
  void router.push(`/classroom/${id}`)
}
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/">← 返回首页</RouterLink>
    <p class="eyebrow">AI多智能体互动课堂</p>
    <h1 class="page-title">把任何主题或文档变成一场沉浸式课堂</h1>
    <p class="lead">
      AI 统筹编排：<strong>幻灯讲解</strong>、<strong>测验检验</strong>、<strong>模拟动手</strong>、
      <strong>PBL 创造</strong>——从听到会，再到做出东西。
    </p>

    <div class="pillars">
      <article v-for="p in pillars" :key="p.type" class="pillar panel">
        <span class="dot" :style="{ background: sceneMeta[p.type].color }" />
        <h3>{{ sceneMeta[p.type].label }}</h3>
        <p>{{ p.desc }}</p>
        <em>{{ sceneMeta[p.type].verb }}</em>
      </article>
    </div>

    <section class="compose panel">
      <h2>一句话成课</h2>
      <p>输入主题，AI 编排四场景大纲并进入课堂（未配置大模型时使用本地编排模板）。</p>
      <div class="row">
        <input v-model="topic" type="text" placeholder="例如：光合作用入门 / 英语过去时" />
        <button class="btn btn-primary" type="button" :disabled="busy || !topic.trim()" @click="generate">
          {{ busy ? '编排中…' : '生成并开课' }}
        </button>
      </div>
      <p v-if="error" class="err">{{ error }}</p>
    </section>

    <section class="catalog">
      <h2>精选课堂</h2>
      <button
        v-for="c in classroomCatalog"
        :key="c.id"
        type="button"
        class="item panel"
        @click="openDemo(c.id)"
      >
        <div>
          <span class="tag">{{ c.tag }}</span>
          <h3>{{ c.title }}</h3>
          <p>{{ c.topic }} · 约 {{ c.durationMin }} 分钟 · {{ c.scenes.length }} 个场景</p>
          <small>{{ c.orchestrationNote }}</small>
        </div>
        <span class="go">进入课堂 →</span>
      </button>
    </section>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  color: var(--muted);
  margin-bottom: 18px;
  font-size: 0.92rem;
}

.pillars {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 28px 0;
}

.pillar {
  padding: 18px 16px;
  position: relative;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: block;
  margin-bottom: 10px;
}

.pillar h3 {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 1.15rem;
}

.pillar p {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
}

.pillar em {
  display: block;
  margin-top: 12px;
  font-style: normal;
  font-weight: 700;
  color: var(--brand);
}

.compose {
  padding: 22px;
  margin-bottom: 28px;
}

.compose h2,
.catalog h2 {
  margin: 0 0 8px;
  font-family: var(--font-display);
}

.compose > p {
  margin: 0 0 14px;
  color: var(--muted);
}

.row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

input {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  font: inherit;
}

.err {
  color: #b42318;
  margin: 10px 0 0;
}

.catalog {
  display: grid;
  gap: 12px;
}

.item {
  width: 100%;
  text-align: left;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 18px 20px;
  cursor: pointer;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.75);
}

.item:hover {
  border-color: rgba(15, 107, 92, 0.35);
  transform: translateX(3px);
}

.tag {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--brand-deep);
  background: var(--brand-soft);
  padding: 2px 8px;
  border-radius: 6px;
}

.item h3 {
  margin: 8px 0 4px;
  font-family: var(--font-display);
}

.item p {
  margin: 0;
  color: var(--muted);
}

.item small {
  display: block;
  margin-top: 8px;
  color: var(--muted);
  line-height: 1.45;
}

.go {
  flex-shrink: 0;
  color: var(--brand);
  font-weight: 600;
}

@media (max-width: 900px) {
  .pillars {
    grid-template-columns: 1fr 1fr;
  }
  .row {
    grid-template-columns: 1fr;
  }
}
</style>
