<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createClass,
  deleteClass,
  fetchClasses,
  fetchCourses,
  fetchMe,
  fetchUserOptions,
  updateClass,
  type User,
} from '../lib/api'

const me = ref<User | null>(null)
const rows = ref<any[]>([])
const teachers = ref<User[]>([])
const students = ref<User[]>([])
const courses = ref<any[]>([])
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  teacher_id: undefined as number | undefined,
  course_id: undefined as number | undefined,
  member_ids: [] as number[],
})

const isAdmin = computed(() => me.value?.role === 'admin')
const teacherName = (id?: number | null) =>
  teachers.value.find((t) => t.id === id)?.display_name || (id ? `#${id}` : '—')

async function load() {
  me.value = await fetchMe()
  ;[rows.value, teachers.value, students.value, courses.value] = await Promise.all([
    fetchClasses(),
    fetchUserOptions('teacher'),
    fetchUserOptions('student'),
    fetchCourses(),
  ])
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '',
    teacher_id: isAdmin.value ? teachers.value[0]?.id : me.value?.id,
    course_id: courses.value[0]?.id,
    member_ids: [],
  })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    teacher_id: row.teacher_id,
    course_id: row.course_id,
    member_ids: row.member_ids || [],
  })
  dialog.value = true
}

async function save() {
  const payload = {
    ...form,
    teacher_id: isAdmin.value ? form.teacher_id : me.value?.id,
  }
  if (editingId.value) await updateClass(editingId.value, payload)
  else await createClass(payload)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`删除班级「${row.name}」？`, '提示')
  await deleteClass(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建班级</el-button>
      <span class="hint">{{ isAdmin ? '全部班级' : '仅显示我任教的班级' }}</span>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="班级" />
      <el-table-column label="任课教师" min-width="120">
        <template #default="{ row }">{{ teacherName(row.teacher_id) }}</template>
      </el-table-column>
      <el-table-column label="关联课程" min-width="160">
        <template #default="{ row }">
          {{ courses.find((c) => c.id === row.course_id)?.title || (row.course_id ? `#${row.course_id}` : '—') }}
        </template>
      </el-table-column>
      <el-table-column label="人数" width="90">
        <template #default="{ row }">{{ row.member_ids?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" title="班级" width="520px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item v-if="isAdmin" label="教师">
          <el-select v-model="form.teacher_id" clearable style="width: 100%">
            <el-option v-for="t in teachers" :key="t.id" :label="t.display_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程">
          <el-select v-model="form.course_id" clearable style="width: 100%">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学员">
          <el-select v-model="form.member_ids" multiple filterable style="width: 100%">
            <el-option
              v-for="s in students"
              :key="s.id"
              :label="`${s.display_name} (${s.email})`"
              :value="s.id"
            />
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
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.hint {
  color: #64748b;
  font-size: 13px;
}
</style>
