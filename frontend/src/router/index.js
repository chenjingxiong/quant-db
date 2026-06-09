import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/User/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/stocks',
    name: 'Stocks',
    component: () => import('../views/Stock/List.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/stocks/:symbol',
    name: 'StockDetail',
    component: () => import('../views/Stock/Detail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/futures',
    name: 'Futures',
    component: () => import('../views/Futures/List.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/indices',
    name: 'Indices',
    component: () => import('../views/Index/List.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/sectors',
    name: 'Sectors',
    component: () => import('../views/Sector/List.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/collect',
    name: 'Collect',
    component: () => import('../views/Collect/Status.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/User/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/User/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/screener',
    name: 'Screener',
    component: () => import('../views/Screener/Index.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/portfolio',
    name: 'Portfolio',
    component: () => import('../views/Portfolio/Index.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: () => import('../views/Backtest/Index.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  if (to.meta.requiresAuth !== false && !token) {
    // 需要登录但未登录，跳转到登录页
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && token) {
    // 已登录但访问登录页，跳转到首页
    next({ path: '/dashboard' })
  } else {
    next()
  }
})

export default router
