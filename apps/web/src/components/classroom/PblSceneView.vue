<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PblScene } from '../../data/classroom'

const props = defineProps<{ scene: PblScene }>()
const emit = defineEmits<{ done: [] }>()

const role = ref('')
const checks = ref<Record<string, boolean>>({})
const draft = ref('')

watch(
  () => props.scene.id,
  () => {
    role.value = props.scene.roles[0] || ''
    checks.value = Object.fromEntries(props.scene.milestones.map((m) => [m.id, false]))
    draft.value = ''
  },
  { immediate: true },
)

const allDone = computed(() =>
  props.scene.milestones.every((m) => checks.value[m.id]) && draft.value.trim().length >= 8,
)

function finish() {
  if (!allDone.value) return
  emit('done')
}
</script>

<template>
  <div class="pbl">
    <header>
      <span class="badge">PBL 创造</span>
      <h2>{{ scene.title }}</h2>
      <p class="brief">{{ scene.brief }}</p>
    </header>

    <div class="grid">
      <section class="panel">
        <h3>选择角色</h3>
        <div class="roles">
          <button
            v-for="r in scene.roles"
            :key="r"
            type="button"
            class="role"
            :class="{ active: role === r }"
            @click="role = r"
          >
            {{ r }}
          </button>
        </div>
        <p class="hint">当前身份：{{ role || '未选择' }} · 可与 AI 同伴分工协作</p>
      </section>

      <section class="panel">
        <h3>里程碑</h3>
        <label v-for="m in scene.milestones" :key="m.id" class="mile">
          <input v-model="checks[m.id]" type="checkbox" />
          <span>
            <strong>{{ m.title }}</strong>
            <small>{{ m.doneHint }}</small>
          </span>
        </label>
      </section>
    </div>

    <section class="panel">
      <h3>交付物：{{ scene.deliverable }}</h3>
      <textarea
        v-model="draft"
        rows="5"
        placeholder="在这里写下你的作品草稿（要点即可）…"
      />
    </section>

    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="!allDone" @click="finish">
        提交作品并完课
      </button>
    </div>
  </div>
</template>

<style scoped>
.pbl {
  display: grid;
  gap: 14px;
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
  margin: 8px 0 6px;
  font-family: var(--font-display);
}

.brief {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.panel {
  padding: 16px;
}

h3 {
  margin: 0 0 12px;
  font-size: 0.95rem;
  color: var(--brand-deep);
}

.roles {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.role {
  border: 1px solid var(--line);
  background: white;
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
}

.role.active {
  background: var(--brand);
  border-color: var(--brand);
  color: white;
}

.hint {
  margin: 12px 0 0;
  font-size: 0.85rem;
  color: var(--muted);
}

.mile {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 10px;
  cursor: pointer;
}

.mile strong {
  display: block;
}

.mile small {
  color: var(--muted);
}

textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  font: inherit;
  resize: vertical;
  box-sizing: border-box;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 800px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
