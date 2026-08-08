<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAnnouncements, type Announcement } from '../lib/api'

const rows = ref<Announcement[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchAnnouncements()
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
    <h1>平台公告</h1>
    <p class="sub">学习活动、功能更新与打卡挑战都会在这里发布。</p>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <ul v-else-if="rows.length">
      <li v-for="a in rows" :key="a.id">
        <RouterLink :to="`/announcements/${a.id}`">
          <h2>{{ a.title }}</h2>
          <p>{{ a.body.slice(0, 90) }}{{ a.body.length > 90 ? '…' : '' }}</p>
          <small>浏览 {{ a.views }}</small>
        </RouterLink>
      </li>
    </ul>
    <p v-else class="muted">暂无公告</p>
  </div>
</template>

<style scoped>
.page {
  width: min(820px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 0 0 8px;
}
.sub {
  color: var(--muted);
  margin-bottom: 22px;
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
ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}
li a {
  display: block;
  padding: 18px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
h2 {
  margin: 0 0 8px;
  font-size: 1.2rem;
}
p {
  margin: 0 0 8px;
  color: var(--muted);
}
small {
  color: var(--brand);
}
</style>
