<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { addEbookChapter, createEbook, deleteEbook, fetchEbooks, updateEbook } from '../lib/api'

const rows = ref<any[]>([])
const dialog = ref(false)
const chDialog = ref(false)
const editingId = ref<number | null>(null)
const chapterBookId = ref(0)
const form = reactive({ title: '', cover: '', summary: '', status: 'draft' })
const chForm = reactive({ title: '', content: '', sort_order: 1 })

async function load() {
  rows.value = await fetchEbooks()
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { title: '', cover: '', summary: '', status: 'draft' })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    title: row.title,
    cover: row.cover,
    summary: row.summary,
    status: row.status,
  })
  dialog.value = true
}

async function save() {
  if (editingId.value) await updateEbook(editingId.value, form)
  else await createEbook(form)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

function openChapter(row: any) {
  chapterBookId.value = row.id
  Object.assign(chForm, { title: '新章节', content: '', sort_order: (row.chapters?.length || 0) + 1 })
  chDialog.value = true
}

async function saveChapter() {
  await addEbookChapter(chapterBookId.value, chForm)
  ElMessage.success('章节已添加')
  chDialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`删除《${row.title}》？`, '提示')
  await deleteEbook(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar"><el-button type="primary" @click="openCreate">新建电子书</el-button></div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="书名" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="章节" width="90">
        <template #default="{ row }">{{ row.chapters?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="summary" label="简介" show-overflow-tooltip />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openChapter(row)">加章节</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="电子书" width="560px">
      <el-form label-width="80px">
        <el-form-item label="书名"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="封面"><el-input v-model="form.cover" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.summary" type="textarea" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chDialog" title="添加章节" width="640px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="chForm.title" /></el-form-item>
        <el-form-item label="正文"><el-input v-model="chForm.content" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chDialog = false">取消</el-button>
        <el-button type="primary" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  margin-bottom: 12px;
}
</style>
