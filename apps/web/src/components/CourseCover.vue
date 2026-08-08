<script setup lang="ts">
defineProps<{
  tone: 'forest' | 'amber' | 'slate'
  title: string
}>()
</script>

<template>
  <div class="cover" :data-tone="tone" aria-hidden="true">
    <div class="grid" />
    <div class="orb orb-a" />
    <div class="orb orb-b" />
    <svg v-if="tone === 'forest'" class="motif" viewBox="0 0 120 80" fill="none">
      <path d="M20 58 L60 18 L100 58 Z" stroke="currentColor" stroke-width="2" />
      <path d="M60 18 V58" stroke="currentColor" stroke-width="2" />
      <circle cx="60" cy="38" r="4" fill="currentColor" />
    </svg>
    <svg v-else-if="tone === 'amber'" class="motif" viewBox="0 0 120 80" fill="none">
      <path
        d="M28 50c8-18 20-26 32-26s24 8 32 26"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
      />
      <circle cx="48" cy="36" r="3" fill="currentColor" />
      <circle cx="72" cy="34" r="3" fill="currentColor" />
      <path d="M50 48h20" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </svg>
    <svg v-else class="motif" viewBox="0 0 120 80" fill="none">
      <rect x="28" y="22" width="28" height="36" rx="4" stroke="currentColor" stroke-width="2" />
      <rect x="64" y="30" width="28" height="28" rx="4" stroke="currentColor" stroke-width="2" />
      <path d="M36 34h12M36 42h12M72 40h12" stroke="currentColor" stroke-width="2" />
    </svg>
    <span class="label">{{ title }}</span>
  </div>
</template>

<style scoped>
.cover {
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  border-radius: 14px 14px 0 0;
  color: rgba(255, 255, 255, 0.88);
}

.cover[data-tone='forest'] {
  background: linear-gradient(135deg, #0f6b5c 0%, #1a8f7a 45%, #0a4f44 100%);
}

.cover[data-tone='amber'] {
  background: linear-gradient(135deg, #c48912 0%, #e8a317 40%, #8a5a10 100%);
}

.cover[data-tone='slate'] {
  background: linear-gradient(135deg, #243642 0%, #3d5563 50%, #14212b 100%);
}

.grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 22px 22px;
  mask-image: linear-gradient(to bottom, black, transparent 85%);
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
}

.orb-a {
  width: 120px;
  height: 120px;
  right: -20px;
  top: -30px;
  background: rgba(255, 255, 255, 0.12);
}

.orb-b {
  width: 80px;
  height: 80px;
  left: 12%;
  bottom: -20px;
  background: rgba(232, 163, 23, 0.25);
}

.motif {
  position: absolute;
  width: 46%;
  right: 8%;
  top: 18%;
  opacity: 0.9;
}

.label {
  position: absolute;
  left: 16px;
  bottom: 14px;
  font-family: var(--font-display);
  font-size: 1.05rem;
}
</style>
