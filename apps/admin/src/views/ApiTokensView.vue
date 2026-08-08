<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createApiToken, fetchApiTokens, revokeApiToken } from '../lib/api'

const SCOPE_OPTIONS = [
  { value: 'courses:read', label: '课程只读' },
  { value: 'announcements:read', label: '公告只读' },
  { value: 'labs:read', label: '实验室只读' },
  { value: 'papers:read', label: '试卷只读' },
  { value: '*', label: '全部权限 *' },
]

const rows = ref<any[]>([])
const created = ref('')
const form = reactive({
  name: 'LMS 集成',
  selected: ['courses:read', 'announcements:read', 'labs:read', 'papers:read'] as string[],
})

const scopesStr = computed(() => form.selected.join(','))

async function load() {
  rows.value = await fetchApiTokens()
}

async function create() {
  if (!form.selected.length) {
    ElMessage.warning('请至少勾选一个权限范围')
    return
  }
  const r = await createApiToken({ name: form.name, scopes: scopesStr.value })
  created.value = r.token || ''
  ElMessage.success('Token 已创建，请立即复制保存')
  await load()
}

async function revoke(row: any) {
  await ElMessageBox.confirm(`吊销「${row.name}」？`, '提示')
  await revokeApiToken(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 14px; max-width: 720px">
      <template #header>创建开放 API Token</template>
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="权限范围">
          <el-checkbox-group v-model="form.selected">
            <el-checkbox v-for="s in SCOPE_OPTIONS" :key="s.value" :label="s.value">
              {{ s.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="create">生成 Token</el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="created" type="success" :closable="false" title="明文 Token（仅显示一次）">
        <code style="word-break: break-all">{{ created }}</code>
      </el-alert>
      <p class="hint">
        调用示例：<code>curl -H "X-API-Key: eduai_xxx" http://127.0.0.1:8000/api/v1/public/v1/courses</code>
      </p>
    </el-card>

    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="token_prefix" label="前缀" width="140" />
      <el-table-column prop="scopes" label="权限" show-overflow-tooltip />
      <el-table-column prop="enabled" label="启用" width="80" />
      <el-table-column prop="last_used_at" label="最近使用" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" :disabled="!row.enabled" @click="revoke(row)">吊销</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.hint {
  color: var(--edu-muted);
  font-size: 0.9rem;
}
code {
  font-size: 0.85rem;
}
</style>
