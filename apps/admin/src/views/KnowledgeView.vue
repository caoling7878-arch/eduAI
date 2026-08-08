<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addDoc,
  createBase,
  deleteDoc,
  fetchBases,
  fetchDocs,
  fetchEmbeddingStatus,
  reindexKb,
  searchKb,
} from '../lib/api'

const bases = ref<any[]>([])
const docs = ref<any[]>([])
const activeKb = ref<number | null>(null)
const baseDialog = ref(false)
const docDialog = ref(false)
const baseForm = reactive({ name: '', description: '' })
const docForm = reactive({ title: '', content: '' })
const query = ref('什么是线面角')
const hits = ref<any[]>([])
const embStatus = ref<any | null>(null)

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

async function loadEmb() {
  try {
    embStatus.value = await fetchEmbeddingStatus()
  } catch {
    embStatus.value = null
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

onMounted(async () => {
  await Promise.all([loadBases(), loadEmb()])
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
        @select="(i: string) => { activeKb = Number(i); loadDocs(); hits = [] }"
      >
        <el-menu-item v-for="b in bases" :key="b.id" :index="String(b.id)">
          {{ b.name }}（{{ b.doc_count }} 文 / {{ b.chunk_count || 0 }} 片）
        </el-menu-item>
      </el-menu>
    </aside>
    <section>
      <el-alert
        v-if="embStatus"
        :type="embStatus.api_ready ? 'success' : 'info'"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        :title="embStatus.api_ready ? `向量后端：真实 Embedding（${embStatus.model}）` : '向量后端：本地哈希回退'"
        :description="embStatus.hint"
      />
      <div class="toolbar">
        <el-button type="primary" :disabled="!activeKb" @click="docDialog = true">添加文档</el-button>
        <el-button :disabled="!activeKb" @click="doReindex">重建向量索引</el-button>
      </div>
      <el-table :data="docs" stripe>
        <el-table-column prop="title" label="标题" width="200" />
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeDoc(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

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

    <el-dialog v-model="docDialog" title="文档" width="640px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="docForm.title" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="docForm.content" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="docDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDoc">保存</el-button>
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
  gap: 8px;
  margin-bottom: 10px;
}
.search {
  display: flex;
  gap: 8px;
}
</style>
