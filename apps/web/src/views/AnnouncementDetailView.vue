<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAnnouncement, type Announcement } from '../lib/api'

const props = defineProps<{ id: string }>()
const item = ref<Announcement | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  item.value = null
  try {
    item.value = await fetchAnnouncement(Number(props.id))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '公告不存在或已下线'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="page">
    <RouterLink to="/announcements" class="back">← 返回公告</RouterLink>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="error" class="err">
      {{ error }}
      <RouterLink to="/announcements">返回列表</RouterLink>
    </p>
    <template v-else-if="item">
      <h1>{{ item.title }}</h1>
      <p class="meta">浏览 {{ item.views }} · {{ item.created_at }}</p>
      <article>{{ item.body }}</article>
    </template>
  </div>
</template>

<style scoped>
.page {
  width: min(760px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.back {
  color: var(--brand);
}
.muted {
  color: var(--muted);
}
.err {
  color: #a35;
  margin-top: 16px;
}
.err a {
  margin-left: 10px;
  color: var(--brand);
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 16px 0 8px;
}
.meta {
  color: var(--muted);
}
article {
  white-space: pre-wrap;
  line-height: 1.8;
  margin-top: 20px;
  padding: 20px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
</style>
