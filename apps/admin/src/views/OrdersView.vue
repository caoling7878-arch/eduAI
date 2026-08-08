<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchOrders, fetchPlans } from '../lib/api'

const orders = ref<any[]>([])
const plans = ref<any[]>([])
const loading = ref(false)

const orderStatus: Record<string, string> = {
  paid: '已支付',
  pending: '待支付',
  cancelled: '已取消',
  refunded: '已退款',
}

async function load() {
  loading.value = true
  try {
    ;[orders.value, plans.value] = await Promise.all([fetchOrders(), fetchPlans()])
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="grid" v-loading="loading">
    <el-card shadow="never">
      <template #header>会员套餐</template>
      <div class="table-scroll">
        <el-table :data="plans" style="width: 100%">
          <el-table-column prop="name" label="套餐" min-width="140" />
          <el-table-column prop="price" label="价格" width="100" />
          <el-table-column prop="days" label="天数" width="90" />
          <el-table-column prop="benefits" label="权益" min-width="220" show-overflow-tooltip />
        </el-table>
        <el-empty v-if="!loading && !plans.length" description="暂无套餐" :image-size="64" />
      </div>
    </el-card>
    <el-card shadow="never">
      <template #header>订单（模拟支付）</template>
      <div class="table-scroll">
        <el-table :data="orders" style="min-width: 720px" :scrollbar-always-on="true">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="user_id" label="用户" width="90" />
          <el-table-column prop="plan_id" label="套餐" width="90" />
          <el-table-column prop="course_id" label="课程" width="90" />
          <el-table-column prop="amount" label="金额" width="100" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              {{ orderStatus[row.status] || row.status }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" min-width="180" />
        </el-table>
        <el-empty v-if="!loading && !orders.length" description="暂无订单" :image-size="64" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  gap: 16px;
}
.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
</style>
