<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchFeedbackAdmin, replyFeedback } from '../lib/api'

const rows = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const current = ref<any>(null)
const form = reactive({ reply: '', status: 'done' })

const statusMap: Record<string, string> = {
  open: '待处理',
  processing: '处理中',
  resolved: '已回复',
  done: '已完成',
  closed: '已关闭',
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchFeedbackAdmin()
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function open(row: any) {
  current.value = row
  form.reply = row.reply || ''
  form.status = row.status === 'open' ? 'done' : row.status
  dialog.value = true
}

async function save() {
  if (!current.value) return
  try {
    await replyFeedback(current.value.id, { ...form })
    ElMessage.success('已回复')
    dialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="学员" min-width="110">
        <template #default="{ row }">
          {{ row.user_name || (row.user_id ? `#${row.user_id}` : '游客') }}
        </template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="title" label="标题" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'open' ? 'warning' : 'success'">
            {{ statusMap[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="open(row)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !rows.length" description="暂无反馈工单" />
    <el-dialog v-model="dialog" title="处理反馈" width="560px">
      <template v-if="current">
        <p>
          <b>{{ current.title }}</b>
          <span style="color: #64748b; margin-left: 8px">
            · {{ current.user_name || (current.user_id ? `#${current.user_id}` : '游客') }}
          </span>
        </p>
        <p>{{ current.body }}</p>
        <el-form label-width="70px" style="margin-top: 12px">
          <el-form-item label="回复"><el-input v-model="form.reply" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status">
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="done" />
              <el-option label="待处理" value="open" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>
