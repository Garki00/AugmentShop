<script setup>
import { nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { askAi } from '../api'
import { toast } from '../store'

const props = defineProps({
  product: { type: Object, required: true }
})

const QUICK = ['这件商品多少钱？', '它的主要卖点是什么？', '适合什么场景或人群使用？', '能推荐一些相似商品吗？']

const messages = ref([])
const related = ref([])
const input = ref('')
const sending = ref(false)
const listEl = ref(null)

function scrollToEnd() {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}

async function send(text) {
  const question = (text ?? input.value).trim()
  if (!question || sending.value) return

  const history = messages.value.map(({ role, content }) => ({ role, content }))
  messages.value.push({ role: 'user', content: question })
  input.value = ''
  sending.value = true
  scrollToEnd()

  try {
    const data = await askAi({ product_id: props.product.id, question, history })
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      meta: {
        model: data.model,
        embedModel: data.embedding_model,
        embeddingUsed: data.embedding_used,
        degraded: data.degraded,
        elapsed: data.elapsed_ms
      }
    })
    related.value = data.related || []
    if (data.degraded) toast('AI 服务不可用，已用商品库信息作答', 'error')
  } catch (err) {
    messages.value.push({ role: 'assistant', content: `抱歉，客服暂时无法作答：${err.message}`, meta: { degraded: true } })
  } finally {
    sending.value = false
    scrollToEnd()
  }
}

function clearChat() {
  messages.value = []
  related.value = []
}

watch(() => props.product?.id, clearChat)
</script>

<template>
  <aside class="chat card">
    <header class="chat-head">
      <div class="row">
        <span class="avatar">AI</span>
        <div>
          <b>AI 智能客服</b>
          <div class="muted" style="font-size: 12px">已读取本商品名称 / 价格 / 简介</div>
        </div>
      </div>
      <button v-if="messages.length" class="ghost sm" @click="clearChat">清空</button>
    </header>

    <div ref="listEl" class="msgs">
      <div v-if="!messages.length" class="hello">
        <p>你好！我是「{{ product.name }}」的专属客服 👋</p>
        <p class="muted">价格、卖点、适用场景、相似商品，都可以问我。</p>
      </div>

      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <div class="bubble">{{ m.content }}</div>
        <div v-if="m.meta" class="meta muted">
          <span v-if="m.meta.model">{{ m.meta.model }}</span>
          <span v-if="m.meta.embeddingUsed">· 已用 {{ m.meta.embedModel }} 检索相关商品</span>
          <span v-if="m.meta.elapsed">· {{ m.meta.elapsed }}ms</span>
          <span v-if="m.meta.degraded" class="warn">· 降级回答</span>
        </div>
      </div>

      <div v-if="sending" class="msg assistant">
        <div class="bubble typing"><span class="dot" /><span class="dot" /><span class="dot" /></div>
      </div>
    </div>

    <div v-if="related.length" class="related">
      <div class="muted" style="font-size: 12px; margin-bottom: 6px">相关商品（向量检索）</div>
      <div class="chips">
        <RouterLink v-for="r in related" :key="r.id" :to="`/product/${r.id}`" class="chip">
          <img :src="r.image" @error="$event.target.src = '/static/products/placeholder.svg'" />
          <span class="line-clamp-2">{{ r.name }}</span>
          <b>${{ Number(r.price).toFixed(2) }}</b>
        </RouterLink>
      </div>
    </div>

    <div class="quick">
      <button v-for="q in QUICK" :key="q" class="ghost sm" :disabled="sending" @click="send(q)">{{ q }}</button>
    </div>

    <form class="composer" @submit.prevent="send()">
      <input v-model="input" placeholder="输入你的问题，回车发送…" :disabled="sending" />
      <button type="submit" :disabled="sending || !input.trim()">
        <span v-if="sending" class="spinner" /><span v-else>发送</span>
      </button>
    </form>
  </aside>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; height: 620px; padding: 14px; gap: 10px; }
.chat-head { display: flex; align-items: center; justify-content: space-between; }
.avatar {
  width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; color: #fff; font-weight: 700;
  background: linear-gradient(135deg, var(--brand), var(--brand-2));
}
.msgs { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding: 10px 4px; background: #fafbff; border-radius: 12px; }
.hello p { margin: 4px 0; font-size: 13.5px; }
.msg { display: flex; flex-direction: column; gap: 3px; max-width: 92%; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.bubble { padding: 9px 12px; border-radius: 12px; background: #fff; border: 1px solid var(--line); white-space: pre-wrap; word-break: break-word; font-size: 13.5px; }
.msg.user .bubble { background: var(--brand); color: #fff; border-color: transparent; }
.meta { font-size: 11px; }
.warn { color: #d92d20; }
.typing { display: flex; gap: 4px; align-items: center; }
.typing .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-3); animation: blink 1.2s infinite; }
.typing .dot:nth-child(2) { animation-delay: .2s; }
.typing .dot:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 60%, 100% { opacity: .25; } 30% { opacity: 1; } }
.quick { display: flex; flex-wrap: wrap; gap: 6px; }
.quick button { font-size: 12px; }
.related .chips { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.chip {
  min-width: 108px; max-width: 118px; border: 1px solid var(--line); border-radius: 10px; padding: 6px;
  display: flex; flex-direction: column; gap: 4px; font-size: 11.5px; background: #fff;
}
.chip img { height: 54px; object-fit: contain; }
.chip b { color: var(--price); }
.composer { display: flex; gap: 8px; }
.composer button { min-width: 74px; }
</style>
