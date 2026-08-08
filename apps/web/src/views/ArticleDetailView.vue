<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'
import { speakEnglish } from '../lib/speech'

const props = defineProps<{ id: string }>()
const article = ref<any>(null)
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
  article.value = null
  try {
    article.value = await api(`/articles/${props.id}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '美文不存在或已下线'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="page">
    <RouterLink to="/reading">← 返回美文</RouterLink>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <RouterLink to="/reading">返回列表</RouterLink>
    </p>
    <template v-else-if="article">
      <h1>{{ article.title }}</h1>
      <p class="meta">{{ langLabel(article.lang) }} · {{ article.created_at }}</p>
      <article>{{ article.body }}</article>
      <button
        v-if="article.lang === 'en' || article.lang === 'en-US'"
        type="button"
        @click="speakEnglish(article.body)"
      >
        朗读英文
      </button>
    </template>
  </div>
</template>

<style scoped>
.page {
  width: min(720px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 14px 0 6px;
}
.meta {
  color: var(--muted);
}
.err {
  color: #a35;
  margin-top: 14px;
}
.err a {
  margin-left: 10px;
  color: var(--brand);
}
article {
  white-space: pre-wrap;
  line-height: 1.85;
  margin: 18px 0;
  padding: 18px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
}
a {
  color: var(--brand);
}
</style>
