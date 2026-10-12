<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { auth, toast } from '../store'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const busy = ref(false)

async function submit() {
  if (!username.value || !password.value) return toast('请输入用户名和密码', 'error')
  busy.value = true
  try {
    const data = await auth.login(username.value.trim(), password.value)
    toast(`欢迎回来，${data.user.username}`, 'ok')
    router.push(route.query.redirect || (data.user.is_admin ? '/admin' : '/'))
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
      <h2>用户登录</h2>
      <p class="muted">演示管理员账号：admin / admin123</p>

      <label>用户名<input v-model="username" autocomplete="username" placeholder="请输入用户名" /></label>
      <label>密码<input v-model="password" type="password" autocomplete="current-password" placeholder="请输入密码" /></label>

      <button type="submit" :disabled="busy">
        <span v-if="busy" class="spinner" /><span v-else>登录</span>
      </button>

      <p class="muted center">还没有账号？<RouterLink to="/register" class="link">立即注册</RouterLink></p>
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
