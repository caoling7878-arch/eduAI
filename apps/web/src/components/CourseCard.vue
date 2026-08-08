<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { CourseMeta } from '../data/courses'
import CourseCover from './CourseCover.vue'
import ProgressBar from './ProgressBar.vue'

defineProps<{
  course: CourseMeta
  delay?: number
  percent?: number
  loggedIn?: boolean
}>()
</script>

<template>
  <RouterLink
    :to="course.route"
    class="card fade-up"
    :style="{ animationDelay: `${delay ?? 0}ms` }"
  >
    <CourseCover :tone="course.coverTone" :title="course.tag" />
    <div class="body">
      <div class="meta">
        <span>{{ course.audience }}</span>
        <span>{{ course.lessons }} 课节</span>
        <span>{{ course.duration }}</span>
      </div>
      <h3>{{ course.title }}</h3>
      <p>{{ course.subtitle }}</p>
      <ul>
        <li v-for="item in course.highlights" :key="item">{{ item }}</li>
      </ul>
      <ProgressBar
        v-if="loggedIn"
        class="progress"
        :percent="percent ?? 0"
        :label="`${course.title} 进度`"
      />
      <span class="cta">{{ (percent ?? 0) > 0 ? '继续学习 →' : '开始学习 →' }}</span>
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  display: block;
  overflow: hidden;
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 48px rgba(20, 33, 43, 0.12);
}

.body {
  padding: 18px 20px 22px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: var(--muted);
  font-size: 0.8rem;
  margin-bottom: 8px;
}

h3 {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 1.35rem;
}

p {
  margin: 0 0 12px;
  color: var(--muted);
  line-height: 1.55;
  font-size: 0.95rem;
}

ul {
  margin: 0 0 16px;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

li {
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-deep);
}

.progress {
  margin-bottom: 12px;
}

.cta {
  color: var(--brand);
  font-weight: 600;
  font-size: 0.95rem;
}
</style>
