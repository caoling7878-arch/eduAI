<script setup lang="ts">
import { onMounted, ref } from 'vue'

const version = ref(String(import.meta.env.VITE_APP_VERSION || '').trim())

onMounted(() => {
  const api = window.eduaiDesktop
  if (!api?.getVersion) return
  void api.getVersion().then((v) => {
    if (v) version.value = v
  })
})
</script>

<template>
  <span v-if="version" class="app-ver" :title="`eduAI v${version}`">v{{ version }}</span>
</template>

<style scoped>
.app-ver {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.12);
  color: var(--brand-deep, #0f6b5c);
  font-family: var(--font-body, inherit);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1.4;
  vertical-align: middle;
}
</style>
