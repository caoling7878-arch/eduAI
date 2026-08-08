<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import ProgressBar from '../components/ProgressBar.vue'
import { geometryLessons, hotCourses } from '../data/courses'
import { useAuth } from '../stores/auth'

const course = hotCourses.find((c) => c.id === 'geometry-lab')!
const auth = useAuth()
const filter = ref<'all' | 'solid' | 'analytic' | 'chem'>('all')

const lessons = computed(() =>
  filter.value === 'all'
    ? geometryLessons
    : geometryLessons.filter((l) => l.category === filter.value),
)

const percent = computed(() => auth.coursePercent('geometry-lab'))

function badge(cat: string) {
  if (cat === 'solid') return '3D'
  if (cat === 'analytic') return '2D'
  return 'Chem'
}
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/">← 返回首页</RouterLink>
    <p class="eyebrow">{{ course.tag }} · {{ course.audience }}</p>
    <h1 class="page-title">{{ course.title }}</h1>
    <p class="lead">{{ course.subtitle }}。基于开源 edulab，答案与动画同源精确计算。</p>

    <div class="cta-row">
      <RouterLink class="vision-cta tutor" to="/courses/geometry-lab/tutor">对话讲解 →</RouterLink>
      <RouterLink class="vision-cta ghost" to="/courses/geometry-lab/vision">图片读题 →</RouterLink>
    </div>

    <ProgressBar
      v-if="auth.isLoggedIn.value"
      class="course-progress"
      :percent="percent"
      label="几何实验室进度"
    />
    <p v-else class="hint">
      <RouterLink to="/auth?redirect=/courses/geometry-lab">登录</RouterLink> 后打开课页会自动记录进度。
    </p>

    <div class="toolbar">
      <button
        v-for="item in [
          { id: 'all', label: '全部' },
          { id: 'solid', label: '立体几何' },
          { id: 'analytic', label: '解析几何' },
          { id: 'chem', label: '化学微观' },
        ]"
        :key="item.id"
        type="button"
        class="chip"
        :class="{ active: filter === item.id }"
        @click="filter = item.id as typeof filter"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="list">
      <RouterLink
        v-for="lesson in lessons"
        :key="lesson.id"
        class="item panel"
        :class="{ done: auth.isCompleted('geometry-lab', lesson.id) }"
        :to="`/courses/geometry-lab/${lesson.id}`"
      >
        <div>
          <span class="badge" :data-cat="lesson.category">{{ badge(lesson.category) }}</span>
          <h3>
            {{ lesson.title }}
            <small v-if="auth.isCompleted('geometry-lab', lesson.id)">已学</small>
          </h3>
          <p>{{ lesson.blurb }}</p>
        </div>
        <span class="go">打开课页 →</span>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  color: var(--muted);
  margin-bottom: 18px;
  font-size: 0.92rem;
}

.cta-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.vision-cta {
  display: inline-flex;
  align-items: center;
  padding: 10px 16px;
  border-radius: 999px;
  background: linear-gradient(120deg, #0f6b5c, #1a8f7a);
  color: #fff;
  font-weight: 600;
  font-size: 0.92rem;
}

.vision-cta.ghost {
  background: transparent;
  color: var(--brand);
  border: 1px solid rgba(15, 107, 92, 0.35);
}

.course-progress {
  max-width: 320px;
  margin-top: 12px;
}

.hint {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.92rem;
}

.hint a {
  color: var(--brand);
  font-weight: 600;
}

.toolbar {
  display: flex;
  gap: 8px;
  margin: 28px 0 18px;
  flex-wrap: wrap;
}

.chip {
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
  color: var(--muted);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}

.chip.active {
  background: var(--brand);
  border-color: var(--brand);
  color: white;
}

.list {
  display: grid;
  gap: 12px;
}

.item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  text-decoration: none;
  color: inherit;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.72);
  transition: border-color 0.2s, transform 0.2s;
}

.item:hover {
  border-color: rgba(15, 107, 92, 0.35);
  transform: translateY(-1px);
}

.item.done {
  border-color: rgba(15, 107, 92, 0.28);
}

.badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(15, 107, 92, 0.12);
  color: var(--brand-deep);
  margin-bottom: 6px;
}

.badge[data-cat='analytic'] {
  background: rgba(232, 163, 23, 0.18);
  color: #8a5a00;
}

.badge[data-cat='chem'] {
  background: rgba(20, 90, 120, 0.12);
  color: #145a78;
}

h3 {
  margin: 0 0 4px;
  font-size: 1.05rem;
}

h3 small {
  margin-left: 8px;
  color: var(--brand);
  font-weight: 600;
  font-size: 0.8rem;
}

.item p {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.go {
  color: var(--brand);
  white-space: nowrap;
  font-weight: 600;
}
</style>
