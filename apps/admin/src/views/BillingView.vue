<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

const tenants = ref<any[]>([])
const packs = ref<any[]>([])
const lti = ref<any>(null)
const tenantForm = reactive({ name: '', slug: '', status: 'active' })
const packForm = reactive({
  name: '',
  price: 299,
  days: 30,
  token_quota: 2000000,
  request_quota: 10000,
  description: '',
  enabled: true,
})
const assignForm = reactive({ tenant_id: 0, pack_id: 0 })
const userAssign = reactive({ user_id: 0, tenant_id: 0 })
const tenantDialog = ref(false)
const packDialog = ref(false)
const assignDialog = ref(false)
const userDialog = ref(false)

function demoUrl() {
  const launch = lti.value?.launch_url as string | undefined
  if (launch?.includes('/lti/launch')) return launch.replace(/\/launch\/?$/, '/demo')
  return 'http://127.0.0.1:8000/api/v1/lti/demo'
}

async function load() {
  ;[tenants.value, packs.value, lti.value] = await Promise.all([
    api('/billing/tenants'),
    api('/billing/packs'),
    api('/lti/config'),
  ])
  if (!assignForm.tenant_id && tenants.value[0]) assignForm.tenant_id = tenants.value[0].id
  if (!assignForm.pack_id && packs.value[0]) assignForm.pack_id = packs.value[0].id
  if (!userAssign.tenant_id && tenants.value[0]) userAssign.tenant_id = tenants.value[0].id
}

async function copyLaunch() {
  const url = lti.value?.launch_url || ''
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('Launch URL 已复制')
  } catch {
    ElMessage.info(url)
  }
}

async function assignUser() {
  try {
    await api('/billing/assign-user', { method: 'POST', body: JSON.stringify(userAssign) })
    ElMessage.success('用户已绑定租户')
    userDialog.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '绑定失败')
  }
}

async function createTenant() {
  try {
    await api('/billing/tenants', { method: 'POST', body: JSON.stringify(tenantForm) })
    ElMessage.success('租户已创建')
    tenantDialog.value = false
    tenantForm.name = ''
    tenantForm.slug = ''
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  }
}

async function createPack() {
  try {
    await api('/billing/packs', { method: 'POST', body: JSON.stringify(packForm) })
    ElMessage.success('用量包已创建')
    packDialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  }
}

async function assignPack() {
  try {
    await api('/billing/assign', { method: 'POST', body: JSON.stringify(assignForm) })
    ElMessage.success('已开通用量包')
    assignDialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '开通失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-alert
      type="info"
      :closable="false"
      title="多租户用量包：对话与批改成功调用会扣减 Token / 次数配额；额度用尽后学员端 AI 对话将拒绝。"
      style="margin-bottom: 14px"
    />

    <div class="toolbar">
      <el-button type="primary" @click="tenantDialog = true">新建租户</el-button>
      <el-button @click="packDialog = true">新建用量包</el-button>
      <el-button type="success" @click="assignDialog = true">为租户开通套餐</el-button>
      <el-button @click="userDialog = true">绑定用户到租户</el-button>
    </div>

    <el-card shadow="never" header="租户与消耗" style="margin-bottom: 14px">
      <el-table :data="tenants" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="租户" min-width="140" />
        <el-table-column prop="slug" label="Slug" width="140" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="套餐" min-width="120">
          <template #default="{ row }">{{ row.subscription?.pack_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="Token" min-width="160">
          <template #default="{ row }">
            <template v-if="row.subscription">
              {{ row.subscription.tokens_used }} / {{ row.subscription.token_quota }}
              <el-progress
                :percentage="Math.min(100, row.subscription.token_pct || 0)"
                :stroke-width="8"
                style="margin-top: 4px"
              />
            </template>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="调用次数" min-width="160">
          <template #default="{ row }">
            <template v-if="row.subscription">
              {{ row.subscription.requests_used }} / {{ row.subscription.request_quota }}
              <el-progress
                :percentage="Math.min(100, row.subscription.request_pct || 0)"
                :stroke-width="8"
                status="success"
                style="margin-top: 4px"
              />
            </template>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="到期" width="120">
          <template #default="{ row }">{{ row.subscription?.ends_at || '—' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-row :gutter="14">
      <el-col :span="14">
        <el-card shadow="never" header="用量包目录">
          <el-table :data="packs" style="width: 100%">
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="price" label="价格" width="90" />
            <el-table-column prop="days" label="天数" width="80" />
            <el-table-column prop="token_quota" label="Token 配额" width="120" />
            <el-table-column prop="request_quota" label="次数配额" width="100" />
            <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" header="LTI / LMS 对接">
          <p v-if="lti" class="muted">{{ lti.description }}</p>
          <el-descriptions v-if="lti" :column="1" size="small" border>
            <el-descriptions-item label="工具名">{{ lti.title }}</el-descriptions-item>
            <el-descriptions-item label="Launch URL">
              <code>{{ lti.launch_url }}</code>
              <el-button link type="primary" style="margin-left: 8px" @click="copyLaunch">复制</el-button>
            </el-descriptions-item>
            <el-descriptions-item label="说明">{{ lti.login_hint }}</el-descriptions-item>
          </el-descriptions>
          <p class="hint">
            本地演示页：
            <a :href="demoUrl()" target="_blank" rel="noreferrer">{{ demoUrl() }}</a>
          </p>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="tenantDialog" title="新建租户" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="tenantForm.name" placeholder="某某中学" />
        </el-form-item>
        <el-form-item label="Slug">
          <el-input v-model="tenantForm.slug" placeholder="school-a" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tenantDialog = false">取消</el-button>
        <el-button type="primary" @click="createTenant">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="packDialog" title="新建用量包" width="480px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="packForm.name" /></el-form-item>
        <el-form-item label="价格"><el-input-number v-model="packForm.price" :min="0" /></el-form-item>
        <el-form-item label="有效天数"><el-input-number v-model="packForm.days" :min="1" /></el-form-item>
        <el-form-item label="Token 配额">
          <el-input-number v-model="packForm.token_quota" :min="1000" :step="100000" />
        </el-form-item>
        <el-form-item label="次数配额">
          <el-input-number v-model="packForm.request_quota" :min="10" :step="100" />
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="packForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="packDialog = false">取消</el-button>
        <el-button type="primary" @click="createPack">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignDialog" title="开通用量包" width="420px">
      <el-form label-width="80px">
        <el-form-item label="租户">
          <el-select v-model="assignForm.tenant_id" style="width: 100%">
            <el-option v-for="t in tenants" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用量包">
          <el-select v-model="assignForm.pack_id" style="width: 100%">
            <el-option
              v-for="p in packs"
              :key="p.id"
              :label="`${p.name}（¥${p.price}）`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialog = false">取消</el-button>
        <el-button type="primary" @click="assignPack">开通</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="userDialog" title="绑定用户到租户" width="420px">
      <el-form label-width="90px">
        <el-form-item label="用户 ID">
          <el-input-number v-model="userAssign.user_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="租户">
          <el-select v-model="userAssign.tenant_id" style="width: 100%">
            <el-option v-for="t in tenants" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog = false">取消</el-button>
        <el-button type="primary" @click="assignUser">绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.muted {
  color: #64748b;
  margin: 0 0 12px;
  line-height: 1.5;
  font-size: 13px;
}
.hint {
  margin-top: 14px;
  font-size: 13px;
  color: #475569;
}
code {
  font-size: 12px;
  word-break: break-all;
}
</style>
