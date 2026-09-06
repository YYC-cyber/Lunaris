import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginWindow.vue') },
    { path: '/', name: 'main', component: () => import('../views/MainWindow.vue') },
    { path: '/search', name: 'search', component: () => import('../views/SearchView.vue') },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'login' && !token) return { name: 'login' }
  if (to.name === 'login' && token) return { name: 'main' }
  return true
})

export default router
