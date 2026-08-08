<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { addChapter, createCourse, deleteCourse, fetchCourses, updateCourse } from '../lib/api'

const rows = ref<any[]>([])
const dialog = ref(false)
const chapterDialog = ref(false)
const editingId = ref<number | null>(null)
const chapterCourseId = ref(0)
const form = reactive({
  title: '',
  cover: '',
  summary: '',
  price_type: 'public',
  price: 0,
  status: 'draft',
  sort_order: 0,
})
const chapterForm = reactive({ title: '新章节', sort_order: 1, lessons: [{ title: '第一课', content_type: 'richtext', content: '', sort_order: 1 }] })

async function load() {
  rows.value = await fetchCourses()
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    title: '',
    cover: '',
    summary: '',
    price_type: 'public',
    price: 0,
    status: 'draft',
    sort_order: 0,
  })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    title: row.title,
    cover: row.cover,
    summary: row.summary,
    price_type: row.price_type,
    price: row.price,
    status: row.status,
    sort_order: row.sort_order,
  })
  dialog.value = true
}

async function save() {
  if (editingId.value) await updateCourse(editingId.value, form)
  else await createCourse(form)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`删除课程「${row.title}」？`, '提示')
  await deleteCourse(row.id)
  await load()
}

function openChapter(row: any) {
  chapterCourseId.value = row.id
  chapterForm.title = '新章节'
  chapterForm.lessons = [{ title: '第一课', content_type: 'richtext', content: '', sort_order: 1 }]
  chapterDialog.value = true
}

async function saveChapter() {
  await addChapter(chapterCourseId.value, chapterForm)
  ElMessage.success('章节已添加')
  chapterDialog.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建课程</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="price_type" label="定价" width="100" />
      <el-table-column prop="price" label="价格" width="90" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="student_count" label="学员" width="80" />
      <el-table-column label="章节" width="90">
        <template #default="{ row }">{{ row.chapters?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openChapter(row)">加章节</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="课程" width="560px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="封面"><el-input v-model="form.cover" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.summary" type="textarea" /></el-form-item>
        <el-form-item label="定价类型">
          <el-select v-model="form.price_type">
            <el-option label="公开免费" value="public" />
            <el-option label="会员" value="member" />
            <el-option label="付费" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格"><el-input-number v-model="form.price" :min="0" /></el-form-item>
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

    <el-dialog v-model="chapterDialog" title="添加章节" width="560px">
      <el-form label-width="80px">
        <el-form-item label="章节名"><el-input v-model="chapterForm.title" /></el-form-item>
        <el-form-item label="首课标题">
          <el-input v-model="chapterForm.lessons[0].title" />
        </el-form-item>
        <el-form-item label="内容类型">
          <el-select v-model="chapterForm.lessons[0].content_type">
            <el-option label="富文本" value="richtext" />
            <el-option label="视频" value="video" />
            <el-option label="交互实验" value="interactive_lab" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容/课页 ID"><el-input v-model="chapterForm.lessons[0].content" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialog = false">取消</el-button>
        <el-button type="primary" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  margin-bottom: 14px;
}
</style>
