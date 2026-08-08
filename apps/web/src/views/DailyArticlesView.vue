<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'

const rows = ref<any[]>([])
const loading = ref(false)
const error = ref('')

function langLabel(lang: string) {
  if (lang === 'zh' || lang === 'zh-CN') return '中文'
  if (lang === 'en' || lang === 'en-US') return 'English'
  return lang || '其他'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await api('/articles?published_only=true')
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
    <h1>每日美文</h1>
    <p class="sub">中英短文精选，适合碎片阅读。</p>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <ul v-else-if="rows.length">
      <li v-for="a in rows" :key="a.id">
        <RouterLink :to="`/reading/${a.id}`">
          <span class="lang">{{ langLabel(a.lang) }}</span>
          <h2>{{ a.title }}</h2>
          <p>{{ a.summary }}</p>
        </RouterLink>
      </li>
    </ul>
    <p v-else class="muted">暂无已发布美文</p>
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
ul {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 12px;
}
li a {
  display: block;
  padding: 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
}
.lang {
  color: var(--brand);
  font-size: 0.8rem;
}
h2 {
  margin: 6px 0;
  font-size: 1.15rem;
}
p {
  margin: 0;
  color: var(--muted);
}
</style>
