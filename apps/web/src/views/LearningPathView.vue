<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const path = ref<{ weak_points: string[]; steps: any[]; summary: string } | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/path' } })
    return
  }
  loading.value = true
  error.value = ''
  try {
    path.value = await api('/learning-path/me')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>学习路径</h1>
    <p v-if="loading" class="muted">正在生成今日路径…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <template v-else-if="path">
      <p class="sub">{{ path.summary }}</p>
      <div v-if="path.weak_points.length" class="tags">
        <span v-for="k in path.weak_points" :key="k">{{ k }}</span>
      </div>
      <div v-if="!path.steps.length" class="empty">
        <p>暂无路径步骤，先去巩固薄弱点或背单词吧。</p>
        <div class="cta">
          <RouterLink to="/recommend">薄弱推荐</RouterLink>
          <RouterLink to="/courses/love-words">我爱背单词</RouterLink>
        </div>
      </div>
      <ol v-else>
        <li v-for="(s, i) in path.steps" :key="i">
          <div class="kind">{{ s.kind }}</div>
          <h2>{{ s.title }}</h2>
          <p>{{ s.reason }}</p>
          <RouterLink class="go" :to="s.link">去完成</RouterLink>
        </li>
      </ol>
      <RouterLink class="back" to="/learning">返回学情</RouterLink>
    </template>
  </div>
</template>

<style scoped>
.page {
  width: min(780px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
h1 {
  font-family: 'Noto Serif SC', serif;
}
.sub {
  color: var(--muted);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0;
}
.tags span {
  background: rgba(232, 163, 23, 0.18);
  color: #8a5a00;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.85rem;
}
ol {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 12px;
  counter-reset: step;
}
li {
  background: #fff;
  border-radius: 14px;
  padding: 16px 16px 16px 52px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  position: relative;
  counter-increment: step;
}
li::before {
  content: counter(step);
  position: absolute;
  left: 14px;
  top: 16px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 0.85rem;
  font-weight: 700;
}
.kind {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--brand);
  margin-bottom: 4px;
}
h2 {
  margin: 0 0 6px;
  font-size: 1.05rem;
}
p {
  margin: 0 0 10px;
  color: var(--muted);
}
.go {
  color: var(--brand-deep);
  font-weight: 600;
}
.back {
  display: inline-block;
  margin-top: 20px;
  color: var(--muted);
}
.muted {
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
  margin: 16px 0;
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
</style>
