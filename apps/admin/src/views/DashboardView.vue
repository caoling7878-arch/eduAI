<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchDashboard, fetchMe, type Dashboard, type User } from '../lib/api'

const router = useRouter()
const data = ref<Dashboard | null>(null)
const me = ref<User | null>(null)
const isAdmin = computed(() => me.value?.role === 'admin')

onMounted(async () => {
  ;[data.value, me.value] = await Promise.all([fetchDashboard(), fetchMe()])
})

function fmtHours(mins: number) {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h}h ${m}m`
}

const cards = computed(() => {
  if (!data.value) return []
  const d = data.value
  if (!isAdmin.value) {
    return [
      { key: 'courses', label: '课程总数', value: d.courses, tip: `班级 ${d.classes}`, tone: 'blue', to: '/courses' },
      { key: 'classes', label: '我的班级', value: d.classes, tip: '任教班级', tone: 'teal', to: '/classes' },
      { key: 'active', label: '今日打卡', value: d.checkins_today, tip: '当日活跃', tone: 'green', to: '/reports' },
      { key: 'grade', label: '待批改', value: d.grade_pending ?? 0, tip: '主观题队列', tone: 'amber', to: '/grading' },
      { key: 'feedback', label: '待处理反馈', value: d.feedback_open ?? 0, tip: '工单', tone: 'rose', to: '/feedback' },
      {
        key: 'learn',
        label: '平台学习时长',
        value: fmtHours(d.learning_minutes_30d ?? 0),
        tip: '近 30 天估算',
        tone: 'mint',
        to: '/reports',
      },
    ]
  }
  return [
    { key: 'users', label: '用户总数', value: d.users, tip: `学员 ${d.students}`, tone: 'teal', to: '/users' },
    { key: 'courses', label: '课程总数', value: d.courses, tip: `班级 ${d.classes}`, tone: 'blue', to: '/courses' },
    { key: 'members', label: '付费会员', value: d.active_members ?? 0, tip: '有已支付订单', tone: 'amber', to: '/students' },
    { key: 'active', label: '今日打卡', value: d.checkins_today, tip: '当日活跃', tone: 'green', to: '/reports' },
    { key: 'orders', label: '今日订单', value: d.orders_today ?? 0, tip: `累计订单 ${d.orders}`, tone: 'orange', to: '/orders' },
    {
      key: 'revenue',
      label: '今日营收',
      value: `¥${(d.revenue_today ?? 0).toFixed(2)}`,
      tip: `累计 ¥${(d.revenue_total ?? 0).toFixed(2)}`,
      tone: 'cyan',
      to: '/orders',
    },
    {
      key: 'quota',
      label: '配额告警租户',
      value: d.quota_alert_count ?? 0,
      tip: `最高占用 ${d.token_pct_max ?? 0}% · 租户 ${d.tenant_count ?? 0}`,
      tone: 'rose',
      to: '/billing',
    },
    { key: 'feedback', label: '待处理反馈', value: d.feedback_open ?? 0, tip: '工单', tone: 'rose', to: '/feedback' },
    {
      key: 'learn',
      label: '平台学习时长',
      value: fmtHours(d.learning_minutes_30d ?? 0),
      tip: '近 30 天估算',
      tone: 'mint',
      to: '/reports',
    },
  ]
})

const dist = computed(() => {
  const a = data.value?.activity_dist || {}
  const items = [
    { label: '课程学习', value: a.course_watch || 0, color: '#0f6b5c' },
    { label: '打卡', value: a.checkin || 0, color: '#e8a317' },
    { label: '作业提交', value: a.submission || 0, color: '#2a8fbd' },
    { label: '单词学习', value: a.vocab || 0, color: '#5b8c5a' },
  ]
  const total = items.reduce((s, i) => s + i.value, 0) || 1
  return { items, total, slices: items.map((i) => ({ ...i, pct: (i.value / total) * 100 })) }
})

const donutStyle = computed(() => {
  let acc = 0
  const parts = dist.value.slices.map((s) => {
    const start = acc
    acc += s.pct
    return `${s.color} ${start}% ${acc}%`
  })
  return { background: `conic-gradient(${parts.join(',')})` }
})

function barHeights(series: Array<{ count?: number; amount?: number }> | undefined, key: 'count' | 'amount' = 'count') {
  const rows = series || []
  const vals = rows.map((r) => Number(key === 'amount' ? r.amount || 0 : r.count || 0))
  const max = Math.max(...vals, 1)
  return vals.map((v) => Math.max(4, Math.round((v / max) * 100)))
}

const checkinBars = computed(() => barHeights(data.value?.checkin_trend))
const growthBars = computed(() => barHeights(data.value?.user_growth))
const orderBars = computed(() => barHeights(data.value?.order_trend, 'amount'))
</script>

<template>
  <div v-if="data" class="dash">
    <div class="cards">
      <button
        v-for="c in cards"
        :key="c.key"
        type="button"
        class="card"
        :class="c.tone"
        @click="router.push(c.to)"
      >
        <div class="card-top">
          <span class="label">{{ c.label }}</span>
        </div>
        <div class="value">{{ c.value }}</div>
        <div class="tip">{{ c.tip }}</div>
      </button>
    </div>

    <div class="charts">
      <el-card shadow="never" class="panel">
        <template #header>活跃打卡趋势（近 30 天）</template>
        <div class="bars">
          <div v-for="(h, i) in checkinBars" :key="i" class="bar-wrap" :title="String(data.checkin_trend?.[i]?.day)">
            <div class="bar" :style="{ height: h + '%' }" />
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="panel">
        <template #header>学习行为分布</template>
        <div class="dist">
          <div class="donut" :style="donutStyle">
            <div class="donut-hole">
              <b>{{ dist.total > 999 ? (dist.total / 1000).toFixed(1) + 'k' : dist.total }}</b>
              <span>总计</span>
            </div>
          </div>
          <ul>
            <li v-for="s in dist.slices" :key="s.label">
              <i :style="{ background: s.color }" />
              <span>{{ s.label }}</span>
              <strong>{{ s.value }}</strong>
            </li>
          </ul>
        </div>
      </el-card>

      <el-card v-if="isAdmin" shadow="never" class="panel">
        <template #header>用户增长（近 30 天）</template>
        <div class="bars blue">
          <div v-for="(h, i) in growthBars" :key="i" class="bar-wrap">
            <div class="bar" :style="{ height: h + '%' }" />
          </div>
        </div>
      </el-card>

      <el-card v-if="isAdmin" shadow="never" class="panel">
        <template #header>营收趋势（近 30 天）</template>
        <div class="bars amber">
          <div v-for="(h, i) in orderBars" :key="i" class="bar-wrap">
            <div class="bar" :style="{ height: h + '%' }" />
          </div>
        </div>
      </el-card>
    </div>

    <div class="ranks">
      <el-card shadow="never">
        <template #header>活跃学员 Top 10</template>
        <el-table :data="data.top_students || []" size="small">
          <el-table-column type="index" width="50" />
          <el-table-column prop="display_name" label="学员" />
          <el-table-column prop="value" label="活跃分" width="90" />
          <el-table-column prop="label" label="明细" />
        </el-table>
      </el-card>
      <el-card shadow="never">
        <template #header>活跃班级 Top 10</template>
        <el-table :data="data.top_classes || []" size="small">
          <el-table-column type="index" width="50" />
          <el-table-column prop="display_name" label="班级" />
          <el-table-column prop="value" label="活跃度" width="90" />
          <el-table-column prop="label" label="规模" width="100" />
        </el-table>
      </el-card>
    </div>

    <el-card v-if="isAdmin && (data.quota_tenants || []).length" shadow="never" style="margin-bottom: 14px">
      <template #header>
        租户用量占用
        <el-button link type="primary" style="float: right" @click="router.push('/billing')">管理</el-button>
      </template>
      <el-table :data="data.quota_tenants" size="small">
        <el-table-column prop="name" label="租户" />
        <el-table-column label="Token %" width="160">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(100, row.token_pct)"
              :status="row.token_pct >= 80 ? 'exception' : undefined"
              :stroke-width="10"
            />
          </template>
        </el-table-column>
        <el-table-column label="次数 %" width="160">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(100, row.request_pct)"
              :status="row.request_pct >= 80 ? 'exception' : undefined"
              :stroke-width="10"
            />
          </template>
        </el-table-column>
        <el-table-column prop="ends_at" label="到期" width="120" />
        <el-table-column label="告警" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.alert" type="danger" size="small">高占用</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
      <p class="quota-sum">
        合计 Token {{ data.token_used_total ?? 0 }} / {{ data.token_quota_total ?? 0 }} · 调用
        {{ data.request_used_total ?? 0 }} / {{ data.request_quota_total ?? 0 }}
      </p>
    </el-card>

    <el-card v-if="isAdmin" shadow="never">
      <template #header>最近审计</template>
      <el-table :data="data.recent_audits" size="small">
        <el-table-column prop="action" label="动作" width="160" />
        <el-table-column prop="resource" label="资源" />
        <el-table-column prop="detail" label="详情" />
        <el-table-column prop="created_at" label="时间" width="200" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.card {
  border: 0;
  text-align: left;
  border-radius: 14px;
  padding: 16px;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(20, 33, 43, 0.08);
  transition: transform 0.15s;
}
.card:hover {
  transform: translateY(-2px);
}
.card.teal {
  background: linear-gradient(135deg, #0f6b5c, #1a8f7a);
}
.card.blue {
  background: linear-gradient(135deg, #1f6f8b, #2a8fbd);
}
.card.amber {
  background: linear-gradient(135deg, #c48912, #e8a317);
}
.card.green {
  background: linear-gradient(135deg, #2f7d4a, #4caa68);
}
.card.orange {
  background: linear-gradient(135deg, #c45c1a, #e07a2f);
}
.card.cyan {
  background: linear-gradient(135deg, #0f7a7a, #19a0a0);
}
.card.rose {
  background: linear-gradient(135deg, #a33d3d, #c45656);
}
.card.mint {
  background: linear-gradient(135deg, #3d7a6a, #5a9e8c);
}
.card-top .label {
  font-size: 13px;
  opacity: 0.92;
}
.value {
  margin-top: 8px;
  font-size: 1.7rem;
  font-weight: 700;
  line-height: 1.1;
}
.tip {
  margin-top: 6px;
  font-size: 12px;
  opacity: 0.85;
}
.charts {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 12px;
  margin-bottom: 14px;
}
.panel :deep(.el-card__header) {
  font-weight: 700;
  color: #14302a;
}
.bars {
  height: 180px;
  display: flex;
  align-items: flex-end;
  gap: 3px;
  padding: 8px 2px 0;
}
.bar-wrap {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
}
.bar {
  width: 100%;
  border-radius: 4px 4px 0 0;
  background: linear-gradient(180deg, #1a8f7a, #0f6b5c);
  min-height: 4px;
}
.bars.blue .bar {
  background: linear-gradient(180deg, #4aa3cc, #1f6f8b);
}
.bars.amber .bar {
  background: linear-gradient(180deg, #f0bf4a, #c48912);
}
.dist {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 16px;
  align-items: center;
  min-height: 180px;
}
.donut {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: grid;
  place-items: center;
}
.donut-hole {
  width: 78px;
  height: 78px;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
  text-align: center;
}
.donut-hole b {
  font-size: 1.2rem;
  color: var(--edu-teal);
}
.donut-hole span {
  font-size: 11px;
  color: var(--edu-muted);
}
.dist ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}
.dist li {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}
.dist i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.ranks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}
.quota-sum {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 13px;
}
@media (max-width: 1100px) {
  .cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts,
  .ranks,
  .dist {
    grid-template-columns: 1fr;
  }
}
</style>
