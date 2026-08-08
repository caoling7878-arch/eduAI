<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchTeachers, fetchUsers, upsertTeacher, type User } from '../lib/api'

const rows = ref<any[]>([])
const users = ref<User[]>([])
const dialog = ref(false)
const form = reactive({ user_id: 0, title: '教师', bio: '', subjects: '' })

async function load() {
  rows.value = await fetchTeachers()
  users.value = await fetchUsers('', 'teacher')
  const all = await fetchUsers()
  const teacherIds = new Set(users.value.map((u) => u.id))
  users.value = [
    ...users.value,
    ...all.filter((u) => u.role === 'student' || !teacherIds.has(u.id)),
  ]
}

function open() {
  form.user_id = users.value[0]?.id || 0
  form.title = '教师'
  form.bio = ''
  form.subjects = ''
  dialog.value = true
}

async function save() {
  await upsertTeacher(form)
  ElMessage.success('已保存')
  dialog.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="open">录入 / 更新教师档案</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="display_name" label="姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="title" label="职称" />
      <el-table-column prop="subjects" label="学科" />
      <el-table-column prop="bio" label="简介" />
    </el-table>
    <el-dialog v-model="dialog" title="教师档案" width="520px">
      <el-form label-width="80px">
        <el-form-item label="用户">
          <el-select v-model="form.user_id" filterable style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="`${u.display_name} <${u.email}>`" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="职称"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="学科"><el-input v-model="form.subjects" placeholder="数学,物理" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.bio" type="textarea" :rows="3" /></el-form-item>
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
