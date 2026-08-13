<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import MorphIcon from '../components/MorphIcon.vue'
import WordMeaningArt from '../components/WordMeaningArt.vue'
import { api } from '../lib/api'
import { speakWord, speakEnglish } from '../lib/speech'
import { useAuth } from '../stores/auth'

type Segment = {
  text: string
  type: string
  gloss: string
  icon: string
  color: string
}

type Meaning = { pos: string; text: string; example?: string; example_cn?: string; source?: string }

type Word = {
  id: number
  word: string
  phonetic: string
  meaning: string
  meanings?: Meaning[]
  example: string
  level: string
  status: string
  image_key: string
  morph_story: string
  segments: Segment[]
  is_long: boolean
}

type Prefs = {
  daily_count: number
  level_max: string
  prefer_long: boolean
  show_morph: boolean
  auto_speak: boolean
}

const auth = useAuth()
const router = useRouter()
const words = ref<Word[]>([])
const idx = ref(0)
const flipped = ref(false)
const showMorph = ref(true)
const showSettings = ref(false)
const prefs = reactive<Prefs>({
  daily_count: 8,
  level_max: 'B2',
  prefer_long: true,
  show_morph: true,
  auto_speak: false,
})
const saving = ref(false)
const tip = ref('')

const current = () => words.value[idx.value]

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push('/auth')
    return
  }
  const p = await api<Prefs>('/vocab/prefs')
  Object.assign(prefs, p)
  showMorph.value = p.show_morph
  words.value = await api('/vocab/today')
  idx.value = 0
  flipped.value = false
}

async function savePrefs() {
  saving.value = true
  tip.value = ''
  try {
    const p = await api<Prefs>('/vocab/prefs', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    })
    Object.assign(prefs, p)
    showMorph.value = p.show_morph
    tip.value = '设置已保存'
    words.value = await api('/vocab/today')
    idx.value = 0
  } finally {
    saving.value = false
  }
}

async function mark(status: string) {
  const w = current()
  if (!w) return
  await api(`/vocab/${w.id}/progress`, { method: 'POST', body: JSON.stringify({ status }) })
  w.status = status
  next()
}

async function speak() {
  const w = current()
  if (!w) return
  if (flipped.value) {
    const examples = (w.meanings || [])
      .map((m) => (m.example || '').trim())
      .filter(Boolean)
    const text = examples.length ? examples.join('. ') : (w.example || '').trim()
    if (text) {
      await speakEnglish(text, { lang: 'en', mode: 'sentence' })
      return
    }
  }
  await speakWord(w.word)
}

function next() {
  flipped.value = false
  if (idx.value < words.value.length - 1) idx.value += 1
  else idx.value = 0
  if (prefs.auto_speak) void speak()
}

function prev() {
  flipped.value = false
  idx.value = idx.value > 0 ? idx.value - 1 : words.value.length - 1
}

function typeLabel(t: string) {
  if (t === 'prefix') return '前缀'
  if (t === 'suffix') return '后缀'
  return '词根'
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="head">
      <div>
        <h1>每日单词</h1>
        <p class="sub">词根词缀拆解 + 图画联想，复杂单词不用死磕字母串。</p>
      </div>
      <div class="head-actions">
        <label class="toggle" v-if="current()?.is_long || prefs.show_morph">
          <input v-model="showMorph" type="checkbox" />
          显示拆解
        </label>
        <button type="button" class="ghost-btn" @click="showSettings = !showSettings">
          {{ showSettings ? '收起设置' : '学习设置' }}
        </button>
      </div>
    </header>

    <section v-if="showSettings" class="settings">
      <h3>学习偏好</h3>
      <div class="settings-grid">
        <label>
          每日词量
          <input v-model.number="prefs.daily_count" type="number" min="3" max="30" />
        </label>
        <label>
          最高难度
          <select v-model="prefs.level_max">
            <option value="A1">A1</option>
            <option value="A2">A2</option>
            <option value="B1">B1</option>
            <option value="B2">B2</option>
            <option value="C1">C1</option>
            <option value="C2">C2</option>
          </select>
        </label>
        <label class="check">
          <input v-model="prefs.prefer_long" type="checkbox" />
          优先长词拆解
        </label>
        <label class="check">
          <input v-model="prefs.show_morph" type="checkbox" />
          默认显示词根词缀
        </label>
        <label class="check">
          <input v-model="prefs.auto_speak" type="checkbox" />
          切词自动朗读
        </label>
      </div>
      <div class="settings-actions">
        <button type="button" class="save" :disabled="saving" @click="savePrefs">
          {{ saving ? '保存中…' : '保存并刷新词单' }}
        </button>
        <span v-if="tip" class="tip">{{ tip }}</span>
      </div>
    </section>

    <article v-if="current()" class="card" @click="flipped = !flipped">
      <div class="card-top">
        <WordMeaningArt
          :image-key="current().image_key"
          :image-url="(current() as any).image_url"
          :meaning="current().meaning"
          :word="current().word"
        />
        <div class="meta">
          <template v-if="!flipped">
            <h2 class="word">{{ current().word }}</h2>
            <p class="ph">{{ current().phonetic }}</p>
            <small>{{ current().level }} · {{ current().status }}</small>
            <p class="hint">点击卡片查看释义与例句</p>
          </template>
          <template v-else>
            <ul class="meanings">
              <li v-for="(m, i) in current().meanings || []" :key="i" class="sense">
                <p class="sense-head">
                  <em v-if="m.pos">{{ m.pos }}</em>
                  {{ m.text }}
                </p>
                <p v-if="m.example" class="example">{{ m.example }}</p>
                <p v-if="m.example_cn" class="example-cn">{{ m.example_cn }}</p>
                <p v-if="m.source" class="exam-src">{{ m.source }}</p>
              </li>
            </ul>
            <template v-if="!current().meanings?.length">
              <h2 class="meaning">{{ current().meaning }}</h2>
              <p class="example">{{ current().example }}</p>
            </template>
            <p class="ph">{{ current().word }} · {{ current().phonetic }}</p>
          </template>
        </div>
      </div>

      <section
        v-if="showMorph && current().segments?.length"
        class="morph"
        @click.stop
      >
        <div class="morph-head">
          <span class="badge">词根词缀可视化</span>
          <span v-if="current().is_long" class="tip">长单词专用 · 拆成小块记</span>
        </div>

        <div class="segments">
          <div
            v-for="(s, i) in current().segments"
            :key="s.text + i"
            class="seg"
            :style="{ '--c': s.color }"
          >
            <MorphIcon :name="s.icon" :color="s.color" />
            <div>
              <strong>{{ s.text }}</strong>
              <em>{{ typeLabel(s.type) }} · {{ s.gloss }}</em>
            </div>
            <span v-if="i < current().segments.length - 1" class="plus">+</span>
          </div>
        </div>

        <p v-if="current().morph_story" class="story">
          → {{ current().morph_story }}
        </p>

        <div class="built">
          <span
            v-for="s in current().segments"
            :key="'b' + s.text"
            class="chip"
            :style="{ background: s.color }"
          >{{ s.text }}</span>
          <span class="eq">=</span>
          <span class="chip result">{{ current().meaning.split('；')[0] || current().meaning }}</span>
        </div>
      </section>
    </article>

    <div class="actions" v-if="current()">
      <button type="button" @click="prev">上一个</button>
      <button type="button" @click="void speak()">朗读</button>
      <button type="button" class="ghost" @click="mark('hard')">困难</button>
      <button type="button" class="ghost" @click="mark('learning')">学习中</button>
      <button type="button" @click="mark('known')">认识</button>
      <button type="button" @click="next">下一个</button>
    </div>
    <p class="count">{{ idx + 1 }} / {{ words.length }}</p>
  </div>
</template>

<style scoped>
.page {
  width: min(720px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 0 0 6px;
}
.sub {
  margin: 0;
  color: var(--muted);
  line-height: 1.5;
}
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--brand-deep);
  white-space: nowrap;
  cursor: pointer;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.ghost-btn {
  border: 1px solid rgba(15, 107, 92, 0.3);
  background: #fff;
  color: var(--brand);
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 600;
}
.settings {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
  text-align: left;
}
.settings h3 {
  margin: 0 0 10px;
  font-size: 1rem;
}
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}
.settings-grid label {
  display: grid;
  gap: 4px;
  font-size: 0.88rem;
  color: var(--muted);
}
.settings-grid input[type='number'],
.settings-grid select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  color: var(--ink, #14212b);
}
.settings-grid .check {
  display: flex;
  align-items: center;
  gap: 8px;
}
.settings-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.save {
  border: 0;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  padding: 8px 14px;
  cursor: pointer;
  font-weight: 600;
}
.tip {
  color: var(--brand-deep);
  font-size: 0.88rem;
}
.card {
  margin: 22px 0;
  border-radius: 20px;
  background:
    radial-gradient(circle at 12% 0%, rgba(232, 163, 23, 0.12), transparent 42%),
    linear-gradient(165deg, rgba(15, 107, 92, 0.08), #fff 48%);
  border: 1px solid rgba(15, 107, 92, 0.14);
  padding: 18px;
  cursor: pointer;
  text-align: left;
}
.card-top {
  display: flex;
  gap: 16px;
  align-items: center;
}
.meta {
  min-width: 0;
  flex: 1;
}
.word {
  margin: 0 0 6px;
  font-size: clamp(1.6rem, 4vw, 2.2rem);
  font-family: 'Noto Serif SC', Georgia, serif;
  letter-spacing: 0.02em;
  color: var(--brand-deep);
}
.meaning {
  margin: 0 0 8px;
  font-size: 1.45rem;
  font-family: 'Noto Serif SC', serif;
  color: var(--brand-deep);
}
.ph {
  margin: 0;
  color: var(--brand);
  font-weight: 600;
}
.example {
  margin: 0 0 4px;
  color: #334155;
  line-height: 1.55;
  background: rgba(232, 163, 23, 0.12);
  padding: 8px 12px;
  border-radius: 10px;
}
.example-cn {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 0.85rem;
}
.exam-src {
  margin: 0 0 8px;
  color: #b45309;
  font-size: 0.75rem;
  font-weight: 600;
}
.meanings {
  list-style: none;
  padding: 0;
  margin: 0 0 10px;
  display: grid;
  gap: 10px;
}
.sense-head {
  margin: 0 0 6px;
  font-weight: 600;
  color: var(--brand-deep);
}
.meanings em {
  color: var(--brand);
  margin-right: 6px;
  font-style: normal;
  font-size: 0.85rem;
}
.hint,
small {
  color: var(--muted);
}
.hint {
  margin: 10px 0 0;
  font-size: 0.82rem;
}
.morph {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed rgba(15, 107, 92, 0.2);
}
.morph-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.12);
  color: var(--brand-deep);
  font-size: 0.78rem;
  font-weight: 700;
}
.tip {
  color: var(--muted);
  font-size: 0.8rem;
}
.segments {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: stretch;
}
.seg {
  position: relative;
  display: flex;
  gap: 10px;
  align-items: center;
  min-width: 140px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
  box-shadow: 0 4px 14px rgba(15, 40, 35, 0.04);
}
.seg strong {
  display: block;
  font-size: 1.05rem;
  color: var(--c);
  font-family: Georgia, 'Times New Roman', serif;
}
.seg em {
  display: block;
  margin-top: 2px;
  font-style: normal;
  font-size: 0.78rem;
  color: var(--muted);
}
.plus {
  position: absolute;
  right: -14px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.2);
  color: var(--brand);
  font-size: 0.85rem;
  display: grid;
  place-items: center;
  font-weight: 700;
}
.story {
  margin: 14px 0 0;
  color: var(--brand-deep);
  font-weight: 600;
  line-height: 1.55;
  font-size: 0.95rem;
}
.built {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
}
.chip {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 999px;
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
}
.chip.result {
  background: var(--brand-deep);
}
.eq {
  color: var(--muted);
  font-weight: 700;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 10px 14px;
  cursor: pointer;
  font-weight: 600;
}
.ghost {
  background: transparent;
  color: var(--brand);
  border: 1px solid rgba(15, 107, 92, 0.3);
}
.count {
  color: var(--muted);
  margin-top: 14px;
  text-align: center;
}
@media (max-width: 600px) {
  .card-top {
    flex-direction: column;
    align-items: flex-start;
  }
  .plus {
    display: none;
  }
}
</style>
