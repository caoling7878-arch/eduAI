<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createAnnouncement, deleteAnnouncement, fetchAnnouncements, updateAnnouncement } from '../lib/api'

const rows = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', body: '', published: true })

async function load() {
  loading.value = true
  try {
    rows.value = await fetchAnnouncements()
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { title: '', body: '', published: true })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { title: row.title, body: row.body, published: row.published })
  dialog.value = true
}

async function save() {
  if (editingId.value) await updateAnnouncement(editingId.value, form)
  else await createAnnouncement(form)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm('删除公告？', '提示')
  await deleteAnnouncement(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar"><el-button type="primary" @click="openCreate">发布公告</el-button></div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" />
      <el-table-column label="发布" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.published ? 'success' : 'info'">
            {{ row.published ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="views" label="浏览" width="90" />
      <el-table-column prop="created_at" label="时间" width="200" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !rows.length" description="暂无公告" />
    <el-dialog v-model="dialog" title="公告" width="560px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="正文"><el-input v-model="form.body" type="textarea" :rows="6" /></el-form-item>
        <el-form-item label="发布"><el-switch v-model="form.published" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  margin-bottom: 14px;
}
</style>
