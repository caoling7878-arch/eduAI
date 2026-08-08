<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadPpt, fetchPpts, generatePpt } from '../lib/api'

const jobs = ref<any[]>([])
const current = ref<any | null>(null)
const exporting = ref(false)
const form = reactive({
  title: '线面角专题课',
  outline: '概念引入\n判定与性质\n典型例题\n课堂练习',
})

async function load() {
  jobs.value = await fetchPpts()
}

async function gen() {
  current.value = await generatePpt(form)
  ElMessage.success('已生成演示稿大纲')
  await load()
}

async function exportCurrent() {
  if (!current.value?.id) return
  exporting.value = true
  try {
    await downloadPpt(current.value.id, current.value.title || 'slides')
    ElMessage.success('已开始下载 PPTX')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

async function exportRow(row: any) {
  try {
    await downloadPpt(row.id, row.title)
    ElMessage.success('已开始下载')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="grid">
    <el-card shadow="never">
      <template #header>生成 PPT 大纲</template>
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="大纲">
          <el-input v-model="form.outline" type="textarea" :rows="8" placeholder="每行一个小节" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="gen">生成</el-button>
          <el-button :disabled="!current?.id" :loading="exporting" @click="exportCurrent">
            导出 PPTX
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card shadow="never">
      <template #header>预览</template>
      <div v-if="current" class="slides">
        <article v-for="(s, i) in current.slides" :key="i" class="slide">
          <h3>{{ s.title }}</h3>
          <p>{{ s.body }}</p>
        </article>
      </div>
      <el-empty v-else description="生成后在此预览幻灯片卡片" />
    </el-card>
    <el-card shadow="never" class="span">
      <template #header>历史任务</template>
      <el-table :data="jobs" @row-click="(r: any) => (current = r)">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="时间" width="200" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="exportRow(row)">导出</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.span {
  grid-column: 1 / -1;
}
.slides {
  display: grid;
  gap: 10px;
  max-height: 480px;
  overflow: auto;
}
.slide {
  border: 1px solid rgba(15, 107, 92, 0.15);
  border-radius: 12px;
  padding: 14px;
  background: linear-gradient(180deg, #f7fbfa, #fff);
}
.slide h3 {
  margin: 0 0 6px;
  color: var(--edu-teal);
}
.slide p {
  margin: 0;
  color: var(--edu-muted);
}
</style>
