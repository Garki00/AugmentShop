<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { auth, toasts, toast } from './store'

const router = useRouter()

function logout() {
  auth.logout()
  toast('已退出登录')
  router.push('/')
}
</script>

<template>
  <header class="topbar">
    <div class="container bar">
      <RouterLink to="/" class="brand">
        <span class="logo">环球</span>
        <span class="brand-text">环球优选<small>Cross-border Mall</small></span>
      </RouterLink>

      <nav class="nav">
        <RouterLink to="/" exact-active-class="active">商城首页</RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" active-class="active">管理后台</RouterLink>
      </nav>

      <div class="spacer"></div>

      <div class="account">
        <template v-if="auth.isLoggedIn">
          <span class="who">
            <b>{{ auth.user.username }}</b>
            <span v-if="auth.isAdmin" class="tag">管理员</span>
          </span>
          <button class="ghost sm" @click="logout">退出</button>
        </template>
        <template v-else>
          <RouterLink to="/login"><button class="ghost sm">登录</button></RouterLink>
          <RouterLink to="/register"><button class="sm">注册</button></RouterLink>
        </template>
      </div>
    </div>
  </header>

  <main class="page">
    <RouterView />
  </main>

  <footer class="footer">
    <div class="container">
      环球优选 · Flask + Vue 3 + MySQL 跨境电商演示项目 · AI 客服由 SiliconFlow Qwen 模型驱动
    </div>
  </footer>

  <div class="toasts">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">{{ t.message }}</div>
  </div>
</template>

<style scoped>
.topbar {
  position: sticky; top: 0; z-index: 30;
  background: rgba(255, 255, 255, .92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}
.bar { display: flex; align-items: center; height: 62px; gap: 18px; }
.brand { display: flex; align-items: center; gap: 10px; }
.logo {
  width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--brand), var(--brand-2));
  color: #fff; font-weight: 700; font-size: 15px;
}
.brand-text { font-weight: 700; font-size: 17px; display: flex; flex-direction: column; line-height: 1.1; }
.brand-text small { font-weight: 400; font-size: 10px; color: var(--ink-3); letter-spacing: .5px; }
.nav { display: flex; gap: 16px; margin-left: 8px; }
.nav a { color: var(--ink-2); font-size: 14px; padding: 4px 0; border-bottom: 2px solid transparent; }
.nav a.active, .nav a:hover { color: var(--brand); border-bottom-color: var(--brand); }
.account { display: flex; align-items: center; gap: 10px; }
.who { display: flex; align-items: center; gap: 6px; color: var(--ink-2); }
.page { min-height: calc(100vh - 190px); padding: 22px 0 40px; }
.footer { border-top: 1px solid var(--line); background: #fff; color: var(--ink-3); font-size: 12.5px; padding: 16px 0; }
</style>
