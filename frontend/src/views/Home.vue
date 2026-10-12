<script setup>
import { onMounted, ref } from 'vue'
import { fetchProducts, fetchRecommend } from '../api'
import { toast } from '../store'
import RecommendCarousel from '../components/RecommendCarousel.vue'
import ProductCard from '../components/ProductCard.vue'
import Pagination from '../components/Pagination.vue'

const PAGE_SIZE = 18 // 一行 3 个 × 最多 6 行

/* ---------------- 推荐（每次打开页面重新随机抽取 5 个） ---------------- */
const recommend = ref([])
const recLoading = ref(true)

async function loadRecommend() {
  recLoading.value = true
  try {
    const data = await fetchRecommend(5)
    recommend.value = data.items
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    recLoading.value = false
  }
}

/* ---------------- 商品列表 / 搜索 ---------------- */
const items = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(1)
const loading = ref(false)
const keyword = ref('')
const activeKeyword = ref('')
const listAnchor = ref(null)
let reqSeq = 0 // guards against out-of-order responses when paging/seaching quickly

async function loadProducts(targetPage = 1, kw = activeKeyword.value) {
  const myReq = ++reqSeq
  loading.value = true
  try {
    const data = await fetchProducts({ keyword: kw, page: targetPage, page_size: PAGE_SIZE })
    if (myReq !== reqSeq) return // a newer request already resolved; drop this stale payload
    items.value = data.items
    total.value = data.total
    page.value = data.page
    pages.value = data.pages
  } catch (err) {
    if (myReq === reqSeq) toast(err.message, 'error')
  } finally {
    if (myReq === reqSeq) loading.value = false
  }
}

function scrollToList() {
  if (listAnchor.value) listAnchor.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function search() {
  activeKeyword.value = keyword.value.trim()
  loadProducts(1)
  scrollToList()
}

function resetSearch() {
  keyword.value = ''
  activeKeyword.value = ''
  loadProducts(1)
}

function changePage(p) {
  loadProducts(p)
  scrollToList()
}

onMounted(() => {
  loadRecommend()
  loadProducts(1)
})
</script>

<template>
  <div class="container">
    <!-- 推荐区 -->
    <div class="rec-head">
      <RecommendCarousel :items="recommend" :loading="recLoading" />
      <button class="ghost sm reroll" :disabled="recLoading" @click="loadRecommend">🎲 换一批</button>
    </div>

    <!-- 搜索框（推荐下方） -->
    <section class="search card">
      <form class="searchbar" @submit.prevent="search">
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索商品名称、简介、品牌或类目，例如“mascara” / “phone” / “furniture”"
        />
        <button type="submit" :disabled="loading">搜索</button>
        <button v-if="activeKeyword" type="button" class="ghost" @click="resetSearch">重置</button>
      </form>
      <div class="hint muted">
        <template v-if="activeKeyword">
          关键词「<b>{{ activeKeyword }}</b>」共匹配 {{ total }} 件商品
        </template>
        <template v-else>搜索框留空时展示全部原始商品数据（共 {{ total }} 件）</template>
      </div>
    </section>

    <!-- 商品列表 -->
    <section ref="listAnchor" class="list card">
      <header class="list-head">
        <h3>{{ activeKeyword ? `搜索结果：${activeKeyword}` : '全部商品' }}</h3>
        <span class="muted">{{ total }} 件 · 每页 {{ PAGE_SIZE }} 件（3 列 × 最多 6 行）</span>
      </header>

      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="!items.length" class="empty">
        没有找到匹配的商品，换个关键词试试
      </div>
      <div v-else class="grid">
        <ProductCard v-for="p in items" :key="p.id" :product="p" />
      </div>

      <Pagination
        v-if="!loading && items.length"
        :page="page"
        :pages="pages"
        :total="total"
        :page-size="PAGE_SIZE"
        @update:page="changePage"
      />
    </section>
  </div>
</template>

<style scoped>
.rec-head { position: relative; }
.reroll { position: absolute; right: 22px; bottom: 16px; z-index: 2; }
.search { padding: 16px 20px; margin-bottom: 18px; }
.searchbar { display: flex; gap: 10px; }
.searchbar input { flex: 1; font-size: 15px; padding: 12px 16px; border-radius: 12px; }
.searchbar button { padding: 12px 26px; border-radius: 12px; font-size: 15px; }
.hint { margin-top: 8px; font-size: 12.5px; }
.list { padding: 18px 20px 22px; }
.list-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.list-head h3 { margin: 0; font-size: 17px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
@media (max-width: 960px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 620px) { .grid { grid-template-columns: 1fr; } }
</style>
