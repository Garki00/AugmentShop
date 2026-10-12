<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pages: { type: Number, required: true },
  total: { type: Number, default: 0 },
  pageSize: { type: Number, default: 18 }
})
const emit = defineEmits(['update:page'])

const window_ = computed(() => {
  const out = []
  const { page, pages } = props
  const push = (v) => { if (!out.includes(v)) out.push(v) }
  if (pages <= 7) {
    for (let i = 1; i <= pages; i++) push(i)
    return out
  }
  push(1)
  if (page > 4) out.push('…')
  for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) push(i)
  if (page < pages - 3) out.push('…')
  push(pages)
  return out
})

function go(p) {
  if (p === '…' || p === props.page || p < 1 || p > props.pages) return
  emit('update:page', p)
}
</script>

<template>
  <div class="pager">
    <span class="info muted">共 {{ total }} 件商品 · 第 {{ page }}/{{ pages }} 页 · 每页 {{ pageSize }} 件</span>
    <div class="pages">
      <button class="ghost sm" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <button
        v-for="(p, i) in window_"
        :key="`${p}-${i}`"
        :class="['sm', p === page ? '' : 'ghost']"
        :disabled="p === '…'"
        @click="go(p)"
      >{{ p }}</button>
      <button class="ghost sm" :disabled="page >= pages" @click="go(page + 1)">下一页</button>
    </div>
  </div>
</template>

<style scoped>
.pager { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; justify-content: space-between; margin-top: 22px; }
.pages { display: flex; gap: 6px; flex-wrap: wrap; }
.info { font-size: 13px; }
</style>
