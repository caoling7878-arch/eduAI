<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createQuestion, deleteQuestion, fetchQuestions, updateQuestion } from '../lib/api'

const rows = ref<any[]>([])
const q = ref('')
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  type: 'single',
  stem: '',
  optionsText: 'A\nB\nC\nD',
  answer: '0',
  analysis: '',
  knowledge_points: '',
  difficulty: 1,
})

async function load() {
  rows.value = await fetchQuestions(q.value)
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    type: 'single',
    stem: '',
    optionsText: '选项A\n选项B\n选项C\n选项D',
    answer: '0',
    analysis: '',
    knowledge_points: '',
    difficulty: 1,
  })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    type: row.type,
    stem: row.stem,
    optionsText: (row.options || []).join('\n'),
    answer: row.answer,
    analysis: row.analysis,
    knowledge_points: row.knowledge_points,
    difficulty: row.difficulty,
  })
  dialog.value = true
}

async function save() {
  const body = {
    type: form.type,
    stem: form.stem,
    options: form.optionsText.split('\n').map((s) => s.trim()).filter(Boolean),
    answer: form.answer,
    analysis: form.analysis,
    knowledge_points: form.knowledge_points,
    difficulty: form.difficulty,
  }
  if (editingId.value) await updateQuestion(editingId.value, body)
  else await createQuestion(body)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm('确认删除题目？', '提示')
  await deleteQuestion(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索题干" style="width: 240px" @keyup.enter="load" />
      <el-button @click="load">搜索</el-button>
      <el-button type="primary" @click="openCreate">新建题目</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="type" label="题型" width="90" />
      <el-table-column prop="stem" label="题干" />
      <el-table-column prop="difficulty" label="难度" width="80" />
      <el-table-column prop="knowledge_points" label="知识点" width="140" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" title="题目" width="640px">
      <el-form label-width="90px">
        <el-form-item label="题型">
          <el-select v-model="form.type">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multi" />
            <el-option label="判断" value="judge" />
            <el-option label="填空" value="blank" />
            <el-option label="主观题" value="essay" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干"><el-input v-model="form.stem" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="选项"><el-input v-model="form.optionsText" type="textarea" :rows="4" placeholder="每行一个选项" /></el-form-item>
        <el-form-item label="答案"><el-input v-model="form.answer" placeholder="单选填选项下标，如 0" /></el-form-item>
        <el-form-item label="解析"><el-input v-model="form.analysis" type="textarea" /></el-form-item>
        <el-form-item label="知识点"><el-input v-model="form.knowledge_points" /></el-form-item>
        <el-form-item label="难度"><el-input-number v-model="form.difficulty" :min="1" :max="5" /></el-form-item>
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
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
</style>
