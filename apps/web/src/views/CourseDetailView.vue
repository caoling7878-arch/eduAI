<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { useAuth } from '../stores/auth'

const props = defineProps<{ id: string }>()
const auth = useAuth()
const router = useRouter()
const course = ref<any>(null)
const activeLesson = ref<any>(null)
const msg = ref('')

const lessons = computed(() => {
  const list: any[] = []
  for (const ch of course.value?.chapters || []) {
    for (const les of ch.lessons || []) {
      list.push({ ...les, chapter: ch.title })
    }
  }
  return list
})

async function load() {
  course.value = await api(`/courses/${props.id}`)
  activeLesson.value = lessons.value[0] || null
}

async function completeLesson() {
  if (!activeLesson.value || !auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: `/catalog/${props.id}` } })
    return
  }
  await auth.track(`course-${props.id}`, String(activeLesson.value.id), 'completed', {
    title: activeLesson.value.title,
  }, 100)
  msg.value = `已记录「${activeLesson.value.title}」完成`
}

onMounted(load)
</script>

<template>
  <div class="page" v-if="course">
    <RouterLink class="back" to="/catalog">← 课程中心</RouterLink>
    <h1>{{ course.title }}</h1>
    <p class="sub">{{ course.summary }}</p>
    <div class="layout">
      <aside>
        <button
          v-for="les in lessons"
          :key="les.id"
          type="button"
          class="les"
          :class="{ on: activeLesson?.id === les.id }"
          @click="activeLesson = les"
        >
          <small>{{ les.chapter }}</small>
          {{ les.title }}
        </button>
      </aside>
      <article v-if="activeLesson">
        <h2>{{ activeLesson.title }}</h2>
        <p class="meta">类型：{{ activeLesson.content_type }}</p>
        <div v-if="activeLesson.content_type === 'interactive_lab'" class="lab">
          <p>交互实验课页：</p>
          <RouterLink :to="`/courses/geometry-lab/${activeLesson.content}`">
            打开几何课页 {{ activeLesson.content }} →
          </RouterLink>
        </div>
        <div v-else class="body" v-html="(activeLesson.content || '暂无正文').replace(/\n/g, '<br/>')" />
        <button type="button" class="btn btn-primary" @click="completeLesson">标记学完</button>
        <p v-if="msg" class="ok">{{ msg }}</p>
      </article>
    </div>
  </div>
</template>

<style scoped>
.page {
  width: min(1000px, 100%);
  margin: 0 auto;
  padding: 24px 20px 60px;
}
.back {
  color: var(--muted);
}
h1 {
  font-family: var(--font-display);
  margin: 12px 0 6px;
}
.sub,
.meta {
  color: var(--muted);
}
.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
  margin-top: 18px;
}
aside {
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  padding: 10px;
  max-height: 70vh;
  overflow: auto;
}
.les {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 4px;
}
.les small {
  display: block;
  color: var(--muted);
  font-size: 0.75rem;
}
.les.on {
  background: rgba(15, 107, 92, 0.1);
  color: var(--brand-deep);
}
article {
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  padding: 18px;
}
.body {
  line-height: 1.7;
  margin: 12px 0 18px;
  white-space: pre-wrap;
}
.lab {
  margin: 12px 0 18px;
  padding: 12px;
  background: rgba(15, 107, 92, 0.06);
  border-radius: 10px;
}
.lab a {
  color: var(--brand);
  font-weight: 600;
}
.ok {
  color: var(--brand-deep);
  margin-top: 10px;
}
@media (max-width: 800px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
