<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { auth, toast } from '../store'

const router = useRouter()
const username = ref('')
const password = ref('')
const confirm = ref('')
const busy = ref(false)

async function submit() {
  if (!/^[A-Za-z0-9_-]{3,32}$/.test(username.value.trim())) {
    return toast('用户名需为 3-32 位字母、数字、下划线或短横线', 'error')
  }
  if (password.value.length < 6) return toast('密码至少 6 位', 'error')
  if (password.value !== confirm.value) return toast('两次输入的密码不一致', 'error')

  busy.value = true
  try {
    const data = await auth.register(username.value.trim(), password.value)
    toast(`注册成功，欢迎 ${data.user.username}`, 'ok')
    router.push('/')
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="container narrow">
    <form class="card form" @submit.prevent="submit">
      <h2>注册新账号</h2>
      <p class="muted">只需用户名 + 密码即可注册</p>

      <label>用户名<input v-model="username" placeholder="3-32 位字母、数字、_ 或 -" /></label>
      <label>密码<input v-model="password" type="password" placeholder="至少 6 位" /></label>
      <label>确认密码<input v-model="confirm" type="password" placeholder="再次输入密码" /></label>

      <button type="submit" :disabled="busy">
        <span v-if="busy" class="spinner" /><span v-else>注册并登录</span>
      </button>

      <p class="muted center">已有账号？<RouterLink to="/login" class="link">去登录</RouterLink></p>
    </form>
  </div>
</template>

<style scoped>
.narrow { max-width: 420px; padding-top: 40px; }
.form { padding: 26px; display: flex; flex-direction: column; gap: 14px; }
h2 { margin: 0; font-size: 20px; }
.form p { margin: 0; font-size: 12.5px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ink-2); }
.form button { margin-top: 6px; padding: 11px; }
.link { color: var(--brand); }
</style>
