<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchEbooks } from '../lib/api'

const rows = ref<any[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchEbooks()
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
    <h1>电子书</h1>
    <p class="sub">精选读物，随时开读。</p>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <template v-else>
      <div v-if="rows.length" class="grid">
        <RouterLink v-for="b in rows" :key="b.id" :to="`/ebooks/${b.id}`" class="card">
          <h2>{{ b.title }}</h2>
          <p>{{ b.summary }}</p>
          <small>{{ b.chapters?.length || 0 }} 章</small>
        </RouterLink>
      </div>
      <p v-else class="muted">暂无已发布电子书</p>
    </template>
  </div>
</template>

<style scoped>
.page {
  width: min(900px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 0 0 6px;
}
.sub,
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
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-top: 20px;
}
.card {
  display: block;
  padding: 18px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
}
h2 {
  margin: 0 0 8px;
  font-size: 1.15rem;
}
p {
  margin: 0 0 10px;
  color: var(--muted);
}
small {
  color: var(--brand);
}
@media (max-width: 720px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
