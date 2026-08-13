<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { DesktopUpdateStatus } from '../eduai-desktop'

const desktop = typeof window !== 'undefined' ? window.eduaiDesktop : undefined
const status = ref<DesktopUpdateStatus>({ state: 'idle' })

const visible = computed(() => !!desktop)
const busy = computed(
  () =>
    status.value.state === 'checking' ||
    status.value.state === 'downloading' ||
    status.value.state === 'installing',
)
const label = computed(() => {
  const s = status.value
  if (s.state === 'checking') return '正在检查…'
  if (s.state === 'downloading') return `下载中 ${s.percent ?? 0}%`
  if (s.state === 'installing') return '正在安装…'
  if (s.state === 'available' && s.latestVersion) return `更新到 ${s.latestVersion}`
  if (s.state === 'uptodate') return '已是最新'
  if (s.state === 'error') return '重试更新'
  return '检查更新'
})
const title = computed(() => {
  const s = status.value
  if (s.message) return s.message
  if (s.currentVersion) return `当前版本 ${s.currentVersion}`
  return '从 GitHub 检查并安装桌面版更新'
})

let off: (() => void) | undefined

onMounted(() => {
  if (!desktop) return
  off = desktop.onUpdateStatus((data) => {
    status.value = data
  })
  void desktop.getVersion().then((v) => {
    if (!status.value.currentVersion) status.value = { ...status.value, currentVersion: v }
  })
})

onUnmounted(() => {
  off?.()
})

async function onClick() {
  if (!desktop || busy.value) return
  if (status.value.state === 'available') {
    await desktop.startUpdate()
    return
  }
  await desktop.checkForUpdate()
}
</script>

<template>
  <button
    v-if="visible"
    type="button"
    class="upd"
    :class="{
      'upd--hot': status.state === 'available',
      'upd--busy': busy,
    }"
    :disabled="busy"
    :title="title"
    @click="onClick"
  >
    {{ label }}
  </button>
</template>

<style scoped>
.upd {
  border: 1px solid rgba(15, 107, 92, 0.35);
  background: rgba(15, 107, 92, 0.08);
  color: var(--edu-teal, #0f6b5c);
  font-weight: 600;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
}
.upd:hover:not(:disabled) {
  background: var(--edu-teal, #0f6b5c);
  color: #fff;
  border-color: var(--edu-teal, #0f6b5c);
}
.upd--hot {
  background: #e8a317;
  border-color: #d97706;
  color: #1a1a1a;
}
.upd--hot:hover:not(:disabled) {
  background: #d97706;
  color: #fff;
  border-color: #d97706;
}
.upd--busy {
  opacity: 0.85;
  cursor: wait;
}
</style>
