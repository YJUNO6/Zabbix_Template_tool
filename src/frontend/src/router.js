import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./views/Home.vue'),
  },
  {
    path: '/translate',
    name: 'Translate',
    component: () => import('./views/Translate.vue'),
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('./views/History.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
