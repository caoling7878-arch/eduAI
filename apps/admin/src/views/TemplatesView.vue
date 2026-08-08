<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createPaperTemplate,
  createPptTemplate,
  fetchPaperTemplates,
  fetchPptTemplates,
  instantiatePaperTemplate,
} from '../lib/api'

const papers = ref<any[]>([])
const ppts = ref<any[]>([])
const pForm = reactive({
  name: '随堂小测模板',
  description: '',
  question_types: 'single,judge,essay',
  default_count: 6,
})
const tForm = reactive({
  name: '概念课标准版',
  theme: 'teal',
  outline_hint: '导入\n核心概念\n例题\n练习\n小结',
})

async function load() {
  ;[papers.value, ppts.value] = await Promise.all([fetchPaperTemplates(), fetchPptTemplates()])
}

async function savePaper() {
  await createPaperTemplate(pForm)
  ElMessage.success('试卷模板已创建')
  await load()
}

async function usePaper(id: number) {
  const r = await instantiatePaperTemplate(id)
  ElMessage.success(`已生成草稿试卷 #${r.paper_id}：${r.title}`)
}

async function savePpt() {
  await createPptTemplate(tForm)
  ElMessage.success('PPT 模板已创建')
  await load()
}

onMounted(load)
</script>

<template>
  <div class="grid">
    <el-card shadow="never">
      <template #header>试卷模板</template>
      <el-form label-width="90px">
        <el-form-item label="名称"><el-input v-model="pForm.name" /></el-form-item>
        <el-form-item label="题型"><el-input v-model="pForm.question_types" placeholder="single,judge,essay" /></el-form-item>
        <el-form-item label="题量"><el-input-number v-model="pForm.default_count" :min="1" :max="50" /></el-form-item>
        <el-form-item><el-button type="primary" @click="savePaper">新建模板</el-button></el-form-item>
      </el-form>
      <el-table :data="papers" size="small">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="question_types" label="题型" />
        <el-table-column prop="default_count" label="题量" width="80" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="usePaper(row.id)">生成试卷</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>PPT 模板</template>
      <el-form label-width="90px">
        <el-form-item label="名称"><el-input v-model="tForm.name" /></el-form-item>
        <el-form-item label="主题色"><el-input v-model="tForm.theme" /></el-form-item>
        <el-form-item label="大纲提示"><el-input v-model="tForm.outline_hint" type="textarea" :rows="5" /></el-form-item>
        <el-form-item><el-button type="primary" @click="savePpt">新建模板</el-button></el-form-item>
      </el-form>
      <el-table :data="ppts" size="small">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="theme" label="主题" width="100" />
        <el-table-column prop="outline_hint" label="大纲" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 960px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
