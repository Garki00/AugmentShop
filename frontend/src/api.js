import axios from 'axios'

const TOKEN_KEY = 'kjds_token'

const http = axios.create({ baseURL: '/api', timeout: 120000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// store.js registers its handler here at import time, so api.js stays dependency-free
export const unauthorizedHandler = { fn: null }

http.interceptors.response.use(
  (res) => res.data,
  async (error) => {
    const status = error?.response?.status
    const data = error?.response?.data
    if (status === 401 && !String(error.config?.url || '').includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY)
      if (unauthorizedHandler.fn) unauthorizedHandler.fn()
    }
    return Promise.reject(new Error(data?.message || data?.error || error.message || '请求失败'))
  }
)

// ---------------- catalogue (public) ----------------
export const fetchProducts = (params) => http.get('/products', { params })
export const fetchRecommend = (limit = 5) => http.get('/products/recommend', { params: { limit } })
export const fetchProduct = (id) => http.get(`/products/${id}`)
export const fetchCategories = () => http.get('/products/categories')
export const askAi = (payload) => http.post('/chat', payload)
export const health = () => http.get('/health')

// ---------------- auth ----------------
export const login = (username, password) => http.post('/auth/login', { username, password })
export const register = (username, password) => http.post('/auth/register', { username, password })
export const fetchMe = () => http.get('/auth/me')

// ---------------- admin ----------------
export const adminListProducts = (params) => http.get('/admin/products', { params })
export const adminCreateProduct = (payload) => http.post('/admin/products', payload)
export const adminUpdateProduct = (id, payload) => http.put(`/admin/products/${id}`, payload)
export const adminDeleteProduct = (id) => http.delete(`/admin/products/${id}`)
export const adminStats = () => http.get('/admin/stats')
export const adminRefreshEmbeddings = (force = false) => http.post('/admin/embeddings/refresh', { force })
export const adminUploadImage = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/admin/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export default http
