<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createAssistant, deleteAssistant, fetchAssistants, fetchBases, updateAssistant } from '../lib/api'

const rows = ref<any[]>([])
const bases = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  avatar: '助',
  persona: '',
  system_prompt: '',
  suggested_prompts_text: '',
  model: 'gpt-4o-mini',
  temperature: 0.7,
  knowledge_base_id: undefined as number | undefined,
  enabled: true,
})

function promptsToText(arr: string[] | undefined) {
  return (arr || []).join('\n')
}

function textToPrompts(text: string) {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 8)
}

function kbName(id: number | null | undefined) {
  if (!id) return '—'
  return bases.value.find((b) => b.id === id)?.name || `#${id}`
}

async function load() {
  loading.value = true
  try {
    ;[rows.value, bases.value] = await Promise.all([fetchAssistants(), fetchBases()])
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '',
    avatar: '助',
    persona: '',
    system_prompt: '',
    suggested_prompts_text: '',
    model: 'gpt-4o-mini',
    temperature: 0.7,
    knowledge_base_id: undefined,
    enabled: true,
  })
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    avatar: row.avatar,
    persona: row.persona,
    system_prompt: row.system_prompt || '',
    suggested_prompts_text: promptsToText(row.suggested_prompts),
    model: row.model,
    temperature: row.temperature,
    knowledge_base_id: row.knowledge_base_id ?? undefined,
    enabled: row.enabled,
  })
  dialog.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const body = {
    name: form.name,
    avatar: form.avatar,
    persona: form.persona,
    system_prompt: form.system_prompt,
    suggested_prompts: textToPrompts(form.suggested_prompts_text),
    model: form.model,
    temperature: form.temperature,
    knowledge_base_id: form.knowledge_base_id ?? null,
    enabled: form.enabled,
  }
  try {
    if (editingId.value) await updateAssistant(editingId.value, body)
    else await createAssistant(body)
    ElMessage.success('已保存')
    dialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  }
}

async function remove(row: any) {
  await ElMessageBox.confirm('删除助手？', '提示')
  await deleteAssistant(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建助手</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="avatar" label="头像" width="70" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="model" label="模型" width="130" />
      <el-table-column label="知识库" width="140">
        <template #default="{ row }">{{ kbName(row.knowledge_base_id) }}</template>
      </el-table-column>
      <el-table-column prop="temperature" label="温度" width="80" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
            {{ row.enabled ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="persona" label="人设" show-overflow-tooltip />
      <el-table-column label="建议问法" width="100">
        <template #default="{ row }">
          {{ (row.suggested_prompts || []).length }} 条
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !rows.length" description="暂无助手" />
    <el-dialog v-model="dialog" title="AI 助手" width="620px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="头像字"><el-input v-model="form.avatar" maxlength="2" /></el-form-item>
        <el-form-item label="人设"><el-input v-model="form.persona" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="系统 Prompt">
          <el-input
            v-model="form.system_prompt"
            type="textarea"
            :rows="4"
            placeholder="留空则使用全局 chat_system 模板"
          />
        </el-form-item>
        <el-form-item label="建议问法">
          <el-input
            v-model="form.suggested_prompts_text"
            type="textarea"
            :rows="3"
            placeholder="每行一条，学员端空态展示"
          />
        </el-form-item>
        <el-form-item label="模型">
          <el-select v-model="form.model" filterable allow-create default-first-option style="width: 100%">
            <el-option label="gpt-4o-mini" value="gpt-4o-mini" />
            <el-option label="gpt-4o" value="gpt-4o" />
            <el-option label="deepseek-chat" value="deepseek-chat" />
            <el-option label="qwen-plus" value="qwen-plus" />
          </el-select>
        </el-form-item>
        <el-form-item label="温度"><el-slider v-model="form.temperature" :min="0" :max="1" :step="0.1" /></el-form-item>
        <el-form-item label="知识库">
          <el-select v-model="form.knowledge_base_id" clearable style="width: 100%">
            <el-option v-for="b in bases" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
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
  display: flex;
  gap: 8px;
}
</style>
