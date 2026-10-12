import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { auth } from './store'
import './style.css'

// restore the JWT before the first route is resolved
auth.restore()

createApp(App).use(router).mount('#app')
