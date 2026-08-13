<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchStudentHistory, type StudentHistory } from '../lib/api'

const props = defineProps<{
  studentId: number | null
  modelValue: boolean
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const loading = ref(false)
const error = ref('')
const history = ref<StudentHistory | null>(null)
const tab = ref('progress')

async function load(id: number) {
  loading.value = true
  error.value = ''
  history.value = null
  try {
    history.value = await fetchStudentHistory(id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.studentId] as const,
  ([open, id]) => {
    if (open && id) void load(id)
  },
)

function close() {
  emit('update:modelValue', false)
}

function fmtTime(v?: string | null) {
  if (!v) return '-'
  return v.replace('T', ' ').slice(0, 19)
}

function statusLabel(s: string) {
  if (s === 'completed') return '已完成'
  if (s === 'started') return '进行中'
  return s || '-'
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    size="560px"
    :title="history ? `${history.display_name} · 学习历史` : '学生学习历史'"
    @close="close"
  >
    <div v-loading="loading" class="hist">
      <el-alert v-if="error" type="error" :title="error" show-icon class="mb" />
      <template v-if="history">
        <p class="meta">
          {{ history.email }}
          <template v-if="history.class_names.length"> · {{ history.class_names.join('、') }}</template>
        </p>
        <div class="kpis">
          <div><b>{{ history.summary.progress_completed ?? 0 }}</b><span>完成进度</span></div>
          <div><b>{{ history.summary.avg_score_rate ?? 0 }}%</b><span>得分率</span></div>
          <div><b>{{ history.summary.wrong_open ?? 0 }}</b><span>未掌握错题</span></div>
          <div><b>{{ history.summary.vocab_completed_days ?? 0 }}</b><span>背单词打卡天</span></div>
          <div><b>{{ history.summary.streak_days ?? 0 }}</b><span>连续打卡</span></div>
          <div><b>{{ history.summary.submissions ?? 0 }}</b><span>交卷</span></div>
        </div>

        <el-tabs v-model="tab">
          <el-tab-pane label="课程进度" name="progress">
            <el-table :data="history.progress" size="small" empty-text="暂无课程进度记录" max-height="420">
              <el-table-column prop="course_id" label="课程" min-width="110" />
              <el-table-column prop="item_id" label="课时/项目" min-width="120" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">{{ statusLabel(row.status) }}</template>
              </el-table-column>
              <el-table-column prop="score" label="分" width="60" />
              <el-table-column label="更新时间" min-width="140">
                <template #default="{ row }">{{ fmtTime(row.updated_at) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="交卷记录" name="subs">
            <el-table :data="history.submissions" size="small" empty-text="暂无交卷" max-height="420">
              <el-table-column prop="paper_title" label="试卷" min-width="140" />
              <el-table-column label="得分" width="110">
                <template #default="{ row }">{{ row.score }}/{{ row.total }}（{{ row.rate }}%）</template>
              </el-table-column>
              <el-table-column label="时间" min-width="140">
                <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="背单词" name="vocab">
            <el-table :data="history.vocab_logs" size="small" empty-text="暂无背单词记录" max-height="420">
              <el-table-column prop="day" label="日期" width="110" />
              <el-table-column label="打卡" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.completed ? 'success' : 'info'">
                    {{ row.completed ? '完成' : '未完成' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="新词/复习" width="100">
                <template #default="{ row }">{{ row.new_count }}/{{ row.review_count }}</template>
              </el-table-column>
              <el-table-column label="测验" width="100">
                <template #default="{ row }">{{ row.quiz_correct }}/{{ row.quiz_total }}</template>
              </el-table-column>
              <el-table-column prop="stars_earned" label="星" width="60" />
              <el-table-column prop="bank" label="词库" min-width="100" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="错题" name="wrong">
            <el-table :data="history.wrong_items" size="small" empty-text="暂无错题" max-height="420">
              <el-table-column prop="knowledge_points" label="知识点" min-width="140" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.mastered ? 'success' : 'warning'">
                    {{ row.mastered ? '已掌握' : '未掌握' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="user_answer" label="作答" min-width="120" show-overflow-tooltip />
              <el-table-column label="时间" min-width="140">
                <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="普通打卡" name="checkin">
            <el-table :data="history.checkins" size="small" empty-text="暂无打卡" max-height="420">
              <el-table-column prop="day" label="日期" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </el-drawer>
</template>

<style scoped>
.hist {
  min-height: 240px;
}
.mb {
  margin-bottom: 12px;
}
.meta {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 13px;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.kpis div {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.kpis b {
  font-size: 18px;
  color: #0f172a;
}
.kpis span {
  font-size: 12px;
  color: #64748b;
}
</style>
