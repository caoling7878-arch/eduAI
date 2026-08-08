<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ApiError, setToken } from '../lib/api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuth()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const busy = ref(false)
const bridging = ref(false)

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) return
  bridging.value = true
  try {
    setToken(token)
    await auth.hydrate()
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/'
    await router.replace(redirect)
  } catch {
    setToken(null)
    error.value = 'LTI 登录凭证无效，请重新从 LMS 进入'
  } finally {
    bridging.value = false
  }
})

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(email.value.trim(), password.value)
    } else {
      await auth.register(
        email.value.trim(),
        password.value,
        displayName.value.trim() || email.value.split('@')[0] || '学员',
      )
    }
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/'
    await router.replace(redirect)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '操作失败，请稍后重试'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/">← 返回首页</RouterLink>
    <div class="panel card">
      <p class="eyebrow">账号</p>
      <h1 class="page-title">{{ bridging ? '正在进入…' : mode === 'login' ? '登录' : '注册' }}</h1>
      <p v-if="bridging" class="lead">正在完成 LMS / LTI 单点登录，请稍候。</p>
      <template v-else>
        <p class="lead">
          登录后同步学习进度。管理员或教师进入后台，请登录后在顶栏点击「系统管理后台 / 教师工作台」。
        </p>

        <form class="form" @submit.prevent="submit">
          <label v-if="mode === 'register'">
            <span>昵称</span>
            <input v-model="displayName" type="text" placeholder="例如：小林" autocomplete="nickname" />
          </label>
          <label>
            <span>邮箱</span>
            <input v-model="email" type="email" required placeholder="you@school.com" autocomplete="email" />
          </label>
          <label>
            <span>密码</span>
            <input
              v-model="password"
              type="password"
              required
              minlength="6"
              placeholder="至少 6 位"
              autocomplete="current-password"
            />
          </label>
          <p v-if="error" class="error">{{ error }}</p>
          <button class="btn btn-primary" type="submit" :disabled="busy">
            {{ busy ? '请稍候…' : mode === 'login' ? '登录' : '创建账号' }}
          </button>
        </form>

        <p class="switch">
          <template v-if="mode === 'login'">
            还没有账号？
            <button type="button" class="link" @click="mode = 'register'">去注册</button>
          </template>
          <template v-else>
            已有账号？
            <button type="button" class="link" @click="mode = 'login'">去登录</button>
          </template>
        </p>
      </template>
      <p v-if="error && bridging" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  width: min(480px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.back {
  color: var(--muted);
  font-size: 0.92rem;
}
.panel {
  margin-top: 18px;
  padding: 28px 24px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(15, 107, 92, 0.12);
  box-shadow: var(--shadow);
}
.lead {
  color: var(--muted);
  line-height: 1.55;
}
.lead strong {
  color: var(--brand-deep);
}
.form {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}
label {
  display: grid;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}
input {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  font: inherit;
}
.error {
  color: #b42318;
  margin: 0;
}
.switch {
  margin-top: 16px;
  color: var(--muted);
  font-size: 0.92rem;
}
.link {
  border: 0;
  background: transparent;
  color: var(--brand);
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
</style>
