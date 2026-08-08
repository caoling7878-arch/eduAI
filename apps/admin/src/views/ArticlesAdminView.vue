<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createArticle, deleteArticle, fetchArticlesAdmin, updateArticle } from '../lib/api'

const rows = ref<any[]>([])
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  title: '',
  summary: '',
  body: '',
  lang: 'zh',
  published: true,
  day_tag: '',
})

async function load() {
  rows.value = await fetchArticlesAdmin()
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { title: '', summary: '', body: '', lang: 'zh', published: true, day_tag: '' })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, row)
  dialog.value = true
}

async function save() {
  if (editingId.value) await updateArticle(editingId.value, form)
  else await createArticle(form)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm('删除文章？', '提示')
  await deleteArticle(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar"><el-button type="primary" @click="openCreate">发布美文</el-button></div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="lang" label="语言" width="80" />
      <el-table-column prop="published" label="发布" width="80" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" title="每日美文" width="640px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.summary" /></el-form-item>
        <el-form-item label="正文"><el-input v-model="form.body" type="textarea" :rows="8" /></el-form-item>
        <el-form-item label="语言">
          <el-select v-model="form.lang">
            <el-option label="中文" value="zh" />
            <el-option label="English" value="en" />
          </el-select>
        </el-form-item>
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
  margin-bottom: 12px;
}
</style>
