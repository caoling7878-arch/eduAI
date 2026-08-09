<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { attachLab, fetchCourses, fetchLabPages, fetchQuestions, patchLabPage } from '../lib/api'
import { webBaseUrl } from '../lib/webEntry'

const pages = ref<any[]>([])
const courses = ref<any[]>([])
const questions = ref<any[]>([])
const form = reactive({ lesson_id: 0 as number, page_key: '', title: '' })
const editing = ref<Record<number, string>>({})
const editingQids = ref<Record<number, number[]>>({})
const webBase = webBaseUrl()

const lessons = ref<Array<{ id: number; label: string }>>([])

async function load() {
  ;[pages.value, courses.value, questions.value] = await Promise.all([
    fetchLabPages(),
    fetchCourses(),
    fetchQuestions(),
  ])
  const list: Array<{ id: number; label: string }> = []
  for (const c of courses.value) {
    for (const ch of c.chapters || []) {
      for (const les of ch.lessons || []) {
        list.push({ id: les.id, label: `${c.title} / ${ch.title} / ${les.title}` })
      }
    }
  }
  lessons.value = list
  if (list[0]) form.lesson_id = list[0].id
  if (pages.value[0]) form.page_key = pages.value[0].page_key
  editing.value = Object.fromEntries(pages.value.map((p) => [p.id, p.knowledge_points || '']))
  editingQids.value = Object.fromEntries(
    pages.value.map((p) => [p.id, [...(p.question_ids || [])]]),
  )
}

async function attach() {
  const r = await attachLab(form)
  ElMessage.success(`已挂课：${r.preview}`)
}

async function saveRow(row: any) {
  const kp = editing.value[row.id] ?? ''
  const qids = editingQids.value[row.id] || []
  await patchLabPage(row.page_key, { knowledge_points: kp, question_ids: qids })
  ElMessage.success('课页关联已保存')
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <p class="hint">将课页挂到课时，并维护知识点与显式题目关联（学完后推荐/变式练习）。</p>
    <el-card shadow="never" style="margin-bottom: 14px; max-width: 720px">
      <template #header>挂课</template>
      <el-form label-width="80px">
        <el-form-item label="课时">
          <el-select v-model="form.lesson_id" filterable style="width: 100%">
            <el-option v-for="l in lessons" :key="l.id" :label="l.label" :value="l.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课页">
          <el-select v-model="form.page_key" style="width: 100%">
            <el-option
              v-for="p in pages"
              :key="p.page_key"
              :label="`${p.title} (${p.page_key})`"
              :value="p.page_key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="课时名">
          <el-input v-model="form.title" placeholder="可选，覆盖原课时标题" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="attach">挂到课时</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="pages" stripe>
      <el-table-column prop="page_key" label="课页 ID" width="160" />
      <el-table-column prop="title" label="名称" width="110" />
      <el-table-column prop="category" label="分类" width="90" />
      <el-table-column label="知识点" min-width="160">
        <template #default="{ row }">
          <el-input v-model="editing[row.id]" placeholder="逗号分隔" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="关联题目" min-width="220">
        <template #default="{ row }">
          <el-select
            v-model="editingQids[row.id]"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="可选显式挂题"
            size="small"
            style="width: 100%"
          >
            <el-option
              v-for="q in questions.filter((x) => x.type !== 'essay')"
              :key="q.id"
              :label="`#${q.id} ${(q.stem || '').slice(0, 28)}`"
              :value="q.id"
            />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="saveRow(row)">保存</el-button>
        </template>
      </el-table-column>
      <el-table-column label="预览" width="90">
        <template #default="{ row }">
          <el-link :href="`${webBase}${row.preview_path}`" target="_blank" type="primary">打开</el-link>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.hint {
  color: var(--edu-muted);
  margin-top: 0;
}
</style>
