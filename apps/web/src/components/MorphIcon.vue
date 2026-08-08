<script setup lang="ts">
/** 词根/词缀小图标：与后端 icon / 主题字段对应 */
const props = defineProps<{ name: string; color?: string }>()
const c = () => props.color || '#0F6B5C'
</script>

<template>
  <svg class="ico" viewBox="0 0 40 40" aria-hidden="true">
    <g v-if="props.name === 'cross'">
      <circle cx="20" cy="20" r="16" :fill="c()" opacity="0.15" />
      <path d="M12 12l16 16M28 12L12 28" :stroke="c()" stroke-width="3.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'smile'">
      <circle cx="20" cy="20" r="16" fill="#FFE8A3" stroke="#E8A317" stroke-width="1.5" />
      <circle cx="14" cy="16" r="2" fill="#0F6B5C" />
      <circle cx="26" cy="16" r="2" fill="#0F6B5C" />
      <path d="M13 24c2.5 3 11.5 3 14 0" fill="none" stroke="#0F6B5C" stroke-width="2.2" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'line'">
      <circle cx="8" cy="20" r="3.5" :fill="c()" />
      <line x1="12" y1="20" x2="28" y2="20" :stroke="c()" stroke-width="2.5" stroke-dasharray="3 3" />
      <circle cx="32" cy="20" r="3.5" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'phone'">
      <rect x="14" y="6" width="12" height="28" rx="3" :fill="c()" />
      <rect x="16" y="10" width="8" height="16" rx="1" fill="#fff" opacity="0.85" />
    </g>
    <g v-else-if="props.name === 'forward' || props.name === 'arrow'">
      <path d="M8 20h18M20 12l10 8-10 8" fill="none" :stroke="c()" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />
    </g>
    <g v-else-if="props.name === 'throw'">
      <circle cx="10" cy="22" r="4" :fill="c()" />
      <path d="M14 20c6-8 14-8 20-2" fill="none" stroke="#E8A317" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'box'">
      <rect x="8" y="12" width="24" height="18" rx="3" :fill="c()" opacity="0.25" />
      <rect x="8" y="12" width="24" height="18" rx="3" fill="none" :stroke="c()" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'globe' || props.name === 'culture'">
      <circle cx="20" cy="20" r="14" fill="#D8F0EA" :stroke="c()" stroke-width="2" />
      <ellipse cx="20" cy="20" rx="6" ry="14" fill="none" :stroke="c()" stroke-width="1.5" />
      <path d="M6 20h28" fill="none" :stroke="c()" stroke-width="1.2" />
    </g>
    <g v-else-if="props.name === 'ruler'">
      <rect x="7" y="14" width="26" height="12" rx="2" :fill="c()" opacity="0.2" />
      <rect x="7" y="14" width="26" height="12" rx="2" fill="none" :stroke="c()" stroke-width="2" />
      <path d="M12 14v6M17 14v4M22 14v6M27 14v4" :stroke="c()" stroke-width="1.6" />
    </g>
    <g v-else-if="props.name === 'cut'">
      <path d="M8 28L28 8M12 8l4 4M24 24l4 4" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'board'">
      <rect x="6" y="8" width="28" height="20" rx="2" fill="#F4F7F5" :stroke="c()" stroke-width="2" />
      <path d="M11 16h18M11 21h12" :stroke="c()" stroke-width="2" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'target'">
      <circle cx="20" cy="20" r="14" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <circle cx="20" cy="20" r="8" fill="#fff" stroke="#C45C26" stroke-width="2" />
      <circle cx="20" cy="20" r="3" fill="#C45C26" />
    </g>
    <g v-else-if="props.name === 'vertical'">
      <line x1="8" y1="32" x2="32" y2="32" stroke="#94A3B8" stroke-width="2.5" />
      <line x1="20" y1="8" x2="20" y2="32" :stroke="c()" stroke-width="3" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'angle'">
      <path d="M8 30h24M8 30L28 10" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
      <path d="M14 30a10 10 0 0 0 7-9" fill="none" stroke="#E8A317" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'plane'">
      <path d="M6 26L20 10l14 16H6z" fill="#D8F0EA" :stroke="c()" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'ok'">
      <circle cx="20" cy="20" r="14" fill="#D8F0EA" />
      <path d="M12 20l5 5 11-12" fill="none" :stroke="c()" stroke-width="3" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'spark'">
      <path d="M20 6l3 10 10 3-10 3-3 10-3-10-10-3 10-3z" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'school'">
      <path d="M8 22L20 12l12 10v12H8V22z" :fill="c()" opacity="0.25" />
      <path d="M8 22L20 12l12 10v12H8V22z" fill="none" :stroke="c()" stroke-width="2" />
      <rect x="17" y="24" width="6" height="10" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'book'">
      <path d="M8 10h10c3 0 4 2 4 4v16c-2-2-4-3-6-3H8V10z" :fill="c()" />
      <path d="M32 10H22c-3 0-4 2-4 4v16c2-2 4-3 6-3h8V10z" fill="#2A8FBD" />
    </g>
    <g v-else-if="props.name === 'family' || props.name === 'person'">
      <circle cx="20" cy="12" r="6" fill="#FFE8A3" stroke="#E8A317" stroke-width="1.5" />
      <path d="M10 32c1-10 6-14 10-14s9 4 10 14" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'food'">
      <ellipse cx="20" cy="28" rx="12" ry="4" fill="#E8D4A8" />
      <path d="M12 24c3-10 7-14 8-14s5 4 8 14" fill="#E8A317" />
    </g>
    <g v-else-if="props.name === 'car' || props.name === 'transport'">
      <rect x="6" y="16" width="28" height="10" rx="3" :fill="c()" />
      <circle cx="12" cy="28" r="3.5" fill="#1A1A1A" />
      <circle cx="28" cy="28" r="3.5" fill="#1A1A1A" />
    </g>
    <g v-else-if="props.name === 'house'">
      <path d="M8 22L20 12l12 10v12H8V22z" fill="#D8F0EA" :stroke="c()" stroke-width="2" />
      <rect x="17" y="24" width="6" height="10" fill="#E8A317" />
    </g>
    <g v-else-if="props.name === 'nature'">
      <rect x="18" y="20" width="4" height="12" fill="#8B5A2B" />
      <circle cx="20" cy="16" r="8" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'animal'">
      <ellipse cx="20" cy="22" rx="12" ry="9" :fill="c()" opacity="0.3" />
      <ellipse cx="20" cy="22" rx="12" ry="9" fill="none" :stroke="c()" stroke-width="2" />
      <circle cx="12" cy="12" r="4" :fill="c()" opacity="0.4" />
      <circle cx="28" cy="12" r="4" :fill="c()" opacity="0.4" />
    </g>
    <g v-else-if="props.name === 'body'">
      <circle cx="20" cy="10" r="5" fill="#FFE8A3" stroke="#E8A317" stroke-width="1.5" />
      <path d="M20 15v12M13 20h14M15 27l-4 6M25 27l4 6" fill="none" :stroke="c()" stroke-width="2.2" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'sport'">
      <circle cx="20" cy="20" r="12" fill="#FFF6DE" :stroke="c()" stroke-width="2" />
      <path d="M8 20h24M20 8v24" :stroke="c()" stroke-width="1.5" />
    </g>
    <g v-else-if="props.name === 'tech'">
      <rect x="12" y="6" width="16" height="28" rx="3" :fill="c()" />
      <rect x="15" y="10" width="10" height="16" rx="1" fill="#fff" opacity="0.85" />
    </g>
    <g v-else-if="props.name === 'time'">
      <circle cx="20" cy="20" r="14" fill="#fff" :stroke="c()" stroke-width="2" />
      <path d="M20 20V10M20 20l8 6" stroke="#E8A317" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'color'">
      <circle cx="14" cy="18" r="7" fill="#C45C26" />
      <circle cx="26" cy="18" r="7" fill="#2A8FBD" />
      <circle cx="20" cy="26" r="7" fill="#E8A317" />
    </g>
    <g v-else-if="props.name === 'item'">
      <rect x="10" y="12" width="20" height="16" rx="2" fill="#FFF6DE" :stroke="c()" stroke-width="2" />
      <path d="M14 12v-3h12v3" :stroke="c()" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'holiday'">
      <rect x="12" y="16" width="16" height="14" rx="2" fill="#E8A317" />
      <path d="M12 20h16M20 16v14" stroke="#fff" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'health'">
      <rect x="10" y="10" width="20" height="20" rx="4" fill="#fff" :stroke="c()" stroke-width="2" />
      <path d="M20 14v12M14 20h12" stroke="#C45C26" stroke-width="3" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'shop'">
      <path d="M10 14h20l-2 14H12L10 14z" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <path d="M16 14c0 6 8 6 8 0" fill="none" :stroke="c()" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'speak'">
      <path d="M8 12h16c3 0 4 2 4 4v6c0 2-1 4-4 4h-6l-6 5v-5H8c-3 0-4-2-4-4v-6c0-2 1-4 4-4z" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'run' || props.name === 'action'">
      <circle cx="16" cy="10" r="4" fill="#FFE8A3" stroke="#E8A317" stroke-width="1.2" />
      <path d="M16 14l4 8-8 4 4 8M20 22l8-2" fill="none" :stroke="c()" stroke-width="2.2" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'down'">
      <path d="M20 8v20M12 20l8 10 8-10" fill="none" :stroke="c()" stroke-width="2.8" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'up'">
      <path d="M20 32V12M12 20l8-10 8 10" fill="none" :stroke="c()" stroke-width="2.8" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'before'">
      <path d="M28 20H10M18 12l-10 8 10 8" fill="none" :stroke="c()" stroke-width="2.8" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'after'">
      <path d="M12 20h18M22 12l10 8-10 8" fill="none" :stroke="c()" stroke-width="2.8" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'out'">
      <rect x="8" y="10" width="16" height="20" rx="2" fill="none" :stroke="c()" stroke-width="2" />
      <path d="M18 20h14M26 14l8 6-8 6" fill="none" :stroke="c()" stroke-width="2.4" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'in'">
      <rect x="16" y="10" width="16" height="20" rx="2" fill="none" :stroke="c()" stroke-width="2" />
      <path d="M6 20h16M16 14l8 6-8 6" fill="none" :stroke="c()" stroke-width="2.4" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'link'">
      <path d="M16 14a6 6 0 0 1 8 0l4 4a6 6 0 0 1-8 8" fill="none" :stroke="c()" stroke-width="2.4" />
      <path d="M24 26a6 6 0 0 1-8 0l-4-4a6 6 0 0 1 8-8" fill="none" stroke="#2A8FBD" stroke-width="2.4" />
    </g>
    <g v-else-if="props.name === 'half'">
      <circle cx="20" cy="20" r="14" fill="#D8F0EA" :stroke="c()" stroke-width="2" />
      <path d="M20 6v28" :stroke="c()" stroke-width="2" />
      <path d="M20 6a14 14 0 0 0 0 28" :fill="c()" opacity="0.35" />
    </g>
    <g v-else-if="props.name === 'full'">
      <circle cx="20" cy="20" r="14" :fill="c()" opacity="0.25" />
      <circle cx="20" cy="20" r="14" fill="none" :stroke="c()" stroke-width="2" />
      <path d="M12 20h16" :stroke="c()" stroke-width="3" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'empty'">
      <circle cx="20" cy="20" r="14" fill="#fff" :stroke="c()" stroke-width="2" stroke-dasharray="3 3" />
    </g>
    <g v-else-if="props.name === 'wave'">
      <path d="M6 20c4-8 8-8 12 0s8 8 12 0 8-8 12 0" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'warn'">
      <path d="M20 6l14 26H6L20 6z" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <path d="M20 16v8M20 28h.1" stroke="#C45C26" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'gear'">
      <circle cx="20" cy="20" r="6" :fill="c()" />
      <path d="M20 6v4M20 30v4M6 20h4M30 20h4M10 10l3 3M27 27l3 3M30 10l-3 3M13 27l-3 3" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'bag'">
      <rect x="10" y="14" width="20" height="18" rx="2" :fill="c()" opacity="0.25" />
      <rect x="10" y="14" width="20" height="18" rx="2" fill="none" :stroke="c()" stroke-width="2" />
      <path d="M15 14c0-6 10-6 10 0" fill="none" :stroke="c()" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'eye'">
      <ellipse cx="20" cy="20" rx="14" ry="9" fill="#fff" :stroke="c()" stroke-width="2" />
      <circle cx="20" cy="20" r="4" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'pen'">
      <path d="M10 28l16-16 4 4-16 16H10v-4z" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'build'">
      <rect x="8" y="16" width="10" height="16" :fill="c()" opacity="0.35" />
      <rect x="20" y="10" width="12" height="22" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'pull' || props.name === 'lead'">
      <circle cx="10" cy="20" r="4" :fill="c()" />
      <path d="M14 20h18" :stroke="c()" stroke-width="2.5" />
      <path d="M26 14l8 6-8 6" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'place'">
      <path d="M20 6c7 0 12 5 12 12 0 10-12 18-12 18S8 28 8 18c0-7 5-12 12-12z" fill="#C45C26" opacity="0.85" />
      <circle cx="20" cy="18" r="4" fill="#fff" />
    </g>
    <g v-else-if="props.name === 'press'">
      <rect x="8" y="18" width="24" height="10" rx="2" :fill="c()" opacity="0.3" />
      <path d="M20 8v12M14 14l6 6 6-6" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'turn'">
      <path d="M10 22a10 10 0 1 1 4 8" fill="none" :stroke="c()" stroke-width="2.5" />
      <path d="M8 16l2 8 8-2" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'water'">
      <path d="M20 6c8 10 12 16 12 22a12 12 0 1 1-24 0c0-6 4-12 12-22z" fill="#2A8FBD" opacity="0.7" />
    </g>
    <g v-else-if="props.name === 'shield'">
      <path d="M20 6l12 4v10c0 8-6 14-12 16-6-2-12-8-12-16V10l12-4z" fill="#D8F0EA" :stroke="c()" stroke-width="2" />
    </g>
    <g v-else-if="props.name === 'dots' || props.name === 'two'">
      <circle cx="12" cy="20" r="4" :fill="c()" />
      <circle cx="28" cy="20" r="4" :fill="c()" />
      <circle v-if="props.name === 'dots'" cx="20" cy="20" r="4" fill="#E8A317" />
    </g>
    <g v-else-if="props.name === 'loop'">
      <path d="M28 14a10 10 0 1 0 2 8" fill="none" :stroke="c()" stroke-width="2.5" />
      <path d="M24 10l6 4-4 6" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else-if="props.name === 'star'">
      <path d="M20 6l3 9h9l-7 5 3 9-8-5-8 5 3-9-7-5h9z" :fill="c()" />
    </g>
    <g v-else-if="props.name === 'over'">
      <path d="M8 26h24M12 26c4-12 12-12 16 0" fill="none" :stroke="c()" stroke-width="2.5" stroke-linecap="round" />
    </g>
    <g v-else>
      <rect x="9" y="9" width="22" height="22" rx="6" fill="#D8F0EA" :stroke="c()" stroke-width="2" />
      <circle cx="20" cy="20" r="5" :fill="c()" />
    </g>
  </svg>
</template>

<style scoped>
.ico {
  width: 36px;
  height: 36px;
  display: block;
  flex-shrink: 0;
}
</style>
