<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchCatalogCourses } from '../lib/api'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const rows = ref<any[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchCatalogCourses()
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
    <h1>课程中心</h1>
    <p class="sub">来自平台发布的正式课程，学完可同步进度{{ auth.isLoggedIn.value ? '' : '（登录后记录）' }}。</p>
    <p v-if="loading" class="sub">加载中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <div v-else class="list">
      <RouterLink v-for="c in rows" :key="c.id" class="card" :to="`/catalog/${c.id}`">
        <h2>{{ c.title }}</h2>
        <p>{{ c.summary || '暂无简介' }}</p>
        <small>
          {{ c.price_type === 'public' ? '公开' : `¥${c.price}` }} ·
          {{ c.chapters?.length || 0 }} 章 · {{ c.student_count || 0 }} 人在学
        </small>
      </RouterLink>
      <p v-if="!rows.length" class="sub">暂无已发布课程，请稍后再来。</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  width: min(900px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
h1 {
  font-family: var(--font-display);
  margin: 0 0 6px;
}
.sub {
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
.list {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}
.card {
  display: block;
  padding: 16px 18px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
  color: inherit;
}
.card:hover {
  border-color: rgba(15, 107, 92, 0.35);
}
h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
  font-family: var(--font-display);
}
p {
  margin: 0 0 8px;
  color: var(--muted);
  line-height: 1.5;
}
small {
  color: var(--brand-deep);
  font-weight: 600;
}
</style>
