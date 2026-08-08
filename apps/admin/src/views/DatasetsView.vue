<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, exportDataset, fetchDatasetSamples, syncDataset, getToken } from '../lib/api'

const rows = ref<any[]>([])
const jobs = ref<any[]>([])
const syncing = ref(false)
const creating = ref(false)
const filter = reactive({ source: '', exported: '' as '' | '0' | '1' })
const jobForm = reactive({
  name: '样本微调任务',
  base_model: 'gpt-4o-mini',
  unexported_only: true,
  limit: 200,
})

async function load() {
  const params = new URLSearchParams()
  if (filter.source) params.set('source', filter.source)
  if (filter.exported === '0') params.set('exported', 'false')
  if (filter.exported === '1') params.set('exported', 'true')
  const qs = params.toString()
  ;[rows.value, jobs.value] = await Promise.all([
    fetchDatasetSamples(qs ? `?${qs}` : ''),
    api('/datasets/finetune/jobs'),
  ])
}

async function doSync() {
  syncing.value = true
  try {
    const r = await syncDataset()
    ElMessage.success(`已回流 ${r.added} 条新样本`)
    await load()
  } finally {
    syncing.value = false
  }
}

async function doExport(format: 'json' | 'jsonl', unexportedOnly = false) {
  const params = new URLSearchParams({
    format,
    mark_exported: 'true',
    unexported_only: String(unexportedOnly),
  })
  if (filter.source) params.set('source', filter.source)
  if (format === 'json') {
    const items = await exportDataset(`?${params.toString()}`)
    const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' })
    downloadBlob(blob, `eduai-dataset-${Date.now()}.json`)
    ElMessage.success(`已导出 ${items.length} 条 JSON`)
  } else {
    const token = getToken()
    const res = await fetch(`/api/v1/datasets/export?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('导出失败')
    const text = await res.text()
    downloadBlob(new Blob([text], { type: 'application/x-ndjson' }), `eduai-dataset-${Date.now()}.jsonl`)
    ElMessage.success('已导出 JSONL')
  }
  await load()
}

async function createJob() {
  creating.value = true
  try {
    await api('/datasets/finetune/jobs', {
      method: 'POST',
      body: JSON.stringify(jobForm),
    })
    ElMessage.success('已创建外部微调任务（演示）')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function advance(job: any) {
  try {
    const r = await api<any>(`/datasets/finetune/jobs/${job.id}/advance`, { method: 'POST' })
    ElMessage.success(`状态 → ${r.status}`)
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '推进失败')
  }
}

function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-select v-model="filter.source" clearable placeholder="来源" style="width: 140px" @change="load">
        <el-option label="错题" value="wrong" />
        <el-option label="评分差异" value="grade_diff" />
      </el-select>
      <el-select v-model="filter.exported" clearable placeholder="导出状态" style="width: 140px" @change="load">
        <el-option label="未导出" value="0" />
        <el-option label="已导出" value="1" />
      </el-select>
      <el-button type="primary" :loading="syncing" @click="doSync">从错题/评分差异回流</el-button>
      <el-button @click="doExport('json')">导出 JSON</el-button>
      <el-button type="success" @click="doExport('jsonl', true)">导出未导出 JSONL</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-alert
      type="info"
      :closable="false"
      title="样本来源：未掌握错题、教师复核与 AI 分差 ≥ 0.5 的主观题。可组装 Chat JSONL 创建外部微调任务（演示推进；生产配置 FINETUNE_WEBHOOK_URL）。"
      style="margin-bottom: 12px"
    />

    <el-card shadow="never" header="创建外部微调任务" style="margin-bottom: 14px">
      <div class="job-form">
        <el-input v-model="jobForm.name" placeholder="任务名称" style="width: 200px" />
        <el-input v-model="jobForm.base_model" placeholder="基座模型" style="width: 160px" />
        <el-input-number v-model="jobForm.limit" :min="10" :max="2000" />
        <el-checkbox v-model="jobForm.unexported_only">仅未导出样本</el-checkbox>
        <el-button type="warning" :loading="creating" @click="createJob">创建微调任务</el-button>
      </div>
    </el-card>

    <el-card v-if="jobs.length" shadow="never" header="微调任务" style="margin-bottom: 14px">
      <el-table :data="jobs" size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="base_model" label="模型" width="120" />
        <el-table-column prop="sample_count" label="样本" width="80" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column label="进度" width="140">
          <template #default="{ row }">
            <el-progress :percentage="row.progress_pct || 0" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column prop="webhook_status" label="Webhook" width="100" />
        <el-table-column prop="external_job_id" label="外部 ID" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!['succeeded', 'failed', 'cancelled'].includes(row.status)"
              link
              type="primary"
              @click="advance(row)"
            >
              推进演示
            </el-button>
            <span v-else class="done">完成</span>
          </template>
        </el-table-column>
      </el-table>
      <el-collapse v-if="jobs[0]?.training_preview" style="margin-top: 10px">
        <el-collapse-item title="最近任务 JSONL 预览" name="1">
          <pre class="preview">{{ jobs[0].training_preview }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="source" label="来源" width="120" />
      <el-table-column prop="knowledge_points" label="知识点" width="140" />
      <el-table-column label="摘要">
        <template #default="{ row }">
          {{ row.payload?.stem?.slice(0, 60) || row.payload?.fingerprint }}
        </template>
      </el-table-column>
      <el-table-column prop="exported" label="已导出" width="90" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
.job-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.preview {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  max-height: 220px;
  overflow: auto;
  background: #f8fafc;
  padding: 10px;
  border-radius: 8px;
}
.done {
  color: #94a3b8;
  font-size: 12px;
}
</style>
