<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchMe, login, setToken } from '../lib/api'
import { webBaseUrl } from '../lib/webEntry'
import DesktopUpdateButton from '../components/DesktopUpdateButton.vue'
import AppVersionBadge from '../components/AppVersionBadge.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({
  email: 'admin@edu.ai',
  password: 'admin123',
})

async function enterAsStaff(token: string) {
  setToken(token)
  const me = await fetchMe()
  if (me.role !== 'admin' && me.role !== 'teacher') {
    setToken(null)
    throw new Error('当前账号无权进入管理后台')
  }
  const redirect = (route.query.redirect as string) || ''
  if (redirect.startsWith('/') && !redirect.startsWith('//')) {
    await router.replace(redirect)
    return
  }
  await router.replace(me.role === 'teacher' ? '/hub' : '/')
}

async function acceptHandoff() {
  const handoff = typeof route.query.handoff === 'string' ? route.query.handoff : ''
  if (!handoff) return
  loading.value = true
  try {
    await enterAsStaff(handoff)
    ElMessage.success('已从学习门户同步登录')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '同步登录失败，请重新登录')
  } finally {
    loading.value = false
  }
}

async function submit() {
  loading.value = true
  try {
    const { access_token } = await login(form.email, form.password)
    await enterAsStaff(access_token)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void acceptHandoff()
})
</script>

<template>
  <div class="login">
    <form class="card" @submit.prevent="submit">
      <h1 class="brand-serif">eduAI <AppVersionBadge /></h1>
      <p>系统管理后台登录</p>
      <el-input v-model="form.email" placeholder="邮箱" size="large" />
      <el-input v-model="form.password" type="password" show-password placeholder="密码" size="large" />
      <el-button type="primary" size="large" native-type="submit" :loading="loading" style="width: 100%">
        进入后台
      </el-button>
      <small>系统管理员：admin@edu.ai / admin123 · 教师：teacher@edu.ai / teacher123</small>
      <small class="hint">学员端登录页：{{ webBaseUrl() }}/auth（登录后不会自动跳转至此）。</small>
      <a class="back" :href="`${webBaseUrl()}/`">← 返回学员端首页</a>
      <div class="upd-wrap">
        <DesktopUpdateButton />
      </div>
    </form>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background:
    linear-gradient(135deg, rgba(15, 107, 92, 0.92), rgba(17, 79, 70, 0.95)),
    radial-gradient(circle at 20% 20%, rgba(232, 163, 23, 0.35), transparent 40%);
}
.back {
  display: block;
  margin-top: 4px;
  color: var(--el-color-primary);
  text-align: center;
  font-size: 13px;
}
.card {
  width: min(400px, 92vw);
  background: #fff;
  border-radius: 18px;
  padding: 32px;
  display: grid;
  gap: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18);
}
h1 {
  margin: 0;
  font-size: 34px;
  color: var(--edu-teal);
}
p {
  margin: -6px 0 4px;
  color: var(--edu-muted);
}
small {
  color: var(--edu-muted);
}
.hint {
  display: block;
  line-height: 1.45;
}
.upd-wrap {
  display: flex;
  justify-content: center;
}
</style>
