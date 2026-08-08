<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QuizScene } from '../../data/classroom'

const props = defineProps<{ scene: QuizScene }>()
const emit = defineEmits<{ done: [] }>()

const answers = ref<Record<string, number | null>>({})
const submitted = ref(false)

watch(
  () => props.scene.id,
  () => {
    answers.value = Object.fromEntries(props.scene.questions.map((q) => [q.id, null]))
    submitted.value = false
  },
  { immediate: true },
)

const score = computed(() => {
  let ok = 0
  for (const q of props.scene.questions) {
    if (answers.value[q.id] === q.answerIndex) ok += 1
  }
  return ok
})

const allAnswered = computed(() =>
  props.scene.questions.every((q) => answers.value[q.id] != null),
)

function submit() {
  if (!allAnswered.value) return
  submitted.value = true
  emit('done')
}
</script>

<template>
  <div class="quiz">
    <header>
      <span class="badge">测验检验</span>
      <h2>{{ scene.title }}</h2>
      <p class="lead">答完即可看到即时反馈；错题会给出要点提示。</p>
    </header>

    <div v-for="(q, qi) in scene.questions" :key="q.id" class="card">
      <h3>{{ qi + 1 }}. {{ q.stem }}</h3>
      <label v-for="(opt, oi) in q.options" :key="oi" class="opt" :class="{
        locked: submitted,
        correct: submitted && oi === q.answerIndex,
        wrong: submitted && answers[q.id] === oi && oi !== q.answerIndex,
      }">
        <input
          v-model="answers[q.id]"
          type="radio"
          :value="oi"
          :name="q.id"
          :disabled="submitted"
        />
        <span>{{ opt }}</span>
      </label>
      <p v-if="submitted" class="explain">{{ q.explain }}</p>
    </div>

    <div class="footer">
      <p v-if="submitted" class="score">得分 {{ score }} / {{ scene.questions.length }}</p>
      <button class="btn btn-primary" type="button" :disabled="!allAnswered || submitted" @click="submit">
        {{ submitted ? '已提交' : '提交检验' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.quiz {
  display: grid;
  gap: 14px;
}

.badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  color: #8a5a10;
  background: var(--accent-soft);
  padding: 3px 10px;
  border-radius: 999px;
}

h2 {
  margin: 8px 0 4px;
  font-family: var(--font-display);
}

.lead {
  margin: 0;
  color: var(--muted);
}

.card {
  padding: 16px 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--line);
}

h3 {
  margin: 0 0 12px;
  font-size: 1.05rem;
  line-height: 1.45;
}

.opt {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 10px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
}

.opt:hover:not(.locked) {
  background: var(--brand-soft);
}

.opt.correct {
  background: rgba(47, 143, 107, 0.12);
  border-color: rgba(47, 143, 107, 0.35);
}

.opt.wrong {
  background: rgba(180, 35, 24, 0.08);
  border-color: rgba(180, 35, 24, 0.25);
}

.explain {
  margin: 8px 0 0;
  color: var(--brand-deep);
  font-size: 0.92rem;
  line-height: 1.5;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.score {
  margin: 0;
  font-weight: 700;
  color: var(--brand);
}
</style>
