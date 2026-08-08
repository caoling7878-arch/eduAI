<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  exportClassReportCsv,
  exportOverviewCsv,
  fetchClasses,
  fetchClassReport,
  fetchReportOverview,
  pushPractice,
} from '../lib/api'

const overview = ref<any>(null)
const classes = ref<any[]>([])
const classId = ref<number | null>(null)
const detail = ref<any>(null)
const pushing = ref(false)
const exporting = ref(false)

async function load() {
  overview.value = await fetchReportOverview()
  classes.value = await fetchClasses()
  if (classes.value[0]) {
    classId.value = classes.value[0].id
    await loadClass()
  }
}

async function loadClass() {
  if (!classId.value) return
  detail.value = await fetchClassReport(classId.value)
}

async function pushToClass() {
  if (!classId.value) return
  pushing.value = true
  try {
    const r = await pushPractice({
      class_id: classId.value,
      title: '薄弱点练习提醒',
      body: '老师根据班级学情为你推送了巩固练习，请前往「推荐」完成。',
    })
    ElMessage.success(`已推送 ${r.pushed} 人`)
  } finally {
    pushing.value = false
  }
}

async function pushToStudent(userId: number, name: string) {
  const r = await pushPractice({
    user_ids: [userId],
    title: '个人薄弱点练习',
    body: `${name}，系统为你准备了针对性巩固题，请打开「推荐」练习。`,
  })
  ElMessage.success(`已推送 ${r.pushed} 人`)
}

async function exportOverview() {
  exporting.value = true
  try {
    await exportOverviewCsv()
    ElMessage.success('已导出平台学情 CSV')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

async function exportClass() {
  if (!classId.value) return
  exporting.value = true
  try {
    await exportClassReportCsv(classId.value)
    ElMessage.success('已导出班级学情 CSV')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wrap">
    <div v-if="overview" class="stats">
      <div class="stat"><b>{{ overview.students }}</b><span>学员</span></div>
      <div class="stat"><b>{{ overview.submissions }}</b><span>交卷</span></div>
      <div class="stat"><b>{{ overview.wrong_open }}</b><span>未掌握错题</span></div>
      <div class="stat"><b>{{ overview.pending_grades }}</b><span>待复核</span></div>
    </div>

    <el-card shadow="never" style="margin-bottom: 14px">
      <template #header>
        <div class="head">
          <span>平台薄弱知识点</span>
          <el-button :loading="exporting" @click="exportOverview">导出 CSV</el-button>
        </div>
      </template>
      <el-table :data="overview?.weak_points || []" size="small">
        <el-table-column prop="knowledge_point" label="知识点" />
        <el-table-column prop="wrong_count" label="错题数" width="120" />
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>班级学情</span>
          <div class="head-actions">
            <el-select v-model="classId" style="width: 220px" @change="loadClass">
              <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-button :loading="exporting" @click="exportClass">导出班级 CSV</el-button>
            <el-button type="primary" :loading="pushing" @click="pushToClass">推送练习给班级</el-button>
          </div>
        </div>
      </template>
      <template v-if="detail">
        <p class="meta">
          {{ detail.class_name }} · {{ detail.student_count }} 人 · 平均得分率
          {{ detail.avg_score_rate }}%
        </p>
        <el-table :data="detail.students" stripe>
          <el-table-column prop="display_name" label="学员" />
          <el-table-column prop="avg_score_rate" label="得分率%" width="100" />
          <el-table-column prop="wrong_open" label="错题" width="80" />
          <el-table-column prop="checkins" label="打卡" width="80" />
          <el-table-column prop="pending_grades" label="待评" width="80" />
          <el-table-column label="薄弱点">
            <template #default="{ row }">
              {{ row.weak_points.map((w: any) => w.knowledge_point).join('、') || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="pushToStudent(row.user_id, row.display_name)">
                推送
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.stat {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
}
.stat b {
  display: block;
  font-size: 1.5rem;
  color: var(--edu-teal);
}
.stat span {
  color: var(--edu-muted);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.meta {
  color: var(--edu-muted);
  margin-top: 0;
}
</style>
