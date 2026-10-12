import { createRouter, createWebHistory } from 'vue-router'
import { auth, toast } from './store'

const routes = [
  { path: '/', name: 'home', component: () => import('./views/Home.vue') },
  { path: '/product/:id', name: 'product', component: () => import('./views/ProductDetail.vue'), props: true },
  { path: '/login', name: 'login', component: () => import('./views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('./views/Register.vue') },
  { path: '/admin', name: 'admin', component: () => import('./views/Admin.vue'), meta: { requiresAdmin: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach(async (to) => {
  if (!auth.user && auth.token) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
    }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    toast('请使用管理员账号登录后再进入后台', 'error')
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if ((to.path === '/login' || to.path === '/register') && auth.isLoggedIn) return { path: '/' }
  return true
})

export default router
