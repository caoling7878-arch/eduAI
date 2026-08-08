<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { fetchChatHealth, fetchCompanions, type ChatHealth, type Companion } from '../lib/chat'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const list = ref<Companion[]>([])
const health = ref<ChatHealth | null>(null)
const err = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  err.value = ''
  try {
    ;[list.value, health.value] = await Promise.all([fetchCompanions(), fetchChatHealth()])
  } catch (e) {
    err.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

function open(c: Companion) {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: `/ai/${c.id}` } })
    return
  }
  router.push(`/ai/${c.id}`)
}
</script>

<template>
  <div class="page">
    <header>
      <p class="eyebrow">AI 学伴</p>
      <h1>和专属助手一起学</h1>
      <p class="sub">
        绑定知识库的流式对话；
        <template v-if="health">
          当前为
          <strong>{{ health.online ? `云端模型（${health.model || health.provider}）` : '本地演示模式' }}</strong>。
        </template>
        <template v-else>未配置大模型时也可本地演示作答。</template>
      </p>
    </header>
    <p v-if="loading" class="hint">加载学伴中…</p>
    <p v-if="err" class="err">
      {{ err }}
      <button type="button" class="retry" @click="load">重试</button>
    </p>
    <div v-else-if="!loading && !list.length" class="empty">
      <p>暂无可用学伴，请联系管理员在后台启用 AI 助手。</p>
    </div>
    <div v-else-if="list.length" class="grid">
      <button v-for="c in list" :key="c.id" type="button" class="card" @click="open(c)">
        <div class="avatar">
          {{ c.avatar || '助' }}
          <i class="dot" :class="{ on: c.online }" />
        </div>
        <div>
          <h2>{{ c.name }}</h2>
          <p>{{ c.persona || '耐心讲解，陪伴练习。' }}</p>
          <small>
            {{ c.online ? c.model : '本地演示' }}
            {{ c.knowledge_base_id ? ' · 已绑知识库' : '' }}
          </small>
          <div v-if="c.suggested_prompts?.length" class="tips">
            <span v-for="p in c.suggested_prompts.slice(0, 2)" :key="p">{{ p }}</span>
          </div>
        </div>
      </button>
    </div>
    <p class="hint">
      管理员可在后台配置模型 Provider、Prompt 与助手人设。
      <RouterLink to="/me">返回个人中心</RouterLink>
    </p>
  </div>
</template>

<style scoped>
.page {
  width: min(960px, 100%);
  margin: 0 auto;
  padding: 28px 20px 64px;
}
.eyebrow {
  margin: 0;
  color: var(--brand);
  font-weight: 600;
  letter-spacing: 0.08em;
  font-size: 0.78rem;
  text-transform: uppercase;
}
h1 {
  margin: 8px 0;
  font-family: 'Noto Serif SC', serif;
  font-size: clamp(1.8rem, 3vw, 2.4rem);
}
.sub,
.hint {
  color: var(--muted);
}
.sub strong {
  color: var(--brand-deep);
  font-weight: 600;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 24px 0;
}
.card {
  display: flex;
  gap: 14px;
  text-align: left;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  background:
    linear-gradient(160deg, rgba(15, 107, 92, 0.06), transparent 50%),
    #fff;
  cursor: pointer;
}
.card:hover {
  border-color: rgba(15, 107, 92, 0.35);
  transform: translateY(-1px);
}
.avatar {
  position: relative;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: var(--brand);
  color: #fff;
  font-weight: 700;
  font-size: 1.2rem;
  flex-shrink: 0;
}
.dot {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #94a3b8;
  border: 2px solid #fff;
}
.dot.on {
  background: #1a8f7a;
}
h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
}
.card p {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 0.92rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
small {
  color: var(--brand);
}
.tips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.tips span {
  font-size: 0.75rem;
  color: var(--muted);
  background: rgba(15, 107, 92, 0.06);
  padding: 3px 8px;
  border-radius: 999px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.err {
  color: #a35;
}
.retry {
  margin-left: 8px;
  border: 0;
  background: none;
  color: var(--brand);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}
.empty {
  padding: 24px;
  border-radius: 14px;
  background: #f7fbfa;
  color: var(--muted);
}
@media (max-width: 720px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
