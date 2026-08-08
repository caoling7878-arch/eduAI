<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchStudentOps,
  updateUser,
  type StudentOps,
} from '../lib/api'

const rows = ref<StudentOps[]>([])
const q = ref('')
const memberOnly = ref(false)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await fetchStudentOps()
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  let list = rows.value
  if (memberOnly.value) list = list.filter((r) => r.is_member)
  const key = q.value.trim().toLowerCase()
  if (key) {
    list = list.filter(
      (r) =>
        r.email.toLowerCase().includes(key) ||
        r.display_name.toLowerCase().includes(key) ||
        (r.tags || '').toLowerCase().includes(key),
    )
  }
  return list
})

const summary = computed(() => ({
  total: rows.value.length,
  members: rows.value.filter((r) => r.is_member).length,
  active: rows.value.filter((r) => (r.activity_score || 0) > 0).length,
  revenue: rows.value.reduce((s, r) => s + (r.paid_amount || 0), 0),
}))

async function toggleStatus(row: StudentOps) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  await ElMessageBox.confirm(`将「${row.display_name}」设为 ${next === 'active' ? '启用' : '停用'}？`, '账号状态')
  await updateUser(row.id, { status: next })
  ElMessage.success('已更新')
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="summary">
      <div class="s"><b>{{ summary.total }}</b><span>学员账号</span></div>
      <div class="s"><b>{{ summary.members }}</b><span>付费会员</span></div>
      <div class="s"><b>{{ summary.active }}</b><span>有活跃记录</span></div>
      <div class="s"><b>¥{{ summary.revenue.toFixed(2) }}</b><span>累计付费</span></div>
    </div>

    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索姓名 / 邮箱 / 标签" clearable style="width: 260px" />
      <el-checkbox v-model="memberOnly">仅看会员</el-checkbox>
      <el-button @click="load" :loading="loading">刷新</el-button>
    </div>

    <div class="table-scroll">
      <el-table
        :data="filtered"
        stripe
        v-loading="loading"
        :scrollbar-always-on="true"
        style="width: max(100%, 1180px)"
      >
        <el-table-column prop="display_name" label="学员" min-width="110" fixed />
        <el-table-column prop="email" label="账号" min-width="180" show-overflow-tooltip />
        <el-table-column label="会员" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_member" type="success" size="small">{{ row.member_plan || '会员' }}</el-tag>
            <el-tag v-else type="info" size="small">未开通</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="paid_amount" label="付费额" width="100" />
        <el-table-column prop="activity_score" label="活跃分" width="90" sortable />
        <el-table-column prop="checkins" label="打卡" width="72" />
        <el-table-column prop="submissions" label="交卷" width="72" />
        <el-table-column prop="wrong_open" label="错题" width="72" />
        <el-table-column prop="progress_done" label="完成课时" width="96" />
        <el-table-column prop="last_active" label="最近活跃" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.s {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
.s b {
  display: block;
  font-size: 1.4rem;
  color: var(--edu-teal);
}
.s span {
  color: var(--edu-muted);
  font-size: 13px;
}
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.table-scroll {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.1);
  border-radius: 12px;
  -webkit-overflow-scrolling: touch;
}
.table-scroll :deep(.el-table) {
  --el-table-border-color: rgba(15, 107, 92, 0.08);
  min-width: 1180px;
}
@media (max-width: 900px) {
  .summary {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
