<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  aiScoreGrade,
  fetchGradeQueue,
  markGradeQc,
  reviewGrade,
  sampleGradeQc,
} from '../lib/api'

const rows = ref<any[]>([])
const filter = ref('')
const qcFilter = ref('')
const dialog = ref(false)
const qcDialog = ref(false)
const current = ref<any>(null)
const form = reactive({ teacher_score: 0, teacher_feedback: '' })
const qcForm = reactive({ result: 'passed' as 'passed' | 'failed', note: '' })
const sampleN = ref(5)
const sampling = ref(false)

async function load() {
  if (qcFilter.value) {
    rows.value = await fetchGradeQueue('', qcFilter.value)
  } else {
    rows.value = await fetchGradeQueue(filter.value)
  }
}

function openReview(row: any) {
  current.value = row
  form.teacher_score = row.teacher_score ?? row.ai_score ?? 0
  form.teacher_feedback = row.teacher_feedback || row.ai_feedback || ''
  dialog.value = true
}

function openQc(row: any) {
  current.value = row
  qcForm.result = 'passed'
  qcForm.note = row.qc_note || ''
  qcDialog.value = true
}

async function runAi(row: any) {
  await aiScoreGrade(row.id)
  ElMessage.success('AI 初评完成')
  await load()
}

async function saveReview() {
  if (!current.value) return
  await reviewGrade(current.value.id, { ...form })
  ElMessage.success('复核已提交')
  dialog.value = false
  await load()
}

async function saveQc() {
  if (!current.value) return
  await markGradeQc(current.value.id, { ...qcForm })
  ElMessage.success(qcForm.result === 'passed' ? '质检通过' : '已标记质检问题')
  qcDialog.value = false
  await load()
}

async function runSample() {
  sampling.value = true
  try {
    const picked = await sampleGradeQc({ n: sampleN.value, max_confidence: 0.85 })
    ElMessage.success(picked.length ? `已抽检 ${picked.length} 条` : '暂无可抽检任务')
    qcFilter.value = 'sampled'
    filter.value = ''
    await load()
  } finally {
    sampling.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-select v-model="filter" clearable placeholder="状态筛选" style="width: 160px" @change="() => { qcFilter = ''; load() }">
        <el-option label="待处理+已初评" value="" />
        <el-option label="待初评" value="pending" />
        <el-option label="AI 已评" value="ai_scored" />
        <el-option label="已复核" value="teacher_reviewed" />
      </el-select>
      <el-select v-model="qcFilter" clearable placeholder="质检筛选" style="width: 140px" @change="() => { filter = ''; load() }">
        <el-option label="待质检" value="sampled" />
        <el-option label="质检通过" value="passed" />
        <el-option label="质检不通过" value="failed" />
      </el-select>
      <el-input-number v-model="sampleN" :min="1" :max="20" size="small" />
      <el-button type="warning" :loading="sampling" @click="runSample">抽样质检</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="学员" min-width="110">
        <template #default="{ row }">
          {{ row.student_name || `用户 #${row.user_id}` }}
        </template>
      </el-table-column>
      <el-table-column prop="stem" label="题干" min-width="200" show-overflow-tooltip />
      <el-table-column prop="answer_text" label="作答" min-width="140" show-overflow-tooltip />
      <el-table-column label="AI 分" width="90">
        <template #default="{ row }">{{ row.ai_score ?? '-' }} / {{ row.max_score }}</template>
      </el-table-column>
      <el-table-column prop="ai_confidence" label="置信度" width="90" />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column prop="qc_status" label="质检" width="100" />
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="runAi(row)">AI 初评</el-button>
          <el-button link type="primary" @click="openReview(row)">复核</el-button>
          <el-button link type="warning" @click="openQc(row)">质检</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="教师复核" width="640px">
      <template v-if="current">
        <p><b>学员：</b>{{ current.student_name || `#${current.user_id}` }}</p>
        <p><b>题干：</b>{{ current.stem }}</p>
        <p><b>作答：</b>{{ current.answer_text }}</p>
        <p><b>AI 评语：</b>{{ current.ai_feedback }}</p>
        <el-form label-width="90px" style="margin-top: 12px">
          <el-form-item label="复核分数">
            <el-input-number v-model="form.teacher_score" :min="0" :max="current.max_score" :step="0.5" />
          </el-form-item>
          <el-form-item label="复核评语">
            <el-input v-model="form.teacher_feedback" type="textarea" :rows="4" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="saveReview">提交复核</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qcDialog" title="抽样质检" width="560px">
      <template v-if="current">
        <p><b>学员：</b>{{ current.student_name || `#${current.user_id}` }}</p>
        <p><b>题干：</b>{{ current.stem }}</p>
        <p><b>作答：</b>{{ current.answer_text }}</p>
        <p><b>AI：</b>{{ current.ai_score }} / {{ current.max_score }} · 置信度 {{ current.ai_confidence }}</p>
        <p><b>教师分：</b>{{ current.teacher_score ?? '-' }} · {{ current.teacher_feedback || '无评语' }}</p>
        <el-form label-width="90px" style="margin-top: 12px">
          <el-form-item label="结论">
            <el-radio-group v-model="qcForm.result">
              <el-radio value="passed">通过</el-radio>
              <el-radio value="failed">不通过</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="qcForm.note" type="textarea" :rows="3" placeholder="偏差原因、改进建议…" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="qcDialog = false">取消</el-button>
        <el-button type="primary" @click="saveQc">提交质检</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
  align-items: center;
}
</style>
