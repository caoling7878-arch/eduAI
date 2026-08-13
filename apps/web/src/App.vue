<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { openAdminConsole } from './lib/adminEntry'
import { fetchUnreadCount, getToken } from './lib/api'
import { useAuth } from './stores/auth'
import DesktopUpdateButton from './components/DesktopUpdateButton.vue'
import AppVersionBadge from './components/AppVersionBadge.vue'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const sideOpen = ref(false)
const unread = ref(0)

const isGeometryLesson = computed(() => route.name === 'geometry-lesson')
const isHome = computed(() => route.name === 'home')
const isPortal = computed(() => auth.isLoggedIn.value && !isGeometryLesson.value)

function goAdmin() {
  // 教师直达工作台，管理员进仪表盘
  const path = auth.isAdmin.value ? '/' : '/hub'
  openAdminConsole(getToken(), path)
}

async function refreshUnread() {
  if (!auth.isLoggedIn.value) {
    unread.value = 0
    return
  }
  try {
    const r = await fetchUnreadCount()
    unread.value = r.count
  } catch {
    unread.value = 0
  }
}

const navGroups = computed(() => [
  {
    title: '学习中心',
    items: [
      { to: '/classroom', label: 'AI 课堂' },
      { to: '/ai', label: 'AI 学伴' },
      { to: '/catalog', label: '课程中心' },
      { to: '/courses/love-words', label: '我爱背单词' },
      { to: '/courses/math-calc', label: '小学数学计算专项' },
      { to: '/courses/geometry-lab', label: '几何动图' },
      { to: '/courses/english-coach', label: '英语陪练' },
      { to: '/courses/ai-coding', label: 'AI 编程' },
    ],
  },
  {
    title: '学习资源',
    items: [
      { to: '/ebooks', label: '电子书' },
      { to: '/reading', label: '美文' },
      { to: '/announcements', label: '公告' },
    ],
  },
  {
    title: '我的学习',
    items: [
      { to: '/practice', label: '练习' },
      { to: '/recommend', label: '推荐' },
      { to: '/path', label: '路径' },
      { to: '/wrongbook', label: '错题本' },
      { to: '/learning', label: '学情' },
      {
        to: '/messages',
        label: '消息',
      },
      { to: '/me', label: '个人中心' },
      { to: '/feedback', label: '反馈' },
    ],
  },
])

watch(
  () => route.fullPath,
  () => {
    sideOpen.value = false
    void refreshUnread()
  },
)

watch(
  () => auth.isLoggedIn.value,
  (ok) => {
    if (ok) void refreshUnread()
    else unread.value = 0
  },
)

onMounted(async () => {
  // 管理端退出跳转过来时清掉学员端会话，展示未登录主页
  if (route.query.logout === '1') {
    auth.logout()
    const { logout: _drop, ...rest } = route.query
    await router.replace({ path: '/', query: rest })
  }
  await auth.hydrate()
  void refreshUnread()
})
</script>

<template>
  <!-- 登录后：门户壳（顶栏 + 左侧导航） -->
  <div v-if="isPortal" class="portal" :class="{ 'portal--home': isHome }">
    <header class="portal-top">
      <button class="menu-btn" type="button" aria-label="菜单" @click="sideOpen = !sideOpen">
        ☰
      </button>
      <RouterLink to="/" class="brand-lockup">
        <span class="name">eduAI</span>
        <AppVersionBadge />
        <span class="mark">智慧教育云</span>
      </RouterLink>
      <div class="portal-title">学习门户</div>
      <div class="portal-user">
        <DesktopUpdateButton />
        <button
          v-if="auth.isStaff.value"
          type="button"
          class="admin-link"
          @click="goAdmin"
        >
          {{ auth.isAdmin.value ? '系统管理后台' : '教师工作台' }}
        </button>
        <RouterLink to="/me" class="user-pill">
          <span>{{ auth.state.user?.display_name }}</span>
          <span
            v-if="auth.state.vocab_streak_badge"
            class="streak-badge"
            :title="`连续打卡 ${auth.state.vocab_streak_days} 天`"
          >连</span>
        </RouterLink>
        <button type="button" class="link-btn" @click="auth.logout()">退出</button>
      </div>
    </header>

    <div class="portal-body">
      <div v-if="sideOpen" class="side-mask" @click="sideOpen = false" />
      <aside class="side-nav" :class="{ open: sideOpen }">
        <RouterLink v-slot="{ href, navigate, isExactActive }" to="/" custom>
          <a
            :href="href"
            class="side-home"
            :class="{ 'router-link-active': isExactActive }"
            @click="
              (e) => {
                navigate(e)
                sideOpen = false
              }
            "
          >
            首页
          </a>
        </RouterLink>
        <div v-for="g in navGroups" :key="g.title" class="side-group">
          <p class="side-title">{{ g.title }}</p>
          <RouterLink
            v-for="item in g.items"
            :key="item.to"
            :to="item.to"
            class="side-link"
            @click="sideOpen = false"
          >
            {{ item.label }}
            <i v-if="item.to === '/messages' && unread > 0" class="badge">{{ unread > 99 ? '99+' : unread }}</i>
          </RouterLink>
        </div>
      </aside>

      <main class="portal-main" :class="{ 'portal-main--home': isHome }">
        <RouterView />
      </main>
    </div>
  </div>

  <!-- 未登录 / 几何课页：保留原顶栏布局 -->
  <div
    v-else
    class="shell"
    :class="{ 'shell--lab': isGeometryLesson, 'shell--home': isHome && !auth.isLoggedIn.value }"
  >
    <header class="site-nav" :class="{ 'site-nav--home': isHome && !auth.isLoggedIn.value }">
      <RouterLink to="/" class="brand-lockup">
        <span class="name">eduAI</span>
        <AppVersionBadge />
        <span class="mark">智慧教育云</span>
      </RouterLink>
      <nav class="nav-links">
        <DesktopUpdateButton />
        <RouterLink to="/classroom">AI 课堂</RouterLink>
        <RouterLink to="/ai">AI 学伴</RouterLink>
        <RouterLink to="/catalog">课程中心</RouterLink>
        <RouterLink to="/courses/geometry-lab">几何动图</RouterLink>
        <RouterLink to="/courses/english-coach">英语陪练</RouterLink>
        <RouterLink to="/courses/ai-coding">AI 编程</RouterLink>
        <RouterLink
          v-if="!auth.isLoggedIn.value"
          :to="{ path: '/auth', query: { redirect: route.fullPath === '/' ? undefined : route.fullPath } }"
          class="login-link"
        >
          登录
        </RouterLink>
        <template v-else>
          <RouterLink to="/me" class="user-pill">
            <span>{{ auth.state.user?.display_name }}</span>
            <span
              v-if="auth.state.vocab_streak_badge"
              class="streak-badge"
              :title="`连续打卡 ${auth.state.vocab_streak_days} 天`"
            >连</span>
          </RouterLink>
          <button type="button" class="link-btn" @click="auth.logout()">退出</button>
        </template>
      </nav>
    </header>
    <main
      class="shell-main"
      :class="{
        'shell-main--lab': isGeometryLesson,
        'shell-main--home': isHome && !auth.isLoggedIn.value,
      }"
    >
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.portal {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #eef2f0;
}

.portal-top {
  position: sticky;
  top: 0;
  z-index: 30;
  height: var(--nav-h);
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 3px solid var(--brand);
}

.menu-btn {
  display: none;
  border: 1px solid var(--line);
  background: #fff;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--brand-deep);
}

.portal-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--ink);
  justify-self: center;
}

.portal-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admin-link {
  border: 1px solid rgba(15, 107, 92, 0.35);
  background: rgba(15, 107, 92, 0.08);
  color: var(--brand-deep);
  font-weight: 600;
  font-size: 0.85rem;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
}

.admin-link:hover {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.portal-body {
  flex: 1;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  min-height: calc(100vh - var(--nav-h));
}

.side-nav {
  background: var(--brand);
  color: #fff;
  padding: 18px 0 32px;
  overflow-y: auto;
  position: sticky;
  top: var(--nav-h);
  height: calc(100vh - var(--nav-h));
}

.side-home {
  display: block;
  padding: 10px 22px;
  font-weight: 700;
  font-size: 1rem;
  color: #fff;
}

.side-home.router-link-active {
  background: rgba(255, 255, 255, 0.14);
}

.side-group {
  margin-top: 18px;
}

.side-title {
  margin: 0 22px 8px;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.side-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 22px 7px 30px;
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.88);
  transition: background 0.15s;
}

.side-link .badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e8a317;
  color: #1a1a1a;
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 700;
}

.side-link:hover,
.side-link.router-link-active {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.portal-main {
  min-width: 0;
  padding: 20px 22px 48px;
}

.portal-main--home {
  padding: 0;
}

.side-mask {
  display: none;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-deep);
  font-size: 0.85rem;
  font-weight: 600;
}

.streak-badge {
  display: inline-grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8a317, #d97706);
  color: #fff;
  font-size: 0.68rem;
  font-weight: 800;
  box-shadow: 0 0 0 2px rgba(232, 163, 23, 0.25);
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  padding: 8px 10px;
  border-radius: 999px;
}

.link-btn:hover {
  color: var(--brand-deep);
  background: var(--brand-soft);
}

.login-link {
  padding: 8px 14px !important;
  border-radius: 999px !important;
  background: var(--brand);
  color: white !important;
}

.login-link:hover {
  background: var(--brand-deep) !important;
}

@media (max-width: 960px) {
  .menu-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .portal-top {
    grid-template-columns: auto auto 1fr auto;
  }

  .portal-title {
    display: none;
  }

  .portal-body {
    grid-template-columns: 1fr;
  }

  .side-nav {
    position: fixed;
    left: 0;
    top: var(--nav-h);
    bottom: 0;
    width: min(280px, 82vw);
    z-index: 40;
    transform: translateX(-105%);
    transition: transform 0.22s ease;
  }

  .side-nav.open {
    transform: translateX(0);
  }

  .side-mask {
    display: block;
    position: fixed;
    inset: var(--nav-h) 0 0 0;
    background: rgba(10, 30, 26, 0.35);
    z-index: 35;
  }
}
</style>

<style>
.shell--lab .shell-main--lab {
  width: 100%;
  max-width: none;
  padding: 10px 14px 14px;
  box-sizing: border-box;
}

.shell--home .shell-main--home {
  width: 100%;
  max-width: none;
  padding: 0;
}

.shell--home .site-nav--home {
  padding-left: max(24px, calc((100% - 1120px) / 2));
  padding-right: max(24px, calc((100% - 1120px) / 2));
  background: rgba(243, 246, 244, 0.72);
  border-bottom-color: transparent;
}
</style>
