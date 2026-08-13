<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StudentHistoryDrawer from '../components/StudentHistoryDrawer.vue'
import {
  fetchTeacherHub,
  type TeacherHub,
} from '../lib/api'

const router = useRouter()
const hub = ref<TeacherHub | null>(null)
const loading = ref(true)
const error = ref('')
const activeClassId = ref<number | null>(null)
const historyOpen = ref(false)
const historyStudentId = ref<number | null>(null)

const summary = computed(() => hub.value?.summary || {})
const classes = computed(() => hub.value?.classes || [])
const courses = computed(() => hub.value?.courses || [])
const students = computed(() => {
  const list = hub.value?.students || []
  if (!activeClassId.value) return list
  const name = classes.value.find((c) => c.id === activeClassId.value)?.name
  return name ? list.filter((s) => s.class_name === name) : list
})
const vocabRows = computed(() => {
  const list = hub.value?.vocab_checkins || []
  if (!activeClassId.value) return list
  const name = classes.value.find((c) => c.id === activeClassId.value)?.name
  return name ? list.filter((v) => v.class_name === name) : list
})
const vocabDone = computed(() => vocabRows.value.filter((v) => v.completed).length)
const vocabTotal = computed(() => vocabRows.value.length)

function openHistory(userId: number) {
  historyStudentId.value = userId
  historyOpen.value = true
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    hub.value = await fetchTeacherHub()
    if (!activeClassId.value && hub.value.classes.length === 1) {
      activeClassId.value = hub.value.classes[0].id
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="hub">
    <header class="hero">
      <div>
        <p class="eyebrow">教师工作台</p>
        <h1>你好，{{ hub?.teacher_name || '老师' }}</h1>
        <p class="sub">以下均为班级学生数据（不是教师本人）。可点「学习历史」查看学生进度、交卷、背单词与错题记录。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="load" :loading="loading">刷新</el-button>
        <el-button type="primary" @click="router.push('/grading')">
          去批改{{ hub?.grade_pending ? `（${hub.grade_pending}）` : '' }}
        </el-button>
      </div>
    </header>

    <el-alert v-if="error" type="error" :title="error" show-icon class="mb" />

    <section class="kpi-row" v-loading="loading">
      <div class="kpi">
        <b>{{ summary.class_count ?? 0 }}</b>
        <span>我的班级</span>
      </div>
      <div class="kpi">
        <b>{{ summary.student_count ?? 0 }}</b>
        <span>学生人数</span>
      </div>
      <div class="kpi">
        <b>{{ summary.course_count ?? 0 }}</b>
        <span>课程板块</span>
      </div>
      <div class="kpi warn">
        <b>{{ summary.grade_pending ?? 0 }}</b>
        <span>待批改</span>
      </div>
      <div class="kpi">
        <b>{{ summary.vocab_done_today ?? 0 }}/{{ summary.vocab_total_today ?? 0 }}</b>
        <span>今日背单词打卡</span>
      </div>
      <div class="kpi">
        <b>{{ summary.avg_score_rate ?? 0 }}%</b>
        <span>平均得分率</span>
      </div>
    </section>

    <div class="filter" v-if="classes.length">
      <span>班级筛选</span>
      <el-radio-group v-model="activeClassId" size="small">
        <el-radio-button :label="null">全部</el-radio-button>
        <el-radio-button v-for="c in classes" :key="c.id" :label="c.id">{{ c.name }}</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 1. 课程板块 -->
    <section id="courses" class="panel">
      <div class="panel-head">
        <div>
          <h2>课程板块</h2>
          <p>用于上课与学生同步的课程内容，可进入班级绑定与章节管理。</p>
        </div>
        <div class="panel-actions">
          <el-button text type="primary" @click="router.push('/courses')">管理课程</el-button>
          <el-button text type="primary" @click="router.push('/classes')">班级同步</el-button>
          <el-button text type="primary" @click="router.push('/geometry')">几何课页</el-button>
        </div>
      </div>
      <div v-if="!courses.length" class="empty">暂无课程。请先在「课程管理」创建或发布课程，并在班级中绑定。</div>
      <div v-else class="course-grid">
        <article v-for="c in courses" :key="c.id" class="course-card">
          <div class="course-top">
            <h3>{{ c.title }}</h3>
            <el-tag size="small" :type="c.status === 'published' ? 'success' : 'info'">
              {{ c.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
          </div>
          <p class="muted">{{ c.summary || '暂无简介' }}</p>
          <div class="meta">
            <span>{{ c.class_count }} 个班级</span>
            <span>{{ c.student_count }} 名学生</span>
          </div>
          <p v-if="c.class_names.length" class="classes-line">班级：{{ c.class_names.join('、') }}</p>
          <el-button size="small" @click="router.push('/courses')">进入备课内容</el-button>
        </article>
      </div>
    </section>

    <!-- 2. 学生学习进度 -->
    <section id="progress" class="panel">
      <div class="panel-head">
        <div>
          <h2>学生学习进度</h2>
          <p>按班级查看完成进度、得分率与待跟进学生。</p>
        </div>
        <el-button text type="primary" @click="router.push('/reports')">打开学情详情</el-button>
      </div>
      <div class="class-progress" v-if="classes.length">
        <div v-for="c in classes" :key="c.id" class="class-bar">
          <div class="class-bar-top">
            <strong>{{ c.name }}</strong>
            <span>{{ c.course_title || '未绑定课程' }} · {{ c.student_count }} 人</span>
          </div>
          <div class="bars">
            <div>
              <label>人均完成课时 {{ c.progress_completed_avg }}</label>
              <el-progress :percentage="Math.min(100, Math.round(c.progress_completed_avg * 8))" :stroke-width="10" />
            </div>
            <div>
              <label>平均得分率 {{ c.avg_score_rate }}%</label>
              <el-progress :percentage="Math.round(c.avg_score_rate)" status="success" :stroke-width="10" />
            </div>
          </div>
        </div>
      </div>
      <el-table :data="students" stripe size="small" empty-text="暂无学生进度数据" class="mt">
        <el-table-column prop="display_name" label="学生" min-width="110" />
        <el-table-column prop="class_name" label="班级" min-width="100" />
        <el-table-column prop="progress_completed" label="完成进度" width="100" />
        <el-table-column label="得分率" width="90">
          <template #default="{ row }">{{ row.avg_score_rate }}%</template>
        </el-table-column>
        <el-table-column prop="wrong_open" label="未掌握错题" width="110" />
        <el-table-column label="背单词" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.vocab_today ? 'success' : 'warning'">
              {{ row.vocab_today ? '已打卡' : '未打卡' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="pending_grades" label="待批改" width="90" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openHistory(row.user_id)">学习历史</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 3. 我爱背单词打卡 -->
    <section id="vocab" class="panel">
      <div class="panel-head">
        <div>
          <h2>我爱背单词 · 打卡情况</h2>
          <p>
            今日打卡 {{ vocabDone }}/{{ vocabTotal }}
            <template v-if="vocabTotal">（{{ Math.round((vocabDone * 100) / vocabTotal) }}%）</template>
          </p>
        </div>
      </div>
      <el-table :data="vocabRows" stripe size="small" empty-text="班级暂无学生背单词记录" max-height="360">
        <el-table-column prop="display_name" label="学生" min-width="110" />
        <el-table-column prop="class_name" label="班级" min-width="100" />
        <el-table-column label="今日打卡" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.completed ? 'success' : 'info'">
              {{ row.completed ? '已完成' : '未完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="streak_days" label="连续天数" width="100" />
        <el-table-column prop="stars_earned" label="今日星" width="90" />
        <el-table-column prop="bank" label="词库" min-width="120" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openHistory(row.user_id)">学习历史</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 4. 学情分析 -->
    <section id="analytics" class="panel">
      <div class="panel-head">
        <div>
          <h2>学情分析</h2>
          <p>班级薄弱知识点与整体学情，可导出并推送练习。</p>
        </div>
        <el-button type="primary" plain @click="router.push('/reports')">进入学情报表</el-button>
      </div>
      <div v-if="!(hub?.weak_points || []).length" class="empty">暂无明显薄弱点，或班级尚无错题数据。</div>
      <div v-else class="weak-grid">
        <div v-for="w in hub?.weak_points || []" :key="w.knowledge_point" class="weak-item">
          <strong>{{ w.knowledge_point }}</strong>
          <span>{{ w.wrong_count }} 次未掌握</span>
        </div>
      </div>
      <p class="hint">未掌握错题合计：{{ summary.wrong_open_total ?? 0 }}；人均完成进度：{{ summary.avg_progress_completed ?? 0 }}</p>
    </section>

    <!-- 5. 作业批改 -->
    <section id="grading" class="panel">
      <div class="panel-head">
        <div>
          <h2>作业批改</h2>
          <p>主观题 AI 初评 + 教师复核队列。当前待处理 {{ hub?.grade_pending ?? 0 }} 条。</p>
        </div>
        <el-button type="primary" @click="router.push('/grading')">打开批改队列</el-button>
      </div>
      <div class="action-row">
        <button type="button" class="action" @click="router.push('/grading')">
          <h3>批改复核</h3>
          <p>处理 pending / AI 已评分任务</p>
        </button>
        <button type="button" class="action" @click="router.push('/papers')">
          <h3>试卷管理</h3>
          <p>布置与查看班级试卷</p>
        </button>
        <button type="button" class="action" @click="router.push('/questions')">
          <h3>题库</h3>
          <p>维护客观/主观题目</p>
        </button>
      </div>
    </section>

    <!-- 6. AI 备课 -->
    <section id="prep" class="panel">
      <div class="panel-head">
        <div>
          <h2>AI 备课</h2>
          <p>用知识库与课件能力快速准备下一堂课。</p>
        </div>
      </div>
      <div class="action-row">
        <button type="button" class="action teal" @click="router.push('/ppt')">
          <h3>生成 PPT</h3>
          <p>按主题一键生成讲义幻灯</p>
        </button>
        <button type="button" class="action teal" @click="router.push('/knowledge')">
          <h3>知识库备课</h3>
          <p>从教材生成课程 / 出题</p>
        </button>
        <button type="button" class="action teal" @click="router.push('/assistants')">
          <h3>AI 教学助手</h3>
          <p>配置课堂助教与提示词</p>
        </button>
        <button type="button" class="action teal" @click="router.push('/templates')">
          <h3>模板库</h3>
          <p>复用教案与测评模板</p>
        </button>
      </div>
    </section>

    <StudentHistoryDrawer v-model="historyOpen" :student-id="historyStudentId" />
  </div>
</template>

<style scoped>
.hub {
  max-width: 1100px;
}
.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
}
.hero-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.eyebrow {
  margin: 0;
  color: var(--edu-teal, #0f6b5c);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 12px;
}
h1 {
  margin: 6px 0 4px;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', serif;
  font-size: 28px;
  color: #14212b;
}
.sub,
.muted,
.hint {
  margin: 0;
  color: #64748b;
  line-height: 1.5;
}
.hint {
  margin-top: 10px;
  font-size: 13px;
}
.mb {
  margin-bottom: 12px;
}
.mt {
  margin-top: 12px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.kpi {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.kpi b {
  font-size: 22px;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.kpi span {
  font-size: 12px;
  color: #64748b;
}
.kpi.warn b {
  color: #b45309;
}
.filter {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.filter > span {
  font-size: 13px;
  color: #475569;
}
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px 18px 18px;
  margin-bottom: 14px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.panel-head h2 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #0f172a;
}
.panel-head p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
}
.empty {
  padding: 18px;
  text-align: center;
  color: #94a3b8;
  background: #f8fafc;
  border-radius: 10px;
}
.course-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.course-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  background: linear-gradient(180deg, #f8fbfa 0%, #fff 48%);
}
.course-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}
.course-card h3 {
  margin: 0;
  font-size: 16px;
  color: #14212b;
}
.course-card .muted {
  margin: 8px 0;
  min-height: 40px;
  font-size: 13px;
}
.meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #475569;
  margin-bottom: 6px;
}
.classes-line {
  margin: 0 0 10px;
  font-size: 12px;
  color: #64748b;
}
.class-progress {
  display: grid;
  gap: 12px;
}
.class-bar {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 12px;
  background: #f8fafc;
}
.class-bar-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #64748b;
}
.class-bar-top strong {
  color: #0f172a;
}
.bars {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.bars label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
.weak-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.weak-item {
  border-radius: 10px;
  padding: 12px;
  background: #fff7ed;
  border: 1px solid #ffedd5;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.weak-item strong {
  color: #9a3412;
  font-size: 14px;
}
.weak-item span {
  color: #c2410c;
  font-size: 12px;
}
.action-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.action {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  text-align: left;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.action:hover {
  border-color: #99c4bb;
  box-shadow: 0 6px 18px rgba(15, 107, 92, 0.08);
}
.action h3 {
  margin: 0 0 6px;
  font-size: 15px;
  color: #0f172a;
}
.action p {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}
.action.teal {
  background: linear-gradient(160deg, #f2faf8, #fff);
}
@media (max-width: 1000px) {
  .kpi-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .course-grid,
  .bars,
  .action-row {
    grid-template-columns: 1fr 1fr;
  }
  .weak-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 640px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
  .kpi-row,
  .course-grid,
  .bars,
  .action-row,
  .weak-grid {
    grid-template-columns: 1fr;
  }
  .panel-head {
    flex-direction: column;
  }
}
</style>
