<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createPaper, fetchPapers, fetchQuestions, updatePaper } from '../lib/api'

const rows = ref<any[]>([])
const questions = ref<any[]>([])
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', status: 'draft', question_ids: [] as number[] })

async function load() {
  ;[rows.value, questions.value] = await Promise.all([fetchPapers(), fetchQuestions()])
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { title: '', status: 'draft', question_ids: [] })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { title: row.title, status: row.status, question_ids: row.question_ids || [] })
  dialog.value = true
}

async function save() {
  if (editingId.value) await updatePaper(editingId.value, form)
  else await createPaper(form)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar"><el-button type="primary" @click="openCreate">组卷</el-button></div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="试卷" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column label="题量" width="90">
        <template #default="{ row }">{{ row.question_ids?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" title="试卷" width="560px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
        <el-form-item label="选题">
          <el-select v-model="form.question_ids" multiple filterable style="width: 100%">
            <el-option v-for="q in questions" :key="q.id" :label="`#${q.id} ${q.stem.slice(0, 40)}`" :value="q.id" />
          </el-select>
        </el-form-item>
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
