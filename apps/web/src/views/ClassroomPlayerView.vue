<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import SlideSceneView from '../components/classroom/SlideSceneView.vue'
import QuizSceneView from '../components/classroom/QuizSceneView.vue'
import SimSceneView from '../components/classroom/SimSceneView.vue'
import PblSceneView from '../components/classroom/PblSceneView.vue'
import {
  classroomCatalog,
  sceneMeta,
  type ClassroomLesson,
  type SceneType,
} from '../data/classroom'
import { useAuth } from '../stores/auth'

const props = defineProps<{ classroomId: string }>()
const auth = useAuth()

const index = ref(0)
const doneIds = ref<Set<string>>(new Set())
const peerLine = ref('')

const lesson = computed<ClassroomLesson | null>(() => {
  const cached = sessionStorage.getItem(`classroom:${props.classroomId}`)
  if (cached) {
    try {
      return JSON.parse(cached) as ClassroomLesson
    } catch {
      /* ignore */
    }
  }
  return classroomCatalog.find((c) => c.id === props.classroomId) ?? null
})

const scene = computed(() => lesson.value?.scenes[index.value] ?? null)
const teacher = computed(
  () => lesson.value?.agents.find((a) => a.role === 'teacher')?.name || '林老师',
)
const peer = computed(() => lesson.value?.agents.find((a) => a.role === 'peer'))
const progress = computed(() => {
  if (!lesson.value?.scenes.length) return 0
  return Math.round((doneIds.value.size / lesson.value.scenes.length) * 100)
})

const peerTips: Record<SceneType, string> = {
  slide: '这一页我先记关键词，你听讲解时也可以默念一遍定义。',
  quiz: '别怕错——错题解释往往比直接选对更有用。',
  sim: '动手时慢慢转模型，把「直线」和「平面」指给自己看。',
  pbl: '我们可以分工：你写定义，我来想例子？',
}

watch(
  () => props.classroomId,
  () => {
    index.value = 0
    doneIds.value = new Set()
  },
)

watch(
  scene,
  (s) => {
    if (!s) return
    peerLine.value = peerTips[s.type]
  },
  { immediate: true },
)

function markDone() {
  if (!scene.value || !lesson.value) return
  const next = new Set(doneIds.value)
  next.add(scene.value.id)
  doneIds.value = next
  const completed = next.size >= lesson.value.scenes.length
  void auth.track(
    'classroom',
    lesson.value.id,
    completed ? 'completed' : 'started',
    {
      title: lesson.value.title,
      scene: scene.value.id,
      done: next.size,
      total: lesson.value.scenes.length,
    },
    completed ? 100 : Math.round((next.size / lesson.value.scenes.length) * 100),
  )
}

function go(delta: number) {
  if (!lesson.value) return
  index.value = Math.max(0, Math.min(lesson.value.scenes.length - 1, index.value + delta))
}

function jump(i: number) {
  index.value = i
}
</script>

<template>
  <div v-if="lesson && scene" class="player fade-up">
    <aside class="rail panel">
      <RouterLink class="back" to="/classroom">← 课堂大厅</RouterLink>
      <h1>{{ lesson.title }}</h1>
      <p class="note">{{ lesson.orchestrationNote }}</p>
      <div class="bar">
        <div class="fill" :style="{ width: `${progress}%` }" />
      </div>
      <p class="pct">进度 {{ progress }}%</p>

      <ol>
        <li
          v-for="(s, i) in lesson.scenes"
          :key="s.id"
          :class="{ active: i === index, done: doneIds.has(s.id) }"
        >
          <button type="button" @click="jump(i)">
            <span class="type">{{ sceneMeta[s.type].label }}</span>
            <strong>{{ s.title }}</strong>
          </button>
        </li>
      </ol>

      <div class="agents">
        <div v-for="a in lesson.agents" :key="a.id" class="agent">
          <b>{{ a.name }}</b>
          <small>{{ a.persona }}</small>
        </div>
      </div>
    </aside>

    <section class="stage">
      <div class="peer" v-if="peer">
        <i />
        <p><strong>{{ peer.name }}：</strong>{{ peerLine }}</p>
      </div>

      <div class="scene-body panel">
        <SlideSceneView
          v-if="scene.type === 'slide'"
          :scene="scene"
          :teacher-name="teacher"
          @done="markDone"
        />
        <QuizSceneView v-else-if="scene.type === 'quiz'" :scene="scene" @done="markDone" />
        <SimSceneView v-else-if="scene.type === 'sim'" :scene="scene" @done="markDone" />
        <PblSceneView v-else-if="scene.type === 'pbl'" :scene="scene" @done="markDone" />
      </div>

      <div class="nav">
        <button class="btn btn-ghost" type="button" :disabled="index === 0" @click="go(-1)">
          上一场景
        </button>
        <span>{{ index + 1 }} / {{ lesson.scenes.length }}</span>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="index >= lesson.scenes.length - 1"
          @click="go(1)"
        >
          下一场景
        </button>
      </div>
    </section>
  </div>
  <div v-else class="player">
    <p>未找到该课堂。</p>
    <RouterLink to="/classroom">返回课堂大厅</RouterLink>
  </div>
</template>

<style scoped>
.player {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 14px;
  min-height: calc(100vh - var(--nav-h) - 48px);
}

.rail {
  padding: 16px;
  align-self: start;
  position: sticky;
  top: calc(var(--nav-h) + 12px);
  max-height: calc(100vh - var(--nav-h) - 24px);
  overflow: auto;
}

.back {
  color: var(--muted);
  font-size: 0.88rem;
}

h1 {
  margin: 12px 0 8px;
  font-family: var(--font-display);
  font-size: 1.25rem;
  line-height: 1.35;
}

.note {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

.bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.12);
  overflow: hidden;
}

.fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand), #1a8f7a);
  transition: width 0.3s ease;
}

.pct {
  margin: 6px 0 14px;
  font-size: 0.8rem;
  color: var(--muted);
}

ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

li button {
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
  display: grid;
  gap: 2px;
}

li.active button,
li button:hover {
  background: var(--brand-soft);
  border-color: rgba(15, 107, 92, 0.2);
}

li.done .type::after {
  content: ' ✓';
}

.type {
  font-size: 0.72rem;
  color: var(--brand);
  font-weight: 700;
}

li strong {
  font-size: 0.9rem;
  font-weight: 600;
}

.agents {
  margin-top: 16px;
  display: grid;
  gap: 8px;
}

.agent {
  padding: 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--line);
}

.agent b {
  display: block;
  margin-bottom: 2px;
}

.agent small {
  color: var(--muted);
  line-height: 1.4;
}

.stage {
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 12px;
  min-height: 0;
}

.peer {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--accent-soft);
}

.peer i {
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
  animation: pulseDot 1.8s ease-in-out infinite;
}

.peer p {
  margin: 0;
  line-height: 1.5;
  font-size: 0.92rem;
}

.scene-body {
  padding: 20px;
  min-height: 520px;
}

.nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 960px) {
  .player {
    grid-template-columns: 1fr;
  }
  .rail {
    position: static;
    max-height: none;
  }
}
</style>
