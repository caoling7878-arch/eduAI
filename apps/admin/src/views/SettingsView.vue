<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSettings, putSettings } from '../lib/api'

const form = reactive({
  site_name: '',
  site_tagline: '',
  support_email: '',
  member_enabled: 'true',
})

onMounted(async () => {
  const { items } = await fetchSettings()
  Object.assign(form, items)
})

async function save() {
  await putSettings({ ...form })
  ElMessage.success('设置已保存')
}
</script>

<template>
  <el-card shadow="never" style="max-width: 640px">
    <el-form label-width="110px">
      <el-form-item label="站点名称"><el-input v-model="form.site_name" /></el-form-item>
      <el-form-item label="标语"><el-input v-model="form.site_tagline" /></el-form-item>
      <el-form-item label="支持邮箱"><el-input v-model="form.support_email" /></el-form-item>
      <el-form-item label="会员开关">
        <el-select v-model="form.member_enabled">
          <el-option label="开启" value="true" />
          <el-option label="关闭" value="false" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save">保存</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>
