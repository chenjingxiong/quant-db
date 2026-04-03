import { ref, onUnmounted } from 'vue'
import { useWebSocketStore } from '@/store'

const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws`

export function useWebSocket() {
  const ws = ref(null)
  const connected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000
  let reconnectTimer = null

  const store = useWebSocketStore()

  const connect = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts.value = 0
      store.setConnected(true)
    }

    ws.value.onclose = () => {
      connected.value = false
      store.setConnected(false)
      attemptReconnect()
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }
  }

  const attemptReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts) return
    clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, reconnectDelay)
  }

  const handleMessage = (data) => {
    switch (data.type) {
      case 'quote':
        // Dispatch to stock/futures/index stores
        window.dispatchEvent(new CustomEvent('ws:quote', { detail: data.data }))
        break
      case 'trade':
        window.dispatchEvent(new CustomEvent('ws:trade', { detail: data.data }))
        break
      case 'depth':
        window.dispatchEvent(new CustomEvent('ws:depth', { detail: data.data }))
        break
      case 'subscribed':
        if (data.topic) {
          store.subscribe(data.topic)
        }
        break
      case 'unsubscribed':
        if (data.topic) {
          store.unsubscribe(data.topic)
        }
        break
    }
  }

  const subscribe = (topic) => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
    ws.value.send(JSON.stringify({
      action: 'subscribe',
      topic: topic
    }))
    store.subscribe(topic)
  }

  const unsubscribe = (topic) => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
    ws.value.send(JSON.stringify({
      action: 'unsubscribe',
      topic: topic
    }))
    store.unsubscribe(topic)
  }

  const disconnect = () => {
    clearTimeout(reconnectTimer)
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
    store.setConnected(false)
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    connected,
    reconnectAttempts,
    connect,
    disconnect,
    subscribe,
    unsubscribe
  }
}
