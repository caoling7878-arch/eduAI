<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import ProgressBar from '../components/ProgressBar.vue'
import { codingLessons, hotCourses } from '../data/courses'
import { useAuth } from '../stores/auth'

const course = hotCourses.find((c) => c.id === 'ai-coding')!
const auth = useAuth()
const percent = computed(() => auth.coursePercent('ai-coding'))
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/">← 返回首页</RouterLink>
    <p class="eyebrow">{{ course.tag }} · {{ course.audience }}</p>
    <h1 class="page-title">{{ course.title }}</h1>
    <p class="lead">
      {{ course.subtitle }}。每课含概念讲解、可运行练习与通关检查点，浏览器内即可完成。
    </p>
    <ProgressBar
      v-if="auth.isLoggedIn.value"
      class="course-progress"
      :percent="percent"
      label="编程课进度"
    />
    <p v-else class="login-hint">
      <RouterLink to="/auth?redirect=/courses/ai-coding">登录</RouterLink>
      后可记录学习进度与完成状态。
    </p>

    <ol class="path">
      <li
        v-for="lesson in codingLessons"
        :key="lesson.id"
        class="panel"
        :class="{ done: auth.isCompleted('ai-coding', lesson.id) }"
      >
        <div class="idx">{{ String(lesson.index).padStart(2, '0') }}</div>
        <div class="body">
          <h3>
            {{ lesson.title }}
            <small v-if="auth.isCompleted('ai-coding', lesson.id)">已完成</small>
          </h3>
          <p>{{ lesson.summary }}</p>
          <span class="mins">约 {{ lesson.minutes }} 分钟</span>
        </div>
        <RouterLink class="btn btn-primary" :to="`/courses/ai-coding/${lesson.id}`">
          {{ auth.isCompleted('ai-coding', lesson.id) ? '复习' : '开始' }}
        </RouterLink>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  color: var(--muted);
  margin-bottom: 18px;
  font-size: 0.92rem;
}

.course-progress {
  max-width: 320px;
  margin-top: 12px;
}
.login-hint {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 0.92rem;
}
.login-hint a {
  color: var(--brand);
  font-weight: 600;
}

.path {
  list-style: none;
  margin: 28px 0 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 16px 18px;
}

li.done .idx {
  background: var(--brand);
}

.idx {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #243642;
  color: white;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

h3 {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 1.2rem;
}

h3 small {
  margin-left: 8px;
  font-family: var(--font-body);
  font-size: 0.75rem;
  color: var(--brand);
  font-weight: 600;
}

p {
  margin: 0 0 6px;
  color: var(--muted);
}

.mins {
  font-size: 0.8rem;
  color: var(--brand);
  font-weight: 600;
}

@media (max-width: 720px) {
  li {
    grid-template-columns: auto 1fr;
  }

  .btn {
    grid-column: 1 / -1;
  }
}
</style>
