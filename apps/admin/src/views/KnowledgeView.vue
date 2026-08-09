<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addDoc,
  createBase,
  deleteDoc,
  fetchBases,
  fetchDocs,
  fetchEmbeddingConfig,
  fetchEmbeddingStatus,
  generateCourseFromKb,
  generateQuestionsFromKb,
  reindexKb,
  saveEmbeddingConfig,
  searchKb,
  uploadKbDoc,
} from '../lib/api'

const router = useRouter()
const bases = ref<any[]>([])
const docs = ref<any[]>([])
const activeKb = ref<number | null>(null)
const baseDialog = ref(false)
const docDialog = ref(false)
const qDialog = ref(false)
const courseDialog = ref(false)
const embDialog = ref(false)
const uploading = ref(false)
const generatingQ = ref(false)
const generatingC = ref(false)
const savingEmb = ref(false)
const probingEmb = ref(false)
const baseForm = reactive({ name: '', description: '' })
const docForm = reactive({ title: '', content: '' })
const qForm = reactive({ count: 5, difficulty: 2, topic: '', query: '' })
const courseForm = reactive({
  title: '',
  chapter_count: 3,
  query: '',
  create_assistant: true,
})
const embForm = reactive({
  mode: 'hash',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  model: 'text-embedding-3-small',
  has_key: false,
  api_key_masked: '',
})
const query = ref('什么是线面角')
const hits = ref<any[]>([])
const embStatus = ref<any | null>(null)
const lastGen = ref<any | null>(null)
const uploadInput = ref<HTMLInputElement | null>(null)

async function loadBases() {
  bases.value = await fetchBases()
  if (!activeKb.value && bases.value[0]) {
    activeKb.value = bases.value[0].id
    await loadDocs()
  }
}

async function loadDocs() {
  if (!activeKb.value) return
  docs.value = await fetchDocs(activeKb.value)
}

async function loadEmb(probe = false) {
  try {
    const [status, cfg] = await Promise.all([
      fetchEmbeddingStatus(probe),
      fetchEmbeddingConfig(),
    ])
    embStatus.value = status
    embForm.mode = cfg.mode || 'auto'
    embForm.base_url = cfg.base_url || 'https://api.openai.com/v1'
    embForm.model = cfg.model || 'text-embedding-3-small'
    embForm.has_key = !!cfg.has_key
    embForm.api_key_masked = cfg.api_key_masked || ''
    if (!embForm.api_key) embForm.api_key = ''
  } catch {
    embStatus.value = null
  }
}

async function openEmbDialog() {
  await loadEmb(false)
  embDialog.value = true
}

async function probeEmb() {
  probingEmb.value = true
  try {
    embStatus.value = await fetchEmbeddingStatus(true)
    if (embStatus.value?.api_live) ElMessage.success('Embedding 连通成功')
    else ElMessage.warning(embStatus.value?.probe_error || embStatus.value?.hint || '探测未通过，将使用本地哈希')
  } catch (e: any) {
    ElMessage.error(e?.message || '探测失败')
  } finally {
    probingEmb.value = false
  }
}

async function saveEmb() {
  savingEmb.value = true
  try {
    const body: Record<string, unknown> = {
      mode: embForm.mode,
      base_url: embForm.base_url,
      model: embForm.model,
    }
    if (embForm.api_key.trim()) body.api_key = embForm.api_key.trim()
    const r = await saveEmbeddingConfig(body as any)
    embStatus.value = r.status
    embForm.has_key = !!r.config?.has_key
    embForm.api_key_masked = r.config?.api_key_masked || ''
    embForm.api_key = ''
    embDialog.value = false
    ElMessage.success('Embedding 配置已保存。若切换了后端，请点击「重建向量索引」。')
    if (activeKb.value && embForm.mode !== 'hash') {
      await ElMessageBox.confirm('是否立即对当前知识库重建向量索引？', '同步索引', {
        type: 'info',
        confirmButtonText: '重建',
        cancelButtonText: '稍后',
      })
        .then(() => doReindex())
        .catch(() => undefined)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    savingEmb.value = false
  }
}

async function saveBase() {
  await createBase(baseForm)
  baseDialog.value = false
  ElMessage.success('知识库已创建')
  await loadBases()
}

async function saveDoc() {
  if (!activeKb.value) return
  await addDoc(activeKb.value, docForm)
  docDialog.value = false
  docForm.title = ''
  docForm.content = ''
  ElMessage.success('文档已添加并完成向量切片')
  await loadDocs()
  await loadBases()
  await loadEmb()
}

async function onPickFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !activeKb.value) return
  uploading.value = true
  try {
    const doc = await uploadKbDoc(activeKb.value, file)
    ElMessage.success(`已上传并索引：${doc.title}（${doc.source_type || 'file'}）`)
    await loadDocs()
    await loadBases()
    await loadEmb()
  } catch (e: any) {
    ElMessage.error(e?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function removeDoc(row: any) {
  await ElMessageBox.confirm('删除文档？', '提示')
  await deleteDoc(row.id)
  await loadDocs()
  await loadBases()
}

async function doReindex() {
  if (!activeKb.value) return
  const r = await reindexKb(activeKb.value)
  ElMessage.success(
    `已重建索引：${r.docs} 文档 / ${r.chunks} 切片 · 后端 ${r.backend || 'hash'}（${r.model || ''}）`,
  )
  await loadBases()
  await loadEmb()
}

async function doSearch() {
  if (!activeKb.value) return
  const r = await searchKb({ kb_id: activeKb.value, query: query.value, top_k: 5 })
  hits.value = r.items || []
  if (r.embedding) embStatus.value = r.embedding
}

async function doGenQuestions() {
  if (!activeKb.value) return
  generatingQ.value = true
  try {
    const r = await generateQuestionsFromKb(activeKb.value, { ...qForm })
    lastGen.value = { kind: 'questions', ...r }
    qDialog.value = false
    ElMessage.success(
      `已生成 ${r.count} 道题并写入题库（${r.source === 'llm' ? '大模型' : '本地演示'}）`,
    )
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败')
  } finally {
    generatingQ.value = false
  }
}

async function doGenCourse() {
  if (!activeKb.value) return
  generatingC.value = true
  try {
    const r = await generateCourseFromKb(activeKb.value, { ...courseForm })
    lastGen.value = { kind: 'course', ...r }
    courseDialog.value = false
    const asst = r.assistant?.name ? `；助手「${r.assistant.name}」` : ''
    ElMessage.success(
      `已生成课程《${r.title}》${asst}（${r.source === 'llm' ? '大模型' : '本地演示'}）`,
    )
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败')
  } finally {
    generatingC.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadBases(), loadEmb(true)])
})
</script>

<template>
  <div class="wrap">
    <aside>
      <div class="toolbar">
        <el-button type="primary" size="small" @click="baseDialog = true">新建知识库</el-button>
      </div>
      <el-menu
        :default-active="String(activeKb || '')"
        @select="(i: string) => { activeKb = Number(i); loadDocs(); hits = []; lastGen = null }"
      >
        <el-menu-item v-for="b in bases" :key="b.id" :index="String(b.id)">
          {{ b.name }}（{{ b.doc_count }} 文 / {{ b.chunk_count || 0 }} 片）
        </el-menu-item>
      </el-menu>
    </aside>
    <section>
      <el-alert
        v-if="embStatus"
        :type="embStatus.api_live === false ? 'warning' : embStatus.prefer === 'api' ? 'success' : 'info'"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        :title="
          embStatus.prefer === 'api'
            ? `向量后端：Embedding API（${embStatus.model}）`
            : '向量后端：本地哈希（稳定离线）'
        "
        :description="embStatus.hint"
      />
      <el-alert
        type="success"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        title="教材闭环：上传 PDF/MD/TXT/DOCX → 切片入库 → 生成课程 / 题库 → 绑定 AI 助教"
        description="未配置大模型时，生成能力会降级为本地演示逻辑，便于无 Key 验收。"
      />

      <div class="toolbar">
        <el-button type="primary" :disabled="!activeKb" @click="docDialog = true">粘贴文本</el-button>
        <el-button :disabled="!activeKb || uploading" :loading="uploading" @click="uploadInput?.click()">
          上传教材
        </el-button>
        <input
          ref="uploadInput"
          type="file"
          accept=".pdf,.md,.markdown,.txt,.docx,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          class="hidden-file"
          @change="onPickFile"
        />
        <el-button @click="openEmbDialog">Embedding 配置</el-button>
        <el-button :loading="probingEmb" @click="probeEmb">测试连通</el-button>
        <el-button :disabled="!activeKb" @click="doReindex">重建向量索引</el-button>
        <el-button type="success" :disabled="!activeKb" @click="qDialog = true">生成题库</el-button>
        <el-button type="warning" :disabled="!activeKb" @click="courseDialog = true">生成课程</el-button>
      </div>

      <el-table :data="docs" stripe>
        <el-table-column prop="title" label="标题" width="180" />
        <el-table-column prop="source_type" label="来源" width="80" />
        <el-table-column prop="source_filename" label="文件名" width="160" show-overflow-tooltip />
        <el-table-column prop="content" label="内容预览" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeDoc(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-card v-if="lastGen" shadow="never" style="margin-top: 16px">
        <template #header>
          最近生成结果
          <el-tag size="small" style="margin-left: 8px">{{ lastGen.source }}</el-tag>
        </template>
        <template v-if="lastGen.kind === 'questions'">
          <p>已写入题库 {{ lastGen.count }} 道。</p>
          <el-button size="small" type="primary" @click="router.push('/questions')">去题库查看</el-button>
          <el-table :data="lastGen.questions || []" size="small" style="margin-top: 10px">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="type" label="题型" width="90" />
            <el-table-column prop="stem" label="题干" show-overflow-tooltip />
            <el-table-column prop="difficulty" label="难度" width="70" />
          </el-table>
        </template>
        <template v-else>
          <p>
            课程 #{{ lastGen.course_id }} 《{{ lastGen.title }}》· {{ lastGen.chapter_count }} 章 ·
            {{ lastGen.status }}
          </p>
          <p v-if="lastGen.assistant">
            AI 助教：{{ lastGen.assistant.name }}
            <span v-if="lastGen.assistant.created">（新建）</span>
            <span v-else>（已存在）</span>
          </p>
          <el-button size="small" type="primary" @click="router.push('/courses')">去课程管理</el-button>
          <el-button size="small" @click="router.push('/assistants')">去助手管理</el-button>
        </template>
      </el-card>

      <el-card shadow="never" style="margin-top: 16px">
        <template #header>检索测试（向量 + 关键词）</template>
        <div class="search">
          <el-input v-model="query" placeholder="输入查询" @keyup.enter="doSearch" />
          <el-button type="primary" :disabled="!activeKb" @click="doSearch">搜索</el-button>
        </div>
        <el-table :data="hits" size="small" style="margin-top: 10px">
          <el-table-column prop="title" label="文档" width="160" />
          <el-table-column prop="snippet" label="片段" />
          <el-table-column prop="score" label="分数" width="90" />
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="backend" label="向量" width="90" />
        </el-table>
      </el-card>
    </section>

    <el-dialog v-model="embDialog" title="向量后端 Embedding 配置" width="560px">
      <el-form label-width="110px">
        <el-form-item label="模式">
          <el-radio-group v-model="embForm.mode">
            <el-radio value="hash">本地哈希（推荐离线）</el-radio>
            <el-radio value="auto">自动（有 API 则用）</el-radio>
            <el-radio value="api">强制 Embedding API</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input
            v-model="embForm.base_url"
            placeholder="https://api.openai.com/v1"
            :disabled="embForm.mode === 'hash'"
          />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="embForm.api_key"
            type="password"
            show-password
            :placeholder="embForm.has_key ? `已保存 ${embForm.api_key_masked}（留空不修改）` : 'sk-...'"
            :disabled="embForm.mode === 'hash'"
          />
        </el-form-item>
        <el-form-item label="模型">
          <el-input
            v-model="embForm.model"
            placeholder="text-embedding-3-small"
            :disabled="embForm.mode === 'hash'"
          />
        </el-form-item>
        <p class="hint">
          须使用支持 <code>/v1/embeddings</code> 的接口。DeepSeek 等纯对话接口不可用，请选本地哈希或 OpenAI /
          兼容 Embedding 服务。变更后端后务必重建索引，避免维度不一致。
        </p>
      </el-form>
      <template #footer>
        <el-button :loading="probingEmb" :disabled="embForm.mode === 'hash'" @click="probeEmb">
          测试连通
        </el-button>
        <el-button @click="embDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingEmb" @click="saveEmb">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="baseDialog" title="知识库" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="baseForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="baseForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="baseDialog = false">取消</el-button>
        <el-button type="primary" @click="saveBase">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="docDialog" title="粘贴文本文档" width="640px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="docForm.title" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="docForm.content" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="docDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDoc">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qDialog" title="从知识库生成题库" width="520px">
      <el-form label-width="100px">
        <el-form-item label="题目数量">
          <el-input-number v-model="qForm.count" :min="1" :max="20" />
        </el-form-item>
        <el-form-item label="难度">
          <el-input-number v-model="qForm.difficulty" :min="1" :max="5" />
        </el-form-item>
        <el-form-item label="主题侧重">
          <el-input v-model="qForm.topic" placeholder="如：立体几何 / 线面角" />
        </el-form-item>
        <el-form-item label="检索提示">
          <el-input v-model="qForm.query" placeholder="可选，用于从知识库召回相关片段" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="qDialog = false">取消</el-button>
        <el-button type="primary" :loading="generatingQ" @click="doGenQuestions">生成并入库</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="courseDialog" title="从知识库生成 AI 课程" width="520px">
      <el-form label-width="110px">
        <el-form-item label="课程标题">
          <el-input v-model="courseForm.title" placeholder="留空则使用知识库名称" />
        </el-form-item>
        <el-form-item label="章节数">
          <el-input-number v-model="courseForm.chapter_count" :min="1" :max="8" />
        </el-form-item>
        <el-form-item label="检索提示">
          <el-input v-model="courseForm.query" placeholder="可选" />
        </el-form-item>
        <el-form-item label="创建 AI 助教">
          <el-switch v-model="courseForm.create_assistant" />
          <span class="hint">自动绑定本知识库，供学员端教学辅导</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialog = false">取消</el-button>
        <el-button type="primary" :loading="generatingC" @click="doGenCourse">生成课程</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.wrap {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  background: #fff;
  border-radius: 12px;
  padding: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.search {
  display: flex;
  gap: 8px;
}
.hidden-file {
  display: none;
}
.hint {
  margin-left: 10px;
  color: #64748b;
  font-size: 12px;
}
</style>
