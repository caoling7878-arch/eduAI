<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SlideScene } from '../../data/classroom'
import { stopSpeaking } from '../../lib/speech'

const props = defineProps<{
  scene: SlideScene
  teacherName: string
}>()

const emit = defineEmits<{ done: [] }>()
const step = ref(0)
const speaking = ref(false)

const lines = computed(() => {
  const list = [...props.scene.bullets]
  if (props.scene.spotlight) list.push(`关键式：${props.scene.spotlight}`)
  return list
})

watch(
  () => props.scene.id,
  () => {
    step.value = 0
    stopSpeaking()
    speaking.value = false
  },
)

function revealNext() {
  if (step.value < lines.value.length) step.value += 1
  if (step.value >= lines.value.length) emit('done')
}

async function narrate() {
  speaking.value = true
  try {
    // 中文讲解用浏览器 TTS（lang 由 voice 决定时可能不准，拼接英文提示较少）
    // 这里直接用 utterance 中文：复用 speak 管线前先走简易中文朗读
    await speakZh(props.scene.narrate)
  } finally {
    speaking.value = false
  }
}

function speakZh(text: string) {
  return new Promise<void>((resolve) => {
    if (!('speechSynthesis' in window)) {
      resolve()
      return
    }
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'
    u.rate = 0.95
    const voices = window.speechSynthesis.getVoices()
    const zh =
      voices.find((v) => /zh(-|_)CN|Chinese/i.test(v.lang) && /Xiaoxiao|Tingting|Huihui|Google/i.test(v.name)) ||
      voices.find((v) => /zh/i.test(v.lang))
    if (zh) u.voice = zh
    u.onend = () => resolve()
    u.onerror = () => resolve()
    window.speechSynthesis.speak(u)
  })
}
</script>

<template>
  <div class="slide">
    <header>
      <span class="badge">幻灯讲解</span>
      <h2>{{ scene.title }}</h2>
      <p class="by">{{ teacherName }} 主讲</p>
    </header>

    <div class="board">
      <ul>
        <li v-for="(line, i) in lines" :key="i" :class="{ show: i < step }">
          {{ line }}
        </li>
      </ul>
      <p v-if="step === 0" class="hint">点击「下一步要点」逐条揭示，或先听讲解。</p>
    </div>

    <blockquote v-if="scene.narrate">
      <strong>{{ teacherName }}：</strong>{{ scene.narrate }}
    </blockquote>

    <div class="actions">
      <button class="btn btn-ghost" type="button" :disabled="speaking" @click="narrate">
        {{ speaking ? '讲解中…' : '听 AI 讲解' }}
      </button>
      <button class="btn btn-primary" type="button" @click="revealNext">
        {{ step >= lines.length ? '已揭示全部' : '下一步要点' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.slide {
  display: grid;
  gap: 16px;
  height: 100%;
  align-content: start;
}

.badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--brand-deep);
  background: var(--brand-soft);
  padding: 3px 10px;
  border-radius: 999px;
}

h2 {
  margin: 8px 0 4px;
  font-family: var(--font-display);
  font-size: clamp(1.4rem, 2.4vw, 1.9rem);
}

.by {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.board {
  min-height: 220px;
  padding: 22px 24px;
  border-radius: 18px;
  background: linear-gradient(160deg, #0f6b5c 0%, #1a8f7a 55%, #0a4f44 100%);
  color: white;
  box-shadow: var(--shadow);
}

ul {
  margin: 0;
  padding-left: 1.2em;
  display: grid;
  gap: 12px;
  min-height: 120px;
}

li {
  opacity: 0;
  transform: translateY(6px);
  transition: 0.35s ease;
  line-height: 1.55;
}

li.show {
  opacity: 1;
  transform: none;
}

.hint {
  margin: 12px 0 0;
  opacity: 0.75;
  font-size: 0.9rem;
}

blockquote {
  margin: 0;
  padding: 14px 16px;
  border-left: 3px solid var(--accent);
  background: rgba(255, 255, 255, 0.7);
  border-radius: 0 12px 12px 0;
  color: var(--ink);
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
