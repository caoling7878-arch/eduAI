<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import MathExpr from '../components/MathExpr.vue'
import { deleteWrong, fetchWrongbook, masterWrong } from '../lib/api'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const rows = ref<any[]>([])
const showMastered = ref(false)

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/wrongbook' } })
    return
  }
  rows.value = await fetchWrongbook(showMastered.value ? undefined : false)
  if (!showMastered.value) {
    rows.value = rows.value.filter((r) => !r.mastered)
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header>
      <h1>错题本</h1>
      <label class="toggle">
        <input v-model="showMastered" type="checkbox" @change="load" />
        显示已掌握
      </label>
    </header>
    <ul>
      <li v-for="w in rows" :key="w.id" :class="{ mastered: w.mastered }">
        <div class="kp">{{ w.knowledge_points || '未标注' }} · {{ w.source }}</div>
        <h2><MathExpr :text="w.stem" /></h2>
        <p class="ans-line">
          <b>你的答案：</b>
          <MathExpr :text="w.user_answer || '（空）'" />
        </p>
        <p class="ans-line">
          <b>参考答案：</b>
          <MathExpr :text="w.correct_answer" />
        </p>
        <p v-if="w.analysis" class="analysis">{{ w.analysis }}</p>
        <div class="actions">
          <button v-if="!w.mastered" type="button" @click="masterWrong(w.id).then(load)">标为已掌握</button>
          <button type="button" class="ghost" @click="deleteWrong(w.id).then(load)">删除</button>
        </div>
      </li>
    </ul>
    <p v-if="!rows.length" class="muted empty">
      暂无错题。
      <RouterLink to="/practice">去做练习</RouterLink>
      ·
      <RouterLink to="/recommend">薄弱推荐</RouterLink>
      ·
      <RouterLink to="/courses/math-calc">数学计算</RouterLink>
    </p>
  </div>
</template>

<style scoped>
.page {
  width: min(820px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  margin-bottom: 18px;
}
h1 {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
}
.toggle {
  color: var(--muted);
  display: flex;
  gap: 6px;
  align-items: center;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}
li {
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 16px;
  padding: 16px;
}
li.mastered {
  opacity: 0.65;
}
.kp {
  color: var(--brand);
  font-size: 0.85rem;
  margin-bottom: 6px;
}
h2 {
  margin: 0 0 10px;
  font-size: 1.05rem;
}
.ans-line {
  margin: 6px 0;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
p {
  margin: 6px 0;
  color: var(--muted);
}
.analysis {
  background: rgba(15, 107, 92, 0.06);
  padding: 10px;
  border-radius: 10px;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}
.ghost {
  background: transparent;
  color: var(--brand);
  border: 1px solid rgba(15, 107, 92, 0.3);
}
.muted {
  color: var(--muted);
}
.empty a {
  color: var(--brand);
  font-weight: 600;
  margin: 0 4px;
}
</style>
