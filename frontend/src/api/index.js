import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://192.168.6.8:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API接口
export const stockApi = {
  // 获取股票行情
  getQuotes: (symbols) => api.get('/api/v1/stocks/quotes', { params: { symbols } }),

  // 获取股票K线
  getBars: (symbol, interval, startTime, endTime, limit) =>
    api.get('/api/v1/stocks/bars', { params: { symbol, interval, start_time: startTime, end_time: endTime, limit } }),

  // 获取股票列表
  getList: (market, limit) =>
    api.get('/api/v1/stocks/list', { params: { market, limit } })
}

export const futuresApi = {
  // 获取期货行情
  getQuotes: (symbols) => api.get('/api/v1/futures/quotes', { params: { symbols } }),

  // 获取期货K线
  getBars: (symbol, interval, startTime, endTime, limit) =>
    api.get('/api/v1/futures/bars', { params: { symbol, interval, start_time: startTime, end_time: endTime, limit } }),

  // 获取期货列表
  getList: (exchange) => api.get('/api/v1/futures/list', { params: { exchange } }),

  // 获取交易所列表
  getExchanges: () => api.get('/api/v1/futures/exchanges')
}

export const indexApi = {
  // 获取指数行情
  getQuotes: (symbols) => api.get('/api/v1/indices/quotes', { params: { symbols } }),

  // 获取指数K线
  getBars: (symbol, interval, startTime, endTime, limit) =>
    api.get('/api/v1/indices/bars', { params: { symbol, interval, start_time: startTime, end_time: endTime, limit } }),

  // 获取指数列表
  getList: () => api.get('/api/v1/indices/list')
}

export const sectorApi = {
  // 获取板块列表
  getList: (sectorType) => api.get('/api/v1/sectors/list', { params: { sector_type: sectorType } }),

  // 获取板块行情
  getQuotes: (sectorName) => api.get(`/api/v1/sectors/${sectorName}/quotes`),

  // 获取板块成分股
  getStocks: (sectorName) => api.get(`/api/v1/sectors/${sectorName}/stocks`)
}

export const collectApi = {
  // 获取采集状态
  getStatus: () => api.get('/api/v1/collect/status'),

  // 启动采集
  start: (config) => api.post('/api/v1/collect/start', config),

  // 停止采集
  stop: (taskId) => api.post(`/api/v1/collect/stop/${taskId}`),

  // 恢复采集
  resume: (taskId) => api.post(`/api/v1/collect/resume/${taskId}`),

  // 获取采集配置
  getConfig: () => api.get('/api/v1/collect/config'),

  // 获取采集日志
  getLogs: (limit, level) => api.get('/api/v1/collect/logs', { params: { limit, level } }),

  // 获取采集统计
  getStats: () => api.get('/api/v1/collect/stats')
}

export default api
