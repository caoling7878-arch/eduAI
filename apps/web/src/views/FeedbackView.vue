<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'
import { feedbackStatusLabel } from '../lib/labels'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const mine = ref<any[]>([])
const form = reactive({ category: 'general', title: '', body: '' })
const msg = ref('')
const err = ref('')
const loading = ref(false)
const submitting = ref(false)

async function load() {
  if (!auth.isLoggedIn.value) {
    mine.value = []
    return
  }
  loading.value = true
  err.value = ''
  try {
    mine.value = await api('/feedback/me')
  } catch (e) {
    err.value = e instanceof Error ? e.message : '加载反馈失败'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.title.trim() || submitting.value) return
  submitting.value = true
  msg.value = ''
  err.value = ''
  try {
    await api('/feedback', { method: 'POST', body: JSON.stringify(form) })
    msg.value = '反馈已提交，感谢你的建议！'
    form.title = ''
    form.body = ''
    await load()
  } catch (e) {
    err.value = e instanceof Error ? e.message : '提交失败'
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>意见反馈</h1>
    <p class="sub">功能建议、内容纠错或体验问题都可以告诉我们。</p>
    <form class="form" @submit.prevent="submit">
      <select v-model="form.category">
        <option value="general">综合</option>
        <option value="bug">缺陷</option>
        <option value="content">内容</option>
        <option value="ai">AI 相关</option>
      </select>
      <input v-model="form.title" placeholder="标题" required />
      <textarea v-model="form.body" rows="5" placeholder="详细描述" />
      <button type="submit" :disabled="submitting">{{ submitting ? '提交中…' : '提交' }}</button>
    </form>
    <p v-if="msg" class="ok">{{ msg }}</p>
    <p v-if="err" class="err">{{ err }}</p>

    <section v-if="auth.isLoggedIn.value">
      <h2>我的反馈</h2>
      <p v-if="loading" class="muted">加载中…</p>
      <ul v-else-if="mine.length">
        <li v-for="t in mine" :key="t.id">
          <strong>{{ t.title }}</strong>
          <span>{{ feedbackStatusLabel(t.status) }}</span>
          <p>{{ t.body }}</p>
          <p v-if="t.reply" class="reply">回复：{{ t.reply }}</p>
        </li>
      </ul>
      <p v-else class="muted">暂无历史反馈</p>
    </section>
    <p v-else class="muted">
      <RouterLink to="/auth?redirect=/feedback">登录</RouterLink>
      后可查看我的反馈记录。
    </p>
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
}
.sub,
.muted {
  color: var(--muted);
}
.muted a {
  color: var(--brand);
  font-weight: 600;
}
.form {
  display: grid;
  gap: 10px;
  margin: 18px 0;
}
input,
textarea,
select {
  border: 1px solid rgba(15, 107, 92, 0.2);
  border-radius: 10px;
  padding: 10px 12px;
  font: inherit;
}
button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
  justify-self: start;
}
button:disabled {
  opacity: 0.6;
}
.ok {
  color: var(--brand);
}
.err {
  color: #a35;
}
ul {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 10px;
}
li {
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.1);
  border-radius: 12px;
  padding: 12px 14px;
}
li strong {
  margin-right: 8px;
}
li span {
  color: var(--brand);
  font-size: 0.85rem;
}
.reply {
  color: var(--brand-deep);
  background: rgba(15, 107, 92, 0.06);
  padding: 8px 10px;
  border-radius: 8px;
}
</style>
