<script setup>
import { RouterLink } from 'vue-router'

const props = defineProps({
  product: { type: Object, required: true },
  showCategory: { type: Boolean, default: true }
})

function onImgError(event) {
  if (event.target.dataset.fallback) return
  event.target.dataset.fallback = '1'
  event.target.src = '/static/products/placeholder.svg'
}
</script>

<template>
  <RouterLink class="pcard card" :to="`/product/${product.id}`">
    <div class="thumb">
      <img :src="product.image || product.image_remote" :alt="product.name" loading="lazy" @error="onImgError" />
    </div>
    <div class="body">
      <div class="name line-clamp-2" :title="product.name">{{ product.name }}</div>
      <div class="meta">
        <span class="price">${{ Number(product.price).toFixed(2) }}<small>USD</small></span>
        <span v-if="showCategory && product.category" class="tag">{{ product.category }}</span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.pcard {
  display: flex; flex-direction: column; overflow: hidden;
  transition: transform .18s ease, box-shadow .18s ease;
  border: 1px solid var(--line);
}
.pcard:hover { transform: translateY(-4px); box-shadow: var(--shadow-hover); }
.thumb { height: 190px; background: #fff; padding: 12px; border-bottom: 1px solid var(--line); }
/* width/height 100% (not max-*): percentages against an auto grid row resolve to `none` and overflow */
.thumb img { width: 100%; height: 100%; object-fit: contain; }
.body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.name { font-size: 14px; font-weight: 600; min-height: 44px; }
.meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: auto; }
.price { font-size: 16px; }
</style>
