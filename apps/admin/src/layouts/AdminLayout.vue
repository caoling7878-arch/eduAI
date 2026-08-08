<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataBoard,
  User,
  Avatar,
  Reading,
  OfficeBuilding,
  Document,
  Notebook,
  Bell,
  ShoppingCart,
  Setting,
  Cpu,
  Collection,
  PictureFilled,
  Compass,
  List,
  Key,
  EditPen,
  TrendCharts,
  Files,
  ChatDotRound,
  Link,
  Box,
  Wallet,
  UserFilled,
  Monitor,
} from '@element-plus/icons-vue'
import { fetchMe, setToken, type User as UserT } from '../lib/api'

type MenuItem = { path: string; label: string; icon: unknown }
type MenuGroup = { title: string; items: MenuItem[]; adminOnly?: boolean }

const route = useRoute()
const router = useRouter()
const user = ref<UserT | null>(null)

const isAdmin = computed(() => user.value?.role === 'admin')

const groups = computed(() => {
  const list: MenuGroup[] = []

  if (!isAdmin.value) {
    list.push({
      title: '总览',
      items: [
        { path: '/hub', label: '教师工作台', icon: Monitor },
        { path: '/', label: '数据概览', icon: DataBoard },
      ],
    })
  } else {
    list.push({
      title: '总览',
      items: [{ path: '/', label: '仪表盘', icon: DataBoard }],
    })
  }

  if (isAdmin.value) {
    list.push({
      title: '学员运营',
      items: [
        { path: '/students', label: '学员管理', icon: UserFilled },
        { path: '/orders', label: '订单会员', icon: ShoppingCart },
        { path: '/billing', label: '租户用量包', icon: Wallet },
        { path: '/reports', label: '学情报表', icon: TrendCharts },
        { path: '/feedback', label: '反馈工单', icon: ChatDotRound },
      ],
    })
  }

  list.push({
    title: '教学组织',
    items: [
      ...(isAdmin.value ? [{ path: '/teachers', label: '教师管理', icon: Avatar }] : []),
      { path: '/classes', label: '班级管理', icon: OfficeBuilding },
      { path: '/courses', label: '课程管理', icon: Reading },
      ...(!isAdmin.value
        ? [
            { path: '/reports', label: '学情报表', icon: TrendCharts },
            { path: '/feedback', label: '反馈工单', icon: ChatDotRound },
          ]
        : []),
    ],
  })

  list.push({
    title: '内容测评',
    items: [
      { path: '/questions', label: '题库管理', icon: Document },
      { path: '/papers', label: '试卷管理', icon: Notebook },
      { path: '/grading', label: '批改复核', icon: EditPen },
      { path: '/workflows', label: '工作流编排', icon: List },
      { path: '/templates', label: '模板库', icon: Files },
      { path: '/ebooks', label: '电子书', icon: Reading },
      { path: '/articles', label: '每日美文', icon: Notebook },
      { path: '/announcements', label: '公告管理', icon: Bell },
      { path: '/geometry', label: '几何实验室', icon: Compass },
    ],
  })

  list.push({
    title: 'AI 中枢',
    items: isAdmin.value
      ? [
          { path: '/assistants', label: 'AI 教学助手', icon: Cpu },
          { path: '/ai-config', label: 'AI Token / API Key', icon: Key },
          { path: '/knowledge', label: '知识库', icon: Collection },
          { path: '/ppt', label: 'PPT 生成', icon: PictureFilled },
          { path: '/api-tokens', label: '开放 API', icon: Link },
          { path: '/datasets', label: '样本回流', icon: Box },
        ]
      : [
          { path: '/assistants', label: 'AI 教学助手', icon: Cpu },
          { path: '/knowledge', label: '知识库', icon: Collection },
          { path: '/ppt', label: 'PPT 生成', icon: PictureFilled },
        ],
  })

  if (isAdmin.value) {
    list.push({
      title: '系统',
      items: [
        { path: '/users', label: '账号管理', icon: User },
        { path: '/audits', label: '审计日志', icon: List },
        { path: '/settings', label: '系统设置', icon: Setting },
      ],
    })
  }

  return list
})

const flatMenus = computed(() => groups.value.flatMap((g) => g.items))

const active = computed(() => route.path)

const pageTitle = computed(
  () => flatMenus.value.find((m) => m.path === active.value)?.label || '管理',
)

onMounted(async () => {
  try {
    user.value = await fetchMe()
    if (user.value.role !== 'admin' && user.value.role !== 'teacher') {
      setToken(null)
      router.replace('/login')
      return
    }
    if (user.value.role === 'teacher' && route.meta.adminOnly) {
      router.replace('/hub')
    } else if (user.value.role === 'teacher' && route.path === '/') {
      // 教师默认进入简化工作台（直接打开 / 时）
      router.replace('/hub')
    }
  } catch {
    setToken(null)
    router.replace('/login')
  }
})

watch(
  () => route.fullPath,
  () => {
    if (user.value?.role === 'teacher' && route.meta.adminOnly) {
      router.replace('/hub')
    }
  },
)

function logout() {
  setToken(null)
  // 退出后台后回到学员端未登录主页（:5173），不要留在管理端登录页
  const web =
    (import.meta.env.VITE_WEB_URL as string | undefined)?.replace(/\/$/, '') ||
    'http://127.0.0.1:5173'
  window.location.href = `${web}/?logout=1`
}
</script>

<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="logo brand-serif">eduAI</div>
        <p class="logo-sub">{{ isAdmin ? '系统管理后台' : '教师工作台' }}</p>
      </div>

      <nav class="nav">
        <div v-for="g in groups" :key="g.title" class="group">
          <p class="group-title">{{ g.title }}</p>
          <RouterLink
            v-for="m in g.items"
            :key="m.path"
            :to="m.path"
            class="nav-item"
            :class="{ active: active === m.path }"
          >
            <el-icon><component :is="m.icon" /></el-icon>
            <span>{{ m.label }}</span>
          </RouterLink>
        </div>
      </nav>

      <a class="front-link" href="http://127.0.0.1:5173/" target="_blank" rel="noopener">
        <el-icon><Monitor /></el-icon>
        返回前台
      </a>
    </aside>

    <main class="main">
      <header class="top">
        <div>
          <p class="crumb">{{ isAdmin ? '系统管理员' : '教师' }} / {{ pageTitle }}</p>
          <h1 class="brand-serif">{{ pageTitle }}</h1>
        </div>
        <div class="top-right">
          <span class="role-tag">{{ user?.display_name }} · {{ user?.role }}</span>
          <el-button text type="primary" @click="logout">退出</el-button>
        </div>
      </header>
      <section class="content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 248px 1fr;
  min-height: 100vh;
  background: #eef2f0;
}
.side {
  background: #fff;
  border-right: 1px solid rgba(15, 107, 92, 0.1);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
}
.brand {
  padding: 20px 18px 8px;
  border-bottom: 1px solid rgba(15, 107, 92, 0.08);
}
.logo {
  font-size: 26px;
  font-weight: 700;
  color: var(--edu-teal);
}
.logo-sub {
  margin: 2px 0 0;
  color: var(--edu-muted);
  font-size: 12px;
}
.nav {
  flex: 1;
  overflow-y: auto;
  padding: 10px 10px 16px;
}
.group {
  margin-bottom: 12px;
}
.group-title {
  margin: 8px 10px 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #8a9a94;
  text-transform: uppercase;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 10px;
  color: #3d4f49;
  font-size: 13.5px;
  margin-bottom: 2px;
  transition: background 0.15s, color 0.15s;
}
.nav-item:hover {
  background: rgba(15, 107, 92, 0.08);
  color: var(--edu-teal);
}
.nav-item.active {
  background: linear-gradient(120deg, #0f6b5c, #1a8f7a);
  color: #fff;
  box-shadow: 0 8px 18px rgba(15, 107, 92, 0.22);
}
.front-link {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 12px 16px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px dashed rgba(15, 107, 92, 0.3);
  color: var(--edu-teal);
  font-size: 13px;
  font-weight: 600;
}
.front-link:hover {
  background: rgba(15, 107, 92, 0.06);
}
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 28px 6px;
  background: transparent;
}
.crumb {
  margin: 0 0 2px;
  color: var(--edu-muted);
  font-size: 12px;
}
.top h1 {
  margin: 0;
  font-size: 24px;
  color: #14302a;
}
.top-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.role-tag {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.1);
  color: var(--edu-teal);
  font-size: 13px;
  font-weight: 600;
}
.content {
  padding: 8px 28px 28px;
  min-width: 0;
  overflow-x: hidden;
}
@media (max-width: 960px) {
  .shell {
    grid-template-columns: 1fr;
  }
  .side {
    display: none;
  }
}
</style>
