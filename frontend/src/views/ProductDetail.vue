<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { fetchProduct } from '../api'
import { toast } from '../store'
import ChatPanel from '../components/ChatPanel.vue'

const route = useRoute()
const product = ref(null)
const loading = ref(true)
const activeImage = ref('')

async function load(id) {
  loading.value = true
  try {
    const data = await fetchProduct(id)
    product.value = data.item
    activeImage.value = data.item.image || data.item.image_remote
  } catch (err) {
    toast(err.message, 'error')
    product.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => load(route.params.id))
</script>

<template>
  <div class="container">
    <RouterLink to="/" class="back muted">← 返回商品列表</RouterLink>

    <div v-if="loading" class="card empty">加载中…</div>
    <div v-else-if="!product" class="card empty">商品不存在或已被删除</div>

    <div v-else class="layout">
      <!-- 左：商品信息 -->
      <section class="card detail">
        <div class="gallery">
          <div class="stage">
            <img :src="activeImage || '/static/products/placeholder.svg'" :alt="product.name"
                 @error="$event.target.src = '/static/products/placeholder.svg'" />
          </div>
          <div class="thumbs">
            <button class="thumb" :class="{ on: activeImage === (product.image || product.image_remote) }"
                    @click="activeImage = product.image || product.image_remote">
              <img :src="product.image || product.image_remote" @error="$event.target.src = '/static/products/placeholder.svg'" />
            </button>
            <button v-if="product.image_remote && product.image_remote !== product.image" class="thumb"
                    :class="{ on: activeImage === product.image_remote }" @click="activeImage = product.image_remote">
              <img :src="product.image_remote" @error="$event.target.src = '/static/products/placeholder.svg'" />
            </button>
          </div>
        </div>

        <div class="info">
          <div class="row" style="flex-wrap: wrap">
            <span v-if="product.category" class="tag">{{ product.category }}</span>
            <span v-if="product.brand" class="tag">{{ product.brand }}</span>
            <span class="muted" style="font-size: 12.5px">SKU #{{ product.id }}</span>
          </div>
          <h1>{{ product.name }}</h1>

          <div class="pricebox">
            <span class="price big">${{ Number(product.price).toFixed(2) }}<small>USD</small></span>
            <span class="muted" style="font-size: 12.5px">含跨境直邮 · 支持 7 天无理由</span>
          </div>

          <div class="stats">
            <div><b>{{ product.rating ? Number(product.rating).toFixed(1) : '—' }}</b><span class="muted">评分</span></div>
            <div><b>{{ product.stock }}</b><span class="muted">库存</span></div>
            <div><b>{{ product.brand || '—' }}</b><span class="muted">品牌</span></div>
            <div><b>{{ product.category || '—' }}</b><span class="muted">类目</span></div>
          </div>

          <h4>商品简介</h4>
          <p class="desc">{{ product.description || '暂无简介' }}</p>

          <div class="row buy">
            <button :disabled="!product.stock">加入购物车</button>
            <button class="ghost">收藏</button>
            <span class="muted" style="font-size: 12.5px">（演示站点，不产生真实订单）</span>
          </div>
        </div>
      </section>

      <!-- 右：AI 客服栏 -->
      <ChatPanel :product="product" />
    </div>
  </div>
</template>

<style scoped>
.back { display: inline-block; margin: 4px 0 14px; font-size: 13px; }
.back:hover { color: var(--brand); }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 390px; gap: 18px; align-items: start; }
.detail { display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 22px; padding: 22px; }
/* NB: keep this class name distinct from the generic `.price.big` / other `.big` users */
.stage { height: 320px; padding: 12px; background: #fbfcfe; border: 1px solid var(--line); border-radius: 12px; }
.stage img { width: 100%; height: 100%; object-fit: contain; }
.thumbs { display: flex; gap: 8px; margin-top: 10px; }
.thumb { width: 66px; height: 66px; padding: 4px; background: #fff; border: 1px solid var(--line); border-radius: 10px; }
.thumb.on { border-color: var(--brand); }
.thumb img { width: 100%; height: 100%; object-fit: contain; }
.info h1 { font-size: 24px; margin: 10px 0 8px; line-height: 1.35; }
.pricebox { display: flex; align-items: baseline; gap: 12px; padding: 12px 14px; background: #fff6f6; border-radius: 12px; margin: 6px 0 14px; }
.price.big { font-size: 28px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px; }
.stats div { background: #f7f9fd; border-radius: 10px; padding: 8px 10px; display: flex; flex-direction: column; font-size: 12.5px; min-width: 0; overflow-wrap: anywhere; }
.stats b { font-size: 14px; }
h4 { margin: 8px 0 6px; font-size: 15px; }
.desc { color: var(--ink-2); margin: 0 0 18px; white-space: pre-wrap; }
.buy { flex-wrap: wrap; }
.buy button { padding: 11px 22px; border-radius: 12px; white-space: nowrap; }
@media (max-width: 1080px) { .layout { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .detail { grid-template-columns: 1fr; } }
</style>
