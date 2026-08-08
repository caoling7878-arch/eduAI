<script setup lang="ts">
/**
 * 分数显示为「分子 / 分数线 / 分母」，不改变题型。
 * 支持：5/9、1又2/3（带分数）、整数与运算符。
 */
import { computed } from 'vue'

const props = defineProps<{
  text: string
}>()

type Tok =
  | { t: 'text'; v: string }
  | { t: 'int'; v: string }
  | { t: 'frac'; n: string; d: string; sign?: string }
  | { t: 'mixed'; whole: string; n: string; d: string; sign?: string }
  | { t: 'op'; v: string }

const MIXED = /(-?)(\d+)又(\d+)[/／](\d+)/
const FRAC = /(-?)(\d+)[/／](\d+)/
const INT = /\d+(?:\.\d+)?/
const OP = /[+\-×÷＊*○=＝＞＜><]/

const OP_MAP: Record<string, string> = {
  '+': '+',
  '-': '−',
  '×': '×',
  '*': '×',
  '＊': '×',
  '÷': '÷',
  '=': '=',
  '＝': '=',
  '○': '○',
  '>': '>',
  '＞': '>',
  '<': '<',
  '＜': '<',
}

function tokenize(src: string): Tok[] {
  const s = (src || '').trim()
  if (!s) return []
  const out: Tok[] = []
  let i = 0
  while (i < s.length) {
    const rest = s.slice(i)
    if (/^\s+/.test(rest)) {
      i += rest.match(/^\s+/)![0].length
      continue
    }
    let m = rest.match(new RegExp(`^${MIXED.source}`))
    if (m) {
      out.push({
        t: 'mixed',
        sign: m[1] || undefined,
        whole: m[2],
        n: m[3],
        d: m[4],
      })
      i += m[0].length
      continue
    }
    m = rest.match(new RegExp(`^${FRAC.source}`))
    if (m) {
      out.push({ t: 'frac', sign: m[1] || undefined, n: m[2], d: m[3] })
      i += m[0].length
      continue
    }
    m = rest.match(new RegExp(`^${INT.source}`))
    if (m) {
      out.push({ t: 'int', v: m[0] })
      i += m[0].length
      continue
    }
    m = rest.match(new RegExp(`^${OP.source}`))
    if (m) {
      out.push({ t: 'op', v: OP_MAP[m[0]] || m[0] })
      i += m[0].length
      continue
    }
    out.push({ t: 'text', v: s[i] })
    i += 1
  }
  return out
}

const tokens = computed(() => tokenize(props.text))
</script>

<template>
  <span class="math-expr" :aria-label="text">
    <template v-for="(tok, idx) in tokens" :key="idx">
      <span v-if="tok.t === 'text'" class="plain">{{ tok.v }}</span>
      <span v-else-if="tok.t === 'int'" class="digit">{{ tok.v }}</span>
      <span v-else-if="tok.t === 'op'" class="op">{{ tok.v }}</span>
      <span v-else-if="tok.t === 'frac'" class="piece">
        <span v-if="tok.sign" class="sign">{{ tok.sign === '-' ? '−' : tok.sign }}</span>
        <span class="frac" title="">
          <span class="num">{{ tok.n }}</span>
          <span class="bar" aria-hidden="true" />
          <span class="den">{{ tok.d }}</span>
        </span>
      </span>
      <span v-else-if="tok.t === 'mixed'" class="piece">
        <span v-if="tok.sign" class="sign">{{ tok.sign === '-' ? '−' : tok.sign }}</span>
        <span class="digit">{{ tok.whole }}</span>
        <span class="frac">
          <span class="num">{{ tok.n }}</span>
          <span class="bar" aria-hidden="true" />
          <span class="den">{{ tok.d }}</span>
        </span>
      </span>
    </template>
  </span>
</template>

<style scoped>
.math-expr {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.15em;
  font-family: 'STIX Two Math', 'Cambria Math', 'Times New Roman', 'Noto Serif SC', serif;
  font-size: 1.35rem;
  color: #1a1a1a;
  line-height: 1;
}
.piece {
  display: inline-flex;
  align-items: center;
  gap: 0.1em;
}
.digit,
.sign,
.plain {
  font-weight: 500;
  line-height: 1.2;
}
.op {
  margin: 0 0.28em;
  font-weight: 500;
  font-size: 1.05em;
}
/* 教材风格：分子 — 分数线 — 分母 */
.frac {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 0 0.08em;
  vertical-align: middle;
  min-width: 1.1em;
}
.frac .num,
.frac .den {
  display: block;
  padding: 0 0.22em;
  font-size: 0.72em;
  font-weight: 500;
  line-height: 1.15;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.frac .bar {
  display: block;
  width: 100%;
  height: 0;
  border-bottom: 1.8px solid currentColor;
  margin: 0.06em 0;
}
</style>
