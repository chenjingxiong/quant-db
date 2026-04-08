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

// 技术指标API
export const indicatorApi = {
  // 获取支持的指标列表
  getList: () => api.get('/api/v1/indicators/list'),

  // 计算指定证券的技术指标
  calculate: (symbol, interval, indicators, limit) =>
    api.get(`/api/v1/indicators/${symbol}/calculate`, { params: { interval, indicators, limit } }),

  // 批量计算指标
  batchCalculate: (data) => api.post('/api/v1/indicators/batch', data)
}

// 智能选股API
export const screenerApi = {
  // 执行选股
  run: (config) => api.post('/api/v1/screener/run', config),

  // 获取选股策略列表
  getStrategies: () => api.get('/api/v1/screener/strategies'),

  // 创建选股策略
  createStrategy: (data) => api.post('/api/v1/screener/strategies', data),

  // 获取自选股列表
  getWatchlist: () => api.get('/api/v1/screener/watchlist'),

  // 添加自选股
  addToWatchlist: (data) => api.post('/api/v1/screener/watchlist', data),

  // 删除自选股
  removeFromWatchlist: (symbol) => api.delete(`/api/v1/screener/watchlist/${symbol}`)
}

// 组合管理API
export const portfolioApi = {
  // 创建组合
  create: (data) => api.post('/api/v1/portfolios', data),

  // 获取组合列表
  getList: () => api.get('/api/v1/portfolios'),

  // 获取组合详情
  getDetail: (id) => api.get(`/api/v1/portfolios/${id}`),

  // 添加持仓
  addPosition: (id, data) => api.post(`/api/v1/portfolios/${id}/positions`, data),

  // 获取组合绩效
  getPerformance: (id) => api.get(`/api/v1/portfolios/${id}/performance`)
}

// 回测API
export const backtestApi = {
  // 获取可用策略列表
  getStrategies: () => api.get('/api/v1/backtest/strategies'),

  // 运行回测
  run: (data) => api.post('/api/v1/backtest/run', data)
}

export default api
