<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createUser, deleteUser, fetchUsers, updateUser, type User } from '../lib/api'

const rows = ref<User[]>([])
const q = ref('')
const dialog = ref(false)
const editing = ref<User | null>(null)
const form = reactive({
  email: '',
  display_name: '',
  password: '',
  role: 'student',
  status: 'active',
  tags: '',
})

async function load() {
  rows.value = await fetchUsers(q.value)
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    email: '',
    display_name: '',
    password: '',
    role: 'student',
    status: 'active',
    tags: '',
  })
  dialog.value = true
}

function openEdit(u: User) {
  editing.value = u
  Object.assign(form, {
    email: u.email,
    display_name: u.display_name,
    password: '',
    role: u.role,
    status: u.status,
    tags: u.tags,
  })
  dialog.value = true
}

async function save() {
  try {
    if (editing.value) {
      await updateUser(editing.value.id, form)
    } else {
      await createUser(form)
    }
    dialog.value = false
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function remove(u: User) {
  await ElMessageBox.confirm(`确认删除 ${u.email}？`, '提示')
  await deleteUser(u.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索邮箱/姓名" clearable style="width: 240px" @keyup.enter="load" />
      <el-button @click="load">搜索</el-button>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="display_name" label="姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="role" label="角色" width="100" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="tags" label="标签" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editing ? '编辑用户' : '新建用户'" width="480px">
      <el-form label-width="80px">
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.display_name" /></el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" :placeholder="editing ? '留空则不改' : '至少 6 位'" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="管理员" value="admin" />
            <el-option label="教师" value="teacher" />
            <el-option label="学员" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签"><el-input v-model="form.tags" /></el-form-item>
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
