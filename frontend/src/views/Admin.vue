<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  adminCreateProduct,
  adminDeleteProduct,
  adminListProducts,
  adminRefreshEmbeddings,
  adminStats,
  adminUpdateProduct,
  adminUploadImage
} from '../api'
import { toast } from '../store'
import Pagination from '../components/Pagination.vue'

const PAGE_SIZE = 20

const stats = reactive({ products: 0, embedded: 0, categories: 0, avg_price: 0 })
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(1)
const keyword = ref('')
const activeKeyword = ref('')
const loading = ref(false)
const busy = ref(false)

/* ---------------- 弹窗表单 ---------------- */
const dialog = ref(false)
const editingId = ref(null)
const uploading = ref(false)
const form = reactive({
  name: '', price: 0, image: '', image_remote: '', description: '',
  category: '', brand: '', stock: 0, rating: 0
})

const dialogTitle = computed(() => (editingId.value ? `编辑商品 #${editingId.value}` : '新增商品'))

function resetForm() {
  Object.assign(form, {
    name: '', price: 0, image: '', image_remote: '', description: '',
    category: '', brand: '', stock: 0, rating: 0
  })
}

async function loadStats() {
  try {
    Object.assign(stats, await adminStats())
  } catch (err) {
    toast(err.message, 'error')
  }
}

async function load(targetPage = 1, kw = activeKeyword.value) {
  loading.value = true
  try {
    const data = await adminListProducts({ keyword: kw, page: targetPage, page_size: PAGE_SIZE })
    rows.value = data.items
    total.value = data.total
    page.value = data.page
    pages.value = data.pages
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    loading.value = false
  }
}

function search() {
  activeKeyword.value = keyword.value.trim()
  load(1)
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialog.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, price: row.price, image: row.image, image_remote: row.image_remote,
    description: row.description, category: row.category, brand: row.brand,
    stock: row.stock, rating: row.rating
  })
  dialog.value = true
}

async function save() {
  if (!form.name.trim()) return toast('商品名不能为空', 'error')
  busy.value = true
  const payload = { ...form, name: form.name.trim() }
  try {
    if (editingId.value) {
      await adminUpdateProduct(editingId.value, payload)
      toast('商品已更新（名称/简介变化会自动清除向量缓存）', 'ok')
    } else {
      await adminCreateProduct(payload)
      toast('商品创建成功', 'ok')
    }
    dialog.value = false
    await Promise.all([load(editingId.value ? page.value : 1), loadStats()])
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    busy.value = false
  }
}

async function remove(row) {
  if (!window.confirm(`确认删除商品「${row.name}」？该操作不可恢复。`)) return
  try {
    await adminDeleteProduct(row.id)
    toast('已删除', 'ok')
    await Promise.all([load(page.value), loadStats()])
  } catch (err) {
    toast(err.message, 'error')
  }
}

async function pickFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const data = await adminUploadImage(file)
    form.image = data.url
    toast('图片上传成功', 'ok')
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

async function rebuildEmbeddings() {
  busy.value = true
  try {
    const data = await adminRefreshEmbeddings(true)
    toast(`已用 ${data.model} 重新向量化 ${data.embedded} 件商品`, 'ok')
    await loadStats()
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  loadStats()
  load(1)
})
</script>

<template>
  <div class="container">
    <header class="head">
      <div>
        <h2>商品管理后台</h2>
        <p class="muted">增 / 删 / 改 / 查 · 共 {{ stats.products }} 件商品</p>
      </div>
      <div class="row">
        <button class="ghost" :disabled="busy" @click="rebuildEmbeddings">刷新 AI 向量库</button>
        <button @click="openCreate">+ 新增商品</button>
      </div>
    </header>

    <section class="cards">
      <div class="card stat"><span class="muted">商品总数</span><b>{{ stats.products }}</b></div>
      <div class="card stat"><span class="muted">已向量化（Qwen3-Embedding）</span><b>{{ stats.embedded }}</b></div>
      <div class="card stat"><span class="muted">类目数</span><b>{{ stats.categories }}</b></div>
      <div class="card stat"><span class="muted">平均价格</span><b>${{ Number(stats.avg_price).toFixed(2) }}</b></div>
    </section>

    <section class="card table-card">
      <form class="toolbar" @submit.prevent="search">
        <input v-model="keyword" placeholder="按商品名 / 品牌 / 类目搜索" />
        <button type="submit">搜索</button>
        <button v-if="activeKeyword" type="button" class="ghost" @click="keyword = ''; activeKeyword = ''; load(1)">重置</button>
      </form>

      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="!rows.length" class="empty">没有商品</div>
      <table v-else>
        <thead>
          <tr>
            <th style="width: 64px">ID</th>
            <th style="width: 78px">图片</th>
            <th>商品名</th>
            <th style="width: 90px">价格</th>
            <th style="width: 120px">类目</th>
            <th style="width: 80px">库存</th>
            <th style="width: 150px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td class="muted">{{ row.id }}</td>
            <td>
              <img class="mini" :src="row.image" @error="$event.target.src = '/static/products/placeholder.svg'" />
            </td>
            <td>
              <div class="name">{{ row.name }}</div>
              <div class="muted clip">{{ row.description }}</div>
            </td>
            <td class="price">${{ Number(row.price).toFixed(2) }}</td>
            <td><span class="tag">{{ row.category || '—' }}</span></td>
            <td>{{ row.stock }}</td>
            <td class="row">
              <button class="ghost sm" @click="openEdit(row)">编辑</button>
              <button class="danger sm" @click="remove(row)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <Pagination
        v-if="!loading && rows.length"
        :page="page" :pages="pages" :total="total" :page-size="PAGE_SIZE"
        @update:page="(p) => load(p)"
      />
    </section>

    <!-- 新增 / 编辑弹窗 -->
    <div v-if="dialog" class="overlay" @click.self="dialog = false">
      <div class="modal card">
        <header class="row">
          <h3>{{ dialogTitle }}</h3>
          <div class="spacer" />
          <button class="ghost sm" @click="dialog = false">关闭</button>
        </header>

        <div class="fields">
          <label class="full">商品名 *<input v-model="form.name" placeholder="例如 Essence Mascara Lash Princess" /></label>
          <label>价格 (USD)<input v-model.number="form.price" type="number" step="0.01" min="0" /></label>
          <label>库存<input v-model.number="form.stock" type="number" min="0" /></label>
          <label>类目<input v-model="form.category" placeholder="beauty / furniture …" /></label>
          <label>品牌<input v-model="form.brand" /></label>
          <label>评分<input v-model.number="form.rating" type="number" step="0.1" min="0" max="5" /></label>

          <label class="full">
            商品图片 URL
            <input v-model="form.image" placeholder="https://... 或 /static/products/1.webp" />
          </label>
          <div class="full row upload">
            <input type="file" accept="image/*" @change="pickFile" />
            <span v-if="uploading" class="muted">上传中…</span>
          </div>
          <div class="full preview">
            <img :src="form.image || '/static/products/placeholder.svg'" @error="$event.target.src = '/static/products/placeholder.svg'" />
            <span class="muted">图片预览</span>
          </div>

          <label class="full">商品简介<textarea v-model="form.description" rows="4" /></label>
        </div>

        <footer class="row">
          <div class="spacer" />
          <button class="ghost" @click="dialog = false">取消</button>
          <button :disabled="busy" @click="save">
            <span v-if="busy" class="spinner" /><span v-else>保存</span>
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
h2 { margin: 0; font-size: 21px; }
.head p { margin: 2px 0 0; font-size: 13px; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }
.stat { padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; }
.stat b { font-size: 20px; }
.table-card { padding: 16px 18px 20px; }
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.toolbar input { max-width: 420px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 12.5px; color: var(--ink-3); font-weight: 600; padding: 8px 10px; border-bottom: 1px solid var(--line); }
td { padding: 9px 10px; border-bottom: 1px solid #f1f3f8; vertical-align: middle; font-size: 13.5px; }
.mini { width: 46px; height: 46px; object-fit: contain; background: #fff; border: 1px solid var(--line); border-radius: 8px; }
.name { font-weight: 600; max-width: 420px; }
.clip { max-width: 420px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.overlay { position: fixed; inset: 0; background: rgba(18, 24, 38, .45); display: grid; place-items: center; z-index: 50; padding: 20px; }
.modal { width: min(760px, 100%); max-height: 88vh; overflow-y: auto; padding: 20px; }
.modal h3 { margin: 0; font-size: 17px; }
.fields { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 16px 0; }
.fields .full { grid-column: 1 / -1; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ink-2); }
.preview { display: flex; align-items: center; gap: 12px; font-size: 12.5px; }
.preview img { width: 84px; height: 84px; object-fit: contain; border: 1px solid var(--line); border-radius: 10px; background: #fff; }
.upload input { padding: 7px; }
@media (max-width: 900px) { .cards { grid-template-columns: repeat(2, 1fr); } }
</style>
