<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAudits } from '../lib/api'

const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await fetchAudits()
})
</script>

<template>
  <el-table :data="rows" stripe>
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="user_id" label="用户" width="90" />
    <el-table-column prop="action" label="动作" width="160" />
    <el-table-column prop="resource" label="资源" />
    <el-table-column prop="detail" label="详情" />
    <el-table-column prop="created_at" label="时间" width="200" />
  </el-table>
</template>
