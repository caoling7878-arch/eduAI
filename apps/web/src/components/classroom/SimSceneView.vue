<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SimScene } from '../../data/classroom'

const props = defineProps<{ scene: SimScene }>()
const emit = defineEmits<{ done: [] }>()

const tries = ref(0)
const note = ref('')
const marked = ref(false)

watch(
  () => props.scene.id,
  () => {
    tries.value = 0
    note.value = ''
    marked.value = false
  },
)

function bump() {
  tries.value += 1
}

function complete() {
  marked.value = true
  emit('done')
}
</script>

<template>
  <div class="sim">
    <header>
      <span class="badge">模拟动手</span>
      <h2>{{ scene.title }}</h2>
      <p class="lead">{{ scene.blurb }}</p>
      <p class="task"><strong>任务：</strong>{{ scene.task }}</p>
    </header>

    <div v-if="scene.kind === 'geometry' && scene.href" class="frame-wrap">
      <iframe :src="scene.href" :title="scene.title" class="frame" />
    </div>

    <div v-else class="widget panel">
      <p>交互工作台</p>
      <div class="counter">
        <button class="btn btn-accent" type="button" @click="bump">做一次尝试</button>
        <span>已尝试 <b>{{ tries }}</b> 次</span>
      </div>
      <label>
        我的观察
        <textarea v-model="note" rows="3" placeholder="写下你看到的规律或现象…" />
      </label>
    </div>

    <div class="actions">
      <a
        v-if="scene.kind === 'geometry' && scene.href"
        class="btn btn-ghost"
        :href="scene.href"
        target="_blank"
        rel="noopener"
      >
        新窗口打开
      </a>
      <button
        class="btn btn-primary"
        type="button"
        :disabled="marked || (scene.kind !== 'geometry' && (tries < 1 || !note.trim()))"
        @click="complete"
      >
        {{ marked ? '已完成本环节' : '完成动手环节' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.sim {
  display: grid;
  gap: 12px;
  height: 100%;
  grid-template-rows: auto 1fr auto;
}

.badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  color: #243642;
  background: rgba(36, 54, 66, 0.1);
  padding: 3px 10px;
  border-radius: 999px;
}

h2 {
  margin: 8px 0 4px;
  font-family: var(--font-display);
}

.lead,
.task {
  margin: 0 0 4px;
  color: var(--muted);
  line-height: 1.5;
}

.task {
  color: var(--ink);
}

.frame-wrap {
  min-height: 0;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: #edf3f8;
}

.frame {
  width: 100%;
  height: 100%;
  min-height: 420px;
  border: 0;
}

.widget {
  padding: 18px;
  display: grid;
  gap: 12px;
  align-content: start;
}

.counter {
  display: flex;
  gap: 14px;
  align-items: center;
}

label {
  display: grid;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--muted);
}

textarea {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  resize: vertical;
  font: inherit;
  color: var(--ink);
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
</style>
