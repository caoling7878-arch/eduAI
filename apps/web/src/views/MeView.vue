<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  addStudyPlan,
  createOrder,
  deleteMyAccount,
  deleteStudyPlan,
  doCheckin,
  exportMyData,
  fetchAnnouncements,
  fetchCheckin,
  fetchMembershipPlans,
  fetchMyBilling,
  fetchMyOrders,
  fetchStudyPlans,
  toggleStudyPlan,
  type Announcement,
  type CheckinInfo,
  type MembershipPlan,
  type StudyPlan,
} from '../lib/api'
import { courseLabel, courseRoute } from '../lib/courseLabels'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const checkin = ref<CheckinInfo | null>(null)
const plans = ref<StudyPlan[]>([])
const announcements = ref<Announcement[]>([])
const memberships = ref<MembershipPlan[]>([])
const orders = ref<any[]>([])
const billing = ref<Awaited<ReturnType<typeof fetchMyBilling>> | null>(null)
const newPlan = ref('')
const msg = ref('')
const loadError = ref('')
const privacyBusy = ref(false)
const deletePassword = ref('')
const deleteConfirm = ref('')

async function downloadData() {
  privacyBusy.value = true
  msg.value = ''
  try {
    await exportMyData()
    msg.value = '已下载个人数据 JSON'
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '导出失败'
  } finally {
    privacyBusy.value = false
  }
}

async function removeAccount() {
  if (deleteConfirm.value.trim().toUpperCase() !== 'DELETE') {
    msg.value = '请输入 DELETE 确认注销'
    return
  }
  if (!window.confirm('注销后学习数据不可恢复，确定继续？')) return
  privacyBusy.value = true
  msg.value = ''
  try {
    const r = await deleteMyAccount(deletePassword.value, 'DELETE')
    msg.value = r.message
    auth.logout()
    router.push('/')
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '注销失败'
  } finally {
    privacyBusy.value = false
  }
}

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/me' } })
    return
  }
  loadError.value = ''
  try {
    const results = await Promise.allSettled([
      fetchCheckin(),
      fetchStudyPlans(),
      fetchAnnouncements(),
      fetchMembershipPlans(),
      fetchMyOrders(),
      fetchMyBilling(),
    ])
    checkin.value = results[0].status === 'fulfilled' ? results[0].value : null
    plans.value = results[1].status === 'fulfilled' ? results[1].value : []
    announcements.value = results[2].status === 'fulfilled' ? results[2].value : []
    memberships.value = results[3].status === 'fulfilled' ? results[3].value : []
    orders.value = results[4].status === 'fulfilled' ? results[4].value : []
    billing.value = results[5].status === 'fulfilled' ? results[5].value : null
    if (results.some((r) => r.status === 'rejected')) {
      loadError.value = '部分数据加载失败，可刷新重试'
    }
  } catch {
    loadError.value = '加载失败，请稍后重试'
  }
}

async function check() {
  try {
    checkin.value = await doCheckin()
    msg.value = '今日打卡成功'
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '打卡失败'
  }
}

async function add() {
  if (!newPlan.value.trim()) return
  try {
    await addStudyPlan(newPlan.value.trim())
    newPlan.value = ''
    plans.value = await fetchStudyPlans()
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '添加计划失败'
  }
}

async function buy(planId: number) {
  try {
    await createOrder({ plan_id: planId })
    orders.value = await fetchMyOrders()
    msg.value = '已模拟支付成功'
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '开通失败'
  }
}

onMounted(load)
</script>

<template>
  <div class="me">
    <header class="hero">
      <div>
        <p class="eyebrow">个人中心</p>
        <h1>
          {{ auth.state.user?.display_name || '学员' }}
          <span
            v-if="auth.state.vocab_streak_badge"
            class="streak-badge"
            :title="`连续打卡 ${auth.state.vocab_streak_days} 天`"
          >连</span>
        </h1>
        <p class="sub">{{ auth.state.user?.email }}</p>
      </div>
      <div class="actions">
        <RouterLink class="ghost" to="/practice">去练习</RouterLink>
        <RouterLink class="ghost" to="/recommend">薄弱推荐</RouterLink>
        <RouterLink class="ghost" to="/wrongbook">错题本</RouterLink>
        <RouterLink class="ghost" to="/learning">学情</RouterLink>
        <RouterLink class="ghost" to="/messages">消息</RouterLink>
        <RouterLink class="ghost" to="/words">单词</RouterLink>
        <RouterLink class="ghost" to="/reading">美文</RouterLink>
        <RouterLink class="ghost" to="/feedback">反馈</RouterLink>
        <RouterLink class="ghost" to="/announcements">公告</RouterLink>
      </div>
    </header>

    <p v-if="msg" class="toast">{{ msg }}</p>
    <p v-if="loadError" class="toast warn">{{ loadError }}</p>

    <section class="grid">
      <article class="panel checkin">
        <h2>每日打卡</h2>
        <div class="nums" v-if="checkin">
          <div><strong>{{ checkin.streak }}</strong><span>连续天数</span></div>
          <div><strong>{{ checkin.total }}</strong><span>累计打卡</span></div>
        </div>
        <button type="button" :disabled="!checkin || checkin.checked_today" @click="check">
          {{ !checkin ? '加载中…' : checkin.checked_today ? '今日已打卡' : '立即打卡' }}
        </button>
      </article>

      <article class="panel">
        <h2>今日计划</h2>
        <form class="add" @submit.prevent="add">
          <input v-model="newPlan" placeholder="添加一条学习计划" />
          <button type="submit">添加</button>
        </form>
        <ul class="plans">
          <li v-for="p in plans" :key="p.id" :class="{ done: p.done }">
            <button type="button" class="chk" @click="toggleStudyPlan(p.id).then(load)">
              {{ p.done ? '✓' : '○' }}
            </button>
            <span>{{ p.title }}</span>
            <button type="button" class="del" @click="deleteStudyPlan(p.id).then(load)">删</button>
          </li>
          <li v-if="!plans.length" class="muted">暂无计划，添加一条开始今天吧</li>
        </ul>
      </article>

      <article class="panel">
        <h2>学习进度</h2>
        <ul class="progress-list">
          <li v-for="c in auth.state.courses" :key="c.course_id">
            <RouterLink class="cname" :to="courseRoute(c.course_id)">{{ courseLabel(c.course_id) }}</RouterLink>
            <div class="bar"><i :style="{ width: c.percent + '%' }" /></div>
            <em>{{ c.percent }}%</em>
          </li>
          <li v-if="!auth.state.courses.length" class="muted">暂无进度，去课程中心开课吧</li>
        </ul>
      </article>

      <article class="panel">
        <h2>最新公告</h2>
        <ul class="anns">
          <li v-for="a in announcements.slice(0, 3)" :key="a.id">
            <RouterLink :to="`/announcements/${a.id}`">{{ a.title }}</RouterLink>
          </li>
          <li v-if="!announcements.length" class="muted">
            暂无公告 ·
            <RouterLink to="/announcements">查看公告中心</RouterLink>
          </li>
        </ul>
      </article>

      <article class="panel span">
        <h2>会员套餐（模拟下单）</h2>
        <div class="plans-grid">
          <div v-for="m in memberships" :key="m.id" class="mplan">
            <h3>{{ m.name }}</h3>
            <p class="price">¥{{ m.price }} / {{ m.days }} 天</p>
            <p>{{ m.benefits }}</p>
            <button type="button" @click="buy(m.id)">立即开通</button>
          </div>
        </div>
        <h3 class="orders-title">我的订单</h3>
        <ul class="orders">
          <li v-for="o in orders" :key="o.id">
            #{{ o.id }} · ¥{{ o.amount }} · {{ o.status }} · {{ o.created_at }}
          </li>
          <li v-if="!orders.length" class="muted">暂无订单</li>
        </ul>
      </article>

      <article class="panel span privacy">
        <h2>隐私与账号</h2>
        <p class="muted">按合规要求支持导出个人学习数据；注销将删除本账号关联数据（演示种子账号除外）。</p>
        <div class="privacy-actions">
          <button type="button" class="ghost-btn" :disabled="privacyBusy" @click="downloadData">
            导出我的数据
          </button>
        </div>
        <div class="delete-box">
          <h3>注销账号</h3>
          <label>
            密码
            <input v-model="deletePassword" type="password" autocomplete="current-password" />
          </label>
          <label>
            输入 DELETE 确认
            <input v-model="deleteConfirm" type="text" placeholder="DELETE" />
          </label>
          <button type="button" class="danger" :disabled="privacyBusy" @click="removeAccount">
            确认注销
          </button>
        </div>
      </article>

      <article v-if="billing?.tenant" class="panel span">
        <h2>AI 用量（学校配额）</h2>
        <p class="muted">
          所属租户：{{ billing.tenant.name }}
          <template v-if="billing.subscription">
            · 套餐 {{ billing.subscription.pack_name }} · 到期 {{ billing.subscription.ends_at }}
          </template>
        </p>
        <div v-if="billing.subscription" class="usage-bars">
          <div>
            <span
              >Token {{ billing.subscription.tokens_used }} /
              {{ billing.subscription.token_quota }}</span
            >
            <div class="bar">
              <i :style="{ width: Math.min(100, billing.subscription.token_pct) + '%' }" />
            </div>
          </div>
          <div>
            <span
              >调用 {{ billing.subscription.requests_used }} /
              {{ billing.subscription.request_quota }}</span
            >
            <div class="bar">
              <i :style="{ width: Math.min(100, billing.subscription.request_pct) + '%' }" />
            </div>
          </div>
        </div>
        <p v-else class="muted">当前无有效用量包，请联系学校管理员开通。</p>
      </article>
    </section>
  </div>
</template>

<style scoped>
.me {
  width: min(1100px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: end;
  margin-bottom: 22px;
}
.eyebrow {
  margin: 0;
  color: var(--brand);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.78rem;
}
h1 {
  margin: 6px 0 4px;
  font-family: 'Noto Serif SC', serif;
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  display: flex;
  align-items: center;
  gap: 10px;
}
.streak-badge {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8a317, #d97706);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 800;
  font-family: inherit;
}
.sub {
  margin: 0;
  color: var(--muted);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.ghost {
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid rgba(15, 107, 92, 0.25);
  background: #fff;
}
.toast {
  background: rgba(15, 107, 92, 0.1);
  color: var(--brand-deep);
  padding: 10px 14px;
  border-radius: 10px;
}
.toast.warn {
  background: rgba(232, 163, 23, 0.18);
  color: #8a5a00;
}
.cname {
  color: var(--brand-deep);
  font-weight: 600;
  min-width: 0;
}
.muted {
  color: var(--muted);
  list-style: none;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.panel {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(15, 107, 92, 0.1);
  border-radius: 18px;
  padding: 18px;
}
.panel.span {
  grid-column: 1 / -1;
}
.panel h2 {
  margin: 0 0 14px;
  font-size: 1.15rem;
}
.checkin .nums {
  display: flex;
  gap: 24px;
  margin-bottom: 14px;
}
.checkin strong {
  display: block;
  font-size: 2rem;
  color: var(--brand);
}
.checkin span {
  color: var(--muted);
  font-size: 0.85rem;
}
button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
}
button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.add {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.add input {
  flex: 1;
  border: 1px solid rgba(15, 107, 92, 0.2);
  border-radius: 10px;
  padding: 10px 12px;
}
.plans,
.anns,
.progress-list,
.orders {
  list-style: none;
  margin: 0;
  padding: 0;
}
.plans li,
.anns li,
.progress-list li,
.orders li {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(15, 107, 92, 0.08);
}
.plans li.done span {
  text-decoration: line-through;
  color: var(--muted);
}
.chk,
.del {
  background: transparent;
  color: var(--brand);
  padding: 4px 8px;
}
.del {
  margin-left: auto;
  color: #a35;
}
.bar {
  flex: 1;
  height: 8px;
  background: rgba(15, 107, 92, 0.1);
  border-radius: 999px;
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--brand), var(--accent, #e8a317));
}
.plans-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.mplan {
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 14px;
  padding: 14px;
  background: linear-gradient(180deg, #f7fbfa, #fff);
}
.price {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--brand);
}
.orders-title {
  margin: 18px 0 8px;
  font-size: 1rem;
}
.privacy .muted {
  margin-top: 0;
}
.privacy-actions {
  margin: 12px 0 18px;
}
.usage-bars {
  display: grid;
  gap: 12px;
  margin-top: 10px;
}
.usage-bars > div {
  display: grid;
  gap: 6px;
}
.usage-bars span {
  font-size: 0.9rem;
  color: var(--muted);
}
.ghost-btn {
  border: 1px solid rgba(15, 107, 92, 0.3);
  background: #fff;
  color: var(--brand);
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
}
.delete-box {
  display: grid;
  gap: 10px;
  max-width: 360px;
  padding: 14px;
  border-radius: 14px;
  background: #fff7f5;
  border: 1px solid rgba(180, 60, 40, 0.15);
}
.delete-box h3 {
  margin: 0;
  font-size: 1rem;
}
.delete-box label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}
.delete-box input {
  border: 1px solid rgba(15, 107, 92, 0.2);
  border-radius: 10px;
  padding: 10px 12px;
}
.danger {
  background: #b42318;
}
.muted {
  color: var(--muted);
}
@media (max-width: 800px) {
  .grid,
  .plans-grid {
    grid-template-columns: 1fr;
  }
  .hero {
    flex-direction: column;
    align-items: start;
  }
}
</style>
