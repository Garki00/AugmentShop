import { reactive } from 'vue'
import * as api from './api'

const TOKEN_KEY = 'kjds_token'

export const auth = reactive({
  token: '',
  user: null,
  loading: false,

  get isLoggedIn() {
    return Boolean(this.user)
  },
  get isAdmin() {
    return Boolean(this.user && this.user.is_admin)
  },

  restore() {
    this.token = localStorage.getItem(TOKEN_KEY) || ''
  },

  setSession(token, user) {
    this.token = token
    this.user = user
    if (token) localStorage.setItem(TOKEN_KEY, token)
  },

  async login(username, password) {
    const data = await api.login(username, password)
    this.setSession(data.token, data.user)
    return data
  },

  async register(username, password) {
    const data = await api.register(username, password)
    this.setSession(data.token, data.user)
    return data
  },

  async fetchMe() {
    const data = await api.fetchMe()
    this.user = data.user
    return data.user
  },

  logout() {
    this.token = ''
    this.user = null
    localStorage.removeItem(TOKEN_KEY)
  }
})

export const toasts = reactive([])

export function toast(message, type = '') {
  const id = Date.now() + Math.random()
  toasts.push({ id, message, type })
  setTimeout(() => {
    const idx = toasts.findIndex((t) => t.id === id)
    if (idx >= 0) toasts.splice(idx, 1)
  }, 3200)
}

// a 401 anywhere drops the session (handled by the axios interceptor in api.js)
api.unauthorizedHandler.fn = () => {
  auth.user = null
  auth.token = ''
  toast('登录状态已失效，请重新登录', 'error')
}
