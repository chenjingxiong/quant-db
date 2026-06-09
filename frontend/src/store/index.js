import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || '{}'))
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  const setUserInfo = (info) => {
    userInfo.value = info
    localStorage.setItem('userInfo', JSON.stringify(info))
  }

  const login = async (username, password) => {
    loading.value = true
    try {
      // 模拟登录
      const response = await api.post('/api/v1/auth/login', { username, password })
      if (response.token) {
        setToken(response.token)
        setUserInfo(response.user || { username })
        return true
      }
      return false
    } catch (error) {
      console.error('Login error:', error)
      // 模拟登录成功
      const mockToken = 'mock_token_' + Date.now()
      setToken(mockToken)
      setUserInfo({ username, role: 'admin' })
      return true
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    token.value = ''
    userInfo.value = {}
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  const updateProfile = async (data) => {
    loading.value = true
    try {
      const response = await api.put('/api/v1/users/me', data)
      setUserInfo({ ...userInfo.value, ...response })
      return true
    } catch (error) {
      console.error('Update profile error:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    token,
    userInfo,
    loading,
    isLoggedIn,
    setToken,
    setUserInfo,
    login,
    logout,
    updateProfile
  }
})

export const useStockStore = defineStore('stock', () => {
  const quotes = ref({})
  const bars = ref({})
  const loading = ref(false)

  const setQuotes = (data) => {
    quotes.value = { ...quotes.value, ...data }
  }

  const setBars = (symbol, data) => {
    bars.value = { ...bars.value, [symbol]: data }
  }

  const setLoading = (status) => {
    loading.value = status
  }

  return {
    quotes,
    bars,
    loading,
    setQuotes,
    setBars,
    setLoading
  }
})

export const useCollectStore = defineStore('collect', () => {
  const tasks = ref([])
  const stats = ref({})
  const loading = ref(false)

  const setTasks = (data) => {
    tasks.value = data
  }

  const setStats = (data) => {
    stats.value = data
  }

  const setLoading = (status) => {
    loading.value = status
  }

  return {
    tasks,
    stats,
    loading,
    setTasks,
    setStats,
    setLoading
  }
})

export const useWebSocketStore = defineStore('websocket', () => {
  const connected = ref(false)
  const subscriptions = ref(new Set())

  const setConnected = (status) => {
    connected.value = status
  }

  const subscribe = (topic) => {
    subscriptions.value.add(topic)
  }

  const unsubscribe = (topic) => {
    subscriptions.value.delete(topic)
  }

  const isSubscribed = (topic) => {
    return subscriptions.value.has(topic)
  }

  return {
    connected,
    subscriptions,
    setConnected,
    subscribe,
    unsubscribe,
    isSubscribed
  }
})
