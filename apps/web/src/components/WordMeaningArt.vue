<script setup lang="ts">
/**
 * 单词意思配图：优先真实照片（docx 导入），否则按语义主题 SVG 回退。
 */
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  imageKey: string
  meaning?: string
  word?: string
  imageUrl?: string | null
}>()

const theme = computed(() => (props.imageKey || props.word || 'shape').toLowerCase())
const label = computed(() => {
  const m = (props.meaning || '').split('；')[0].split('，')[0].trim()
  return m.slice(0, 8) || props.word || '词义'
})
const photoFailed = ref(false)
watch(
  () => props.imageUrl,
  () => {
    photoFailed.value = false
  },
)
const usePhoto = computed(() => !!props.imageUrl && !photoFailed.value)
</script>

<template>
  <div class="art" role="img" :aria-label="label">
    <div v-if="usePhoto" class="photo-wrap">
      <img
        class="photo"
        :src="imageUrl!"
        :alt="label"
        loading="lazy"
        @error="photoFailed = true"
      />
      <span class="photo-label">{{ label }}</span>
    </div>

    <!-- 精选特例 / 语义回退 SVG -->
    <template v-else>
    <svg v-if="theme === 'unhappy'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF5F0" />
      <circle cx="80" cy="58" r="34" fill="#FFE0D4" stroke="#C45C26" stroke-width="2.5" />
      <circle cx="66" cy="50" r="4" fill="#5C2A1A" />
      <circle cx="94" cy="50" r="4" fill="#5C2A1A" />
      <path d="M66 78c4-5 24-5 28 0" fill="none" stroke="#C45C26" stroke-width="3" stroke-linecap="round" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#C45C26" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'telephone' || theme === 'tech'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <rect x="58" y="22" width="44" height="72" rx="8" fill="#0F6B5C" />
      <rect x="64" y="34" width="32" height="44" rx="3" fill="#D8F0EA" />
      <circle cx="80" cy="86" r="4" fill="#E8A317" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'angle'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <path d="M30 95h100" stroke="#0F6B5C" stroke-width="3.5" stroke-linecap="round" />
      <path d="M30 95L120 28" stroke="#0F6B5C" stroke-width="3.5" stroke-linecap="round" />
      <path d="M48 95A28 28 0 0 0 68 68" fill="none" stroke="#E8A317" stroke-width="3" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'school'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <path d="M28 70L80 34l52 36v34H28V70z" fill="#B8E0D5" stroke="#0F6B5C" stroke-width="2.5" />
      <rect x="68" y="72" width="24" height="32" fill="#0F6B5C" />
      <rect x="40" y="78" width="18" height="14" fill="#FFF6DE" stroke="#E8A317" stroke-width="1.5" />
      <rect x="102" y="78" width="18" height="14" fill="#FFF6DE" stroke="#E8A317" stroke-width="1.5" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'book'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF6DE" />
      <path d="M42 28h36c8 0 12 4 12 10v54c0-8-4-12-12-12H42V28z" fill="#0F6B5C" />
      <path d="M118 28H82c-8 0-12 4-12 10v54c0-8 4-12 12-12h36V28z" fill="#2A8FBD" />
      <path d="M80 38v52" stroke="#fff" stroke-width="2" opacity="0.5" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'family' || theme === 'person'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="58" cy="42" r="12" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <path d="M40 78c2-16 12-22 18-22s16 6 18 22" fill="#0F6B5C" />
      <circle cx="102" cy="44" r="10" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <path d="M88 78c2-14 10-20 14-20s12 6 14 20" fill="#2A8FBD" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'food'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF6DE" />
      <ellipse cx="80" cy="78" rx="46" ry="12" fill="#E8D4A8" />
      <path d="M48 70c8-28 24-40 32-40s24 12 32 40" fill="#E8A317" stroke="#C98500" stroke-width="2" />
      <circle cx="70" cy="58" r="4" fill="#C45C26" />
      <circle cx="90" cy="52" r="3.5" fill="#0F6B5C" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'transport'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <rect x="30" y="48" width="100" height="32" rx="8" fill="#2A8FBD" />
      <path d="M48 48h28l14-16h22v16" fill="#0F6B5C" />
      <circle cx="52" cy="84" r="10" fill="#1A1A1A" />
      <circle cx="108" cy="84" r="10" fill="#1A1A1A" />
      <circle cx="52" cy="84" r="4" fill="#E8A317" />
      <circle cx="108" cy="84" r="4" fill="#E8A317" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'shop'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF6DE" />
      <path d="M36 50h88l-8 42H44L36 50z" fill="#FFE8A3" stroke="#E8A317" stroke-width="2.5" />
      <path d="M70 50c0 14 20 14 20 0" fill="none" stroke="#0F6B5C" stroke-width="3" />
      <circle cx="80" cy="34" r="6" fill="#0F6B5C" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'health'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <rect x="48" y="28" width="64" height="64" rx="12" fill="#fff" stroke="#0F6B5C" stroke-width="2.5" />
      <path d="M80 42v36M62 60h36" stroke="#C45C26" stroke-width="6" stroke-linecap="round" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'nature'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="118" cy="34" r="14" fill="#E8A317" />
      <rect x="72" y="58" width="10" height="34" fill="#8B5A2B" />
      <circle cx="77" cy="52" r="22" fill="#0F6B5C" />
      <circle cx="58" cy="58" r="14" fill="#2A8FBD" opacity="0.35" />
      <path d="M20 92h120" stroke="#94A3B8" stroke-width="3" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'sport'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="80" cy="56" r="28" fill="#FFF6DE" stroke="#0F6B5C" stroke-width="2.5" />
      <path d="M52 56h56M80 28v56M60 36c20 12 20 28 0 40M100 36c-20 12-20 28 0 40" fill="none" stroke="#2A8FBD" stroke-width="2" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'emotion'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF6DE" />
      <circle cx="80" cy="56" r="32" fill="#FFE8A3" stroke="#E8A317" stroke-width="2.5" />
      <circle cx="68" cy="48" r="3.5" fill="#0F6B5C" />
      <circle cx="92" cy="48" r="3.5" fill="#0F6B5C" />
      <path d="M64 64c5 10 27 10 32 0" fill="none" stroke="#0F6B5C" stroke-width="3" stroke-linecap="round" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'time'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="80" cy="56" r="32" fill="#fff" stroke="#0F6B5C" stroke-width="3" />
      <path d="M80 56V34M80 56l18 12" stroke="#E8A317" stroke-width="3.5" stroke-linecap="round" />
      <circle cx="80" cy="56" r="3" fill="#0F6B5C" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'social'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <path d="M36 40h58c8 0 12 6 12 12v18c0 6-4 12-12 12H58l-16 14v-14h-6c-8 0-12-6-12-12V52c0-6 4-12 12-12z" fill="#0F6B5C" />
      <path d="M78 58h46c6 0 10 4 10 10v14c0 6-4 10-10 10h-4v10l-12-10H78c-6 0-10-4-10-10V68c0-6 4-10 10-10z" fill="#2A8FBD" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'animal'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF6DE" />
      <ellipse cx="80" cy="66" rx="36" ry="26" fill="#E8D4A8" stroke="#8B5A2B" stroke-width="2" />
      <circle cx="58" cy="40" r="10" fill="#E8D4A8" stroke="#8B5A2B" stroke-width="2" />
      <circle cx="102" cy="40" r="10" fill="#E8D4A8" stroke="#8B5A2B" stroke-width="2" />
      <circle cx="70" cy="62" r="3" fill="#1A1A1A" />
      <circle cx="90" cy="62" r="3" fill="#1A1A1A" />
      <ellipse cx="80" cy="74" rx="6" ry="4" fill="#C45C26" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'body'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="80" cy="34" r="14" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <path d="M80 48v34M60 60h40M66 82l-10 18M94 82l10 18" fill="none" stroke="#0F6B5C" stroke-width="4" stroke-linecap="round" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'color'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="56" cy="52" r="20" fill="#C45C26" opacity="0.85" />
      <circle cx="80" cy="40" r="20" fill="#E8A317" opacity="0.85" />
      <circle cx="104" cy="52" r="20" fill="#2A8FBD" opacity="0.85" />
      <circle cx="80" cy="68" r="20" fill="#0F6B5C" opacity="0.85" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'item' || theme === 'house'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <path d="M30 70L80 32l50 38v36H30V70z" fill="#B8E0D5" stroke="#0F6B5C" stroke-width="2.5" />
      <rect x="68" y="78" width="24" height="28" fill="#E8A317" />
      <rect x="44" y="78" width="16" height="14" fill="#fff" stroke="#2A8FBD" />
      <rect x="100" y="78" width="16" height="14" fill="#fff" stroke="#2A8FBD" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'holiday'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#FFF6DE" />
      <rect x="55" y="48" width="50" height="40" rx="4" fill="#E8A317" />
      <path d="M55 56h50M80 48v40" stroke="#fff" stroke-width="3" />
      <path d="M68 48c0-12 24-12 24 0" fill="none" stroke="#C45C26" stroke-width="3" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'culture'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="80" cy="56" r="30" fill="#D8F0EA" stroke="#0F6B5C" stroke-width="2.5" />
      <ellipse cx="80" cy="56" rx="12" ry="30" fill="none" stroke="#0F6B5C" stroke-width="2" />
      <path d="M50 56h60M54 42h52M54 70h52" fill="none" stroke="#2A8FBD" stroke-width="1.5" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <svg v-else-if="theme === 'action'" viewBox="0 0 160 120">
      <rect width="160" height="120" rx="16" fill="#EAF6F3" />
      <circle cx="70" cy="36" r="10" fill="#FFE8A3" stroke="#E8A317" stroke-width="2" />
      <path d="M70 46l8 18-16 8 10 20M78 64l22-4M62 72l-16 10" fill="none" stroke="#0F6B5C" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M108 40l16 8M112 34l18-2" stroke="#E8A317" stroke-width="3" stroke-linecap="round" />
      <text x="80" y="112" text-anchor="middle" font-size="12" fill="#0F6B5C" font-family="system-ui">{{ label }}</text>
    </svg>

    <!-- 其余主题 / 回退：语义色块 + 中文首义 -->
    <svg v-else viewBox="0 0 160 120">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#D8F0EA" />
          <stop offset="100%" stop-color="#FFF6DE" />
        </linearGradient>
      </defs>
      <rect width="160" height="120" rx="16" fill="url(#g)" />
      <circle cx="80" cy="48" r="26" fill="#fff" stroke="#0F6B5C" stroke-width="2.5" />
      <text x="80" y="54" text-anchor="middle" font-size="18" fill="#0F6B5C" font-family="system-ui" font-weight="700">
        {{ (word || '').slice(0, 1).toUpperCase() }}
      </text>
      <text x="80" y="92" text-anchor="middle" font-size="13" fill="#0F6B5C" font-family="system-ui" font-weight="600">
        {{ label }}
      </text>
    </svg>
    </template>
  </div>
</template>

<style scoped>
.art {
  width: 160px;
  height: 120px;
  max-width: 100%;
  flex-shrink: 0;
  overflow: hidden;
  position: relative;
  z-index: 0;
  box-sizing: border-box;
}
.photo-wrap {
  width: 100%;
  height: 100%;
  border-radius: 14px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 8px 24px rgba(15, 107, 92, 0.08);
  background: #eaf6f3;
}
.photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.photo-label {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 4px 6px;
  font-size: 11px;
  text-align: center;
  color: #fff;
  background: linear-gradient(transparent, rgba(15, 107, 92, 0.82));
}
.art svg {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(15, 107, 92, 0.08);
}
</style>
