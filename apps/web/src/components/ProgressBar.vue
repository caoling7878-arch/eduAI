<script setup lang="ts">
defineProps<{
  percent: number
  label?: string
}>()
</script>

<template>
  <div class="wrap" :aria-label="label || `进度 ${percent}%`">
    <div class="track">
      <div class="fill" :style="{ width: `${Math.min(100, Math.max(0, percent))}%` }" />
    </div>
    <span class="pct">{{ percent }}%</span>
  </div>
</template>

<style scoped>
.wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.12);
  overflow: hidden;
}

.fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--brand), #1a8f7a);
  transition: width 0.35s ease;
}

.pct {
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  min-width: 2.5em;
  text-align: right;
}
</style>
