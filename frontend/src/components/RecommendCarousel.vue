<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  interval: { type: Number, default: 3500 }
})

const index = ref(0)
const paused = ref(false)
let timer = null

const current = computed(() => props.items[index.value] || null)

function go(i) {
  if (!props.items.length) return
  index.value = (i + props.items.length) % props.items.length
}

function start() {
  stop()
  timer = setInterval(() => {
    if (!paused.value) go(index.value + 1)
  }, props.interval)
}
function stop() {
  if (timer) clearInterval(timer)
  timer = null
}

onMounted(start)
onBeforeUnmount(stop)

defineExpose({ go, start, stop })
</script>

<template>
  <section class="hero card" @mouseenter="paused = true" @mouseleave="paused = false">
    <div class="head">
      <div>
        <h2>今日推荐</h2>
        <p class="muted">每次刷新页面都会从 {{ items.length || 5 }} 件随机商品中重新抽取，自动轮播中</p>
      </div>
      <div class="head-actions">
        <span class="counter">{{ items.length ? index + 1 : 0 }} / {{ items.length }}</span>
        <button class="ghost sm" @click="go(index - 1)">‹</button>
        <button class="ghost sm" @click="go(index + 1)">›</button>
      </div>
    </div>

    <div v-if="loading" class="skeleton">正在抽取推荐商品…</div>
    <div v-else-if="!items.length" class="skeleton">暂无推荐商品</div>

    <template v-else-if="current">
      <div class="slide" :key="current.id">
        <div class="visual">
          <img :src="current.image || current.image_remote" :alt="current.name" @error="$event.target.src = '/static/products/placeholder.svg'" />
        </div>
        <div class="info">
          <span v-if="current.category" class="tag">{{ current.category }}</span>
          <h3>{{ current.name }}</h3>
          <p class="desc line-clamp-2">{{ current.description }}</p>
          <div class="row">
            <span class="price big">${{ Number(current.price).toFixed(2) }}<small>USD</small></span>
            <RouterLink :to="`/product/${current.id}`"><button class="sm">查看详情 →</button></RouterLink>
          </div>
        </div>
      </div>

      <div class="dots">
        <span
          v-for="(item, i) in items"
          :key="item.id"
          :class="['dot', i === index ? 'on' : '']"
          @click="go(i)"
        />
      </div>
    </template>
  </section>
</template>

<style scoped>
.hero { padding: 20px 22px 14px; margin-bottom: 18px; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
h2 { margin: 0; font-size: 18px; }
.head p { margin: 2px 0 0; font-size: 12.5px; }
.head-actions { display: flex; align-items: center; gap: 8px; }
.counter { font-size: 12.5px; color: var(--ink-3); }
.skeleton { padding: 44px 0; text-align: center; color: var(--ink-3); font-size: 13px; }
.slide { display: grid; grid-template-columns: 260px 1fr; gap: 22px; align-items: center; animation: fade .35s ease; }
@keyframes fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.visual { height: 210px; padding: 12px; background: #fbfcfe; border: 1px solid var(--line); border-radius: 12px; }
.visual img { width: 100%; height: 100%; object-fit: contain; }
.info { display: flex; flex-direction: column; gap: 10px; }
.info h3 { margin: 0; font-size: 22px; }
.desc { color: var(--ink-2); margin: 0; }
.price.big { font-size: 26px; }
.dots { display: flex; gap: 7px; justify-content: center; margin-top: 16px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #dfe3ec; cursor: pointer; transition: all .2s; }
.dot.on { width: 22px; border-radius: 4px; background: var(--brand); }
@media (max-width: 720px) {
  .slide { grid-template-columns: 1fr; }
  .visual { height: 170px; }
}
</style>
