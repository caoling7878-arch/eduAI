<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

const router = useRouter()
const data = ref<any>(null)
const rules = ref<any[]>([])
const runs = ref<any[]>([])
const events = ref<any[]>([])
const actions = ref<any[]>([])
const dialog = ref(false)
const form = reactive({
  id: 0,
  name: '',
  event: 'grade.ai_done',
  action: 'notify_staff',
  enabled: true,
  description: '',
  config_json: '{\n  "title": "提醒",\n  "link": "/grading",\n  "roles": ["admin", "teacher"]\n}',
})

async function load() {
  ;[data.value, rules.value, runs.value, events.value, actions.value] = await Promise.all([
    api('/workflows/overview'),
    api('/workflows/rules'),
    api('/workflows/runs?limit=30'),
    api('/workflows/events'),
    api('/workflows/actions'),
  ])
}

function go(link: string) {
  router.push(link)
}

function openCreate() {
  form.id = 0
  form.name = '新规则'
  form.event = 'grade.ai_done'
  form.action = 'notify_staff'
  form.enabled = true
  form.description = ''
  form.config_json =
    '{\n  "title": "提醒",\n  "link": "/grading",\n  "roles": ["admin", "teacher"]\n}'
  dialog.value = true
}

function openEdit(row: any) {
  form.id = row.id
  form.name = row.name
  form.event = row.event
  form.action = row.action
  form.enabled = row.enabled
  form.description = row.description || ''
  form.config_json = row.config_json || '{}'
  dialog.value = true
}

async function saveRule() {
  const body = {
    name: form.name,
    event: form.event,
    action: form.action,
    enabled: form.enabled,
    description: form.description,
    config_json: form.config_json,
  }
  try {
    if (form.id) {
      await api(`/workflows/rules/${form.id}`, { method: 'PATCH', body: JSON.stringify(body) })
    } else {
      await api('/workflows/rules', { method: 'POST', body: JSON.stringify(body) })
    }
    ElMessage.success('规则已保存')
    dialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  }
}

async function toggle(row: any) {
  await api(`/workflows/rules/${row.id}/toggle`, { method: 'POST' })
  await load()
}

async function runCheck() {
  const r = await api<any>('/workflows/dispatch/check.pending_grades', { method: 'POST' })
  ElMessage.success(`巡检完成：${(r.results || []).map((x: any) => x.message).join('；')}`)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <el-alert
      v-if="data?.note"
      type="info"
      :closable="false"
      :title="data.note"
      style="margin-bottom: 14px"
    />
    <div class="stats" v-if="data">
      <div class="stat" v-for="s in data.stages" :key="s.key" @click="go(s.link)">
        <b>{{ s.count }}</b>
        <span>{{ s.label }}</span>
      </div>
    </div>

    <el-row :gutter="14" v-if="data" style="margin-bottom: 14px">
      <el-col :span="8">
        <el-card shadow="never" header="批改状态">
          <el-table
            :data="Object.entries(data.grade_status || {}).map(([k, v]) => ({ k, v }))"
            size="small"
          >
            <el-table-column prop="k" label="状态" />
            <el-table-column prop="v" label="数量" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" header="质检状态">
          <el-table
            :data="Object.entries(data.qc_status || {}).map(([k, v]) => ({ k, v }))"
            size="small"
          >
            <el-table-column prop="k" label="状态" />
            <el-table-column prop="v" label="数量" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" header="反馈工单">
          <el-table
            :data="Object.entries(data.feedback_status || {}).map(([k, v]) => ({ k, v }))"
            size="small"
          >
            <el-table-column prop="k" label="状态" />
            <el-table-column prop="v" label="数量" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-bottom: 14px">
      <template #header>
        <div class="card-head">
          <span>编排规则（{{ data?.rules_enabled || 0 }}/{{ data?.rules_total || 0 }} 启用）</span>
          <div>
            <el-button size="small" @click="runCheck">巡检批改积压</el-button>
            <el-button type="primary" size="small" @click="openCreate">新建规则</el-button>
          </div>
        </div>
      </template>
      <el-table :data="rules" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="event" label="事件" width="160" />
        <el-table-column prop="action" label="动作" width="120" />
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="toggle(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" show-overflow-tooltip />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" header="最近执行日志">
      <el-table :data="runs" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="event" label="事件" width="160" />
        <el-table-column prop="rule_id" label="规则" width="70" />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column prop="message" label="结果" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="190" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="form.id ? '编辑规则' : '新建规则'" width="560px">
      <el-form label-width="88px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="事件">
          <el-select v-model="form.event" style="width: 100%">
            <el-option v-for="e in events" :key="e.id" :label="e.label" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作">
          <el-select v-model="form.action" style="width: 100%">
            <el-option v-for="a in actions" :key="a.id" :label="a.label" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
        <el-form-item label="配置 JSON">
          <el-input v-model="form.config_json" type="textarea" :rows="7" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.stat {
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.15s ease;
}
.stat:hover {
  box-shadow: 0 6px 18px rgba(15, 107, 92, 0.12);
}
.stat b {
  display: block;
  font-size: 1.6rem;
  color: var(--edu-brand, #0f6b5c);
}
.stat span {
  color: var(--edu-muted, #667);
  font-size: 0.9rem;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
</style>
