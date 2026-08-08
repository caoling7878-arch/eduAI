<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchEbook } from '../lib/api'

const props = defineProps<{ id: string }>()
const book = ref<any>(null)
const active = ref(0)

onMounted(async () => {
  book.value = await fetchEbook(Number(props.id))
})
</script>

<template>
  <div class="page" v-if="book">
    <RouterLink to="/ebooks" class="back">← 返回书单</RouterLink>
    <h1>{{ book.title }}</h1>
    <p class="sub">{{ book.summary }}</p>
    <div class="layout">
      <aside>
        <button
          v-for="(c, i) in book.chapters"
          :key="c.id"
          type="button"
          :class="{ on: i === active }"
          @click="active = i"
        >
          {{ c.title }}
        </button>
      </aside>
      <article v-if="book.chapters[active]">
        <h2>{{ book.chapters[active].title }}</h2>
        <pre>{{ book.chapters[active].content }}</pre>
      </article>
    </div>
  </div>
</template>

<style scoped>
.page {
  width: min(960px, 100%);
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.back {
  color: var(--brand);
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 12px 0 6px;
}
.sub {
  color: var(--muted);
}
.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  margin-top: 18px;
}
aside {
  display: grid;
  gap: 6px;
  align-content: start;
}
aside button {
  text-align: left;
  border: 1px solid rgba(15, 107, 92, 0.12);
  background: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
}
aside button.on {
  background: rgba(15, 107, 92, 0.1);
  color: var(--brand-deep);
  border-color: transparent;
}
article {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(15, 107, 92, 0.1);
}
pre {
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.8;
  margin: 0;
  color: var(--ink, #1a2a28);
}
@media (max-width: 800px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
