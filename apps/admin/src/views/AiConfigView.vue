<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createPrompt,
  createProvider,
  deleteProvider,
  exportUsageCostCsv,
  fetchPrompts,
  fetchProviders,
  fetchUsage,
  fetchUsageCost,
  fetchUsageSummary,
  importProviderEnv,
  saveUsagePrices,
  testProvider,
  updatePrompt,
  updateProvider,
} from '../lib/api'

const tab = ref('providers')
const providers = ref<any[]>([])
const prompts = ref<any[]>([])
const usage = ref<any[]>([])
const summary = ref<any>(null)
const cost = ref<any>(null)
const costDays = ref(0)
const priceDraft = ref('')

const pDialog = ref(false)
const editingPid = ref<number | null>(null)
const pForm = reactive({
  name: '',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  default_model: 'gpt-4o-mini',
  enabled: true,
  is_default: true,
})

const prDialog = ref(false)
const editingPr = ref<any | null>(null)
const prForm = reactive({
  key: 'chat_system',
  name: '',
  content: '',
  active: true,
})

async function loadCost() {
  cost.value = await fetchUsageCost(costDays.value)
  priceDraft.value = JSON.stringify(cost.value?.price_table || {}, null, 2)
}

async function load() {
  ;[providers.value, prompts.value, usage.value, summary.value] = await Promise.all([
    fetchProviders(),
    fetchPrompts(),
    fetchUsage(),
    fetchUsageSummary(),
  ])
  await loadCost()
}

function openProvider(row?: any) {
  editingPid.value = row?.id ?? null
  Object.assign(pForm, {
    name: row?.name || '',
    base_url: row?.base_url || 'https://api.openai.com/v1',
    api_key: '',
    default_model: row?.default_model || 'gpt-4o-mini',
    enabled: row?.enabled ?? true,
    is_default: row?.is_default ?? false,
  })
  pDialog.value = true
}

async function saveProvider() {
  if (editingPid.value) await updateProvider(editingPid.value, pForm)
  else await createProvider(pForm)
  ElMessage.success('Provider 已保存')
  pDialog.value = false
  await load()
}

async function removeProvider(row: any) {
  await ElMessageBox.confirm(`删除 Provider「${row.name}」？`, '提示')
  await deleteProvider(row.id)
  await load()
}

async function doTest(row: any) {
  try {
    const r = await testProvider(row.id)
    if (r.ok) ElMessage.success(`连通成功，延迟 ${r.latency_ms}ms`)
    else ElMessage.error(r.detail || '连通失败')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '连通失败')
  }
}

async function doImport() {
  try {
    await importProviderEnv()
    ElMessage.success('已从环境变量导入')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  }
}

function openPrompt(row?: any) {
  editingPr.value = row || null
  Object.assign(prForm, {
    key: row?.key || 'chat_system',
    name: row?.name || '',
    content: row?.content || '',
    active: row?.active ?? true,
  })
  prDialog.value = true
}

async function savePrompt() {
  if (editingPr.value) await updatePrompt(editingPr.value.id, prForm)
  else await createPrompt(prForm)
  ElMessage.success('Prompt 已保存（新建会升版本）')
  prDialog.value = false
  await load()
}

async function savePrices() {
  try {
    const prices = JSON.parse(priceDraft.value || '{}')
    await saveUsagePrices(prices)
    ElMessage.success('单价已保存')
    await loadCost()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : 'JSON 无效')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="模型 Provider" name="providers">
        <div class="toolbar">
          <el-button type="primary" @click="openProvider()">新建 Provider</el-button>
          <el-button @click="doImport">从环境变量导入</el-button>
        </div>
        <el-alert
          type="info"
          :closable="false"
          title="支持 OpenAI 兼容协议（/v1/chat/completions）。密钥仅存服务端，列表中只显示掩码。"
          style="margin-bottom: 12px"
        />
        <el-table :data="providers" stripe>
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="base_url" label="Base URL" min-width="200" />
          <el-table-column prop="default_model" label="默认模型" width="140" />
          <el-table-column prop="api_key_masked" label="API Key" width="140" />
          <el-table-column prop="enabled" label="启用" width="80" />
          <el-table-column prop="is_default" label="默认" width="80" />
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <el-button link type="primary" @click="openProvider(row)">编辑</el-button>
              <el-button link type="primary" @click="doTest(row)">测试</el-button>
              <el-button link type="danger" @click="removeProvider(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Prompt 版本" name="prompts">
        <div class="toolbar">
          <el-button type="primary" @click="openPrompt()">新建 / 升版</el-button>
        </div>
        <el-table :data="prompts" stripe>
          <el-table-column prop="key" label="Key" width="140" />
          <el-table-column prop="name" label="名称" width="160" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="active" label="启用" width="80" />
          <el-table-column prop="content" label="内容" show-overflow-tooltip />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" @click="openPrompt(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="调用用量" name="usage">
        <div v-if="summary" class="stats">
          <div class="stat"><b>{{ summary.total_calls }}</b><span>总调用</span></div>
          <div class="stat"><b>{{ summary.success_calls }}</b><span>成功</span></div>
          <div class="stat"><b>{{ summary.fail_calls }}</b><span>失败</span></div>
          <div class="stat"><b>{{ summary.prompt_tokens + summary.completion_tokens }}</b><span>估算 Token</span></div>
          <div class="stat"><b>{{ summary.avg_latency_ms }}ms</b><span>平均延迟</span></div>
        </div>
        <el-table :data="usage" stripe>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="purpose" label="用途" width="100" />
          <el-table-column prop="model" label="模型" width="140" />
          <el-table-column prop="prompt_tokens" label="Prompt" width="90" />
          <el-table-column prop="completion_tokens" label="补全" width="90" />
          <el-table-column prop="latency_ms" label="延迟" width="90" />
          <el-table-column prop="success" label="成功" width="80" />
          <el-table-column prop="error" label="错误" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="180" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="成本看板" name="cost">
        <div class="toolbar">
          <el-select v-model="costDays" style="width: 140px" @change="loadCost">
            <el-option :value="0" label="全部时间" />
            <el-option :value="7" label="近 7 天" />
            <el-option :value="30" label="近 30 天" />
            <el-option :value="90" label="近 90 天" />
          </el-select>
          <el-button @click="exportUsageCostCsv(costDays)">导出 CSV</el-button>
        </div>
        <div v-if="cost" class="stats">
          <div class="stat"><b>${{ cost.total_cost_usd }}</b><span>估算总成本</span></div>
        </div>
        <p class="note">{{ cost?.note }}</p>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-card shadow="never" header="按模型">
              <el-table :data="Object.entries(cost?.by_model || {}).map(([k, v]: any) => ({ model: k, ...v }))" size="small">
                <el-table-column prop="model" label="模型" />
                <el-table-column prop="calls" label="次数" width="70" />
                <el-table-column prop="cost_usd" label="USD" width="100" />
              </el-table>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never" header="按用途">
              <el-table :data="Object.entries(cost?.by_purpose || {}).map(([k, v]: any) => ({ purpose: k, ...v }))" size="small">
                <el-table-column prop="purpose" label="用途" />
                <el-table-column prop="calls" label="次数" width="70" />
                <el-table-column prop="cost_usd" label="USD" width="100" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
        <el-card shadow="never" header="按日" style="margin-top: 14px">
          <el-table :data="Object.entries(cost?.by_day || {}).map(([k, v]: any) => ({ day: k, ...v }))" size="small">
            <el-table-column prop="day" label="日期" />
            <el-table-column prop="calls" label="次数" width="100" />
            <el-table-column prop="cost_usd" label="USD" width="120" />
          </el-table>
        </el-card>
        <el-card shadow="never" header="模型单价（USD / 1K tokens）" style="margin-top: 14px">
          <el-input v-model="priceDraft" type="textarea" :rows="8" />
          <el-button type="primary" style="margin-top: 10px" @click="savePrices">保存单价</el-button>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="pDialog" :title="editingPid ? '编辑 Provider' : '新建 Provider'" width="560px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="pForm.name" /></el-form-item>
        <el-form-item label="Base URL"><el-input v-model="pForm.base_url" /></el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="pForm.api_key"
            type="password"
            show-password
            :placeholder="editingPid ? '留空则保留原密钥' : 'sk-...'"
          />
        </el-form-item>
        <el-form-item label="默认模型"><el-input v-model="pForm.default_model" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="pForm.enabled" /></el-form-item>
        <el-form-item label="设为默认"><el-switch v-model="pForm.is_default" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProvider">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="prDialog" title="Prompt" width="640px">
      <el-form label-width="80px">
        <el-form-item label="Key">
          <el-select v-model="prForm.key" allow-create filterable style="width: 100%">
            <el-option label="chat_system" value="chat_system" />
            <el-option label="rag_wrap" value="rag_wrap" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="prForm.name" /></el-form-item>
        <el-form-item label="内容">
          <el-input v-model="prForm.content" type="textarea" :rows="10" placeholder="rag_wrap 可用 {context}" />
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="prForm.active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="prDialog = false">取消</el-button>
        <el-button type="primary" @click="savePrompt">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.stat {
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 12px;
  padding: 12px 16px;
  min-width: 120px;
}
.stat b {
  display: block;
  font-size: 1.25rem;
  color: var(--edu-brand, #0f6b5c);
}
.stat span {
  color: var(--edu-muted, #667);
  font-size: 0.85rem;
}
.note {
  color: var(--edu-muted, #667);
  font-size: 0.9rem;
}
</style>
