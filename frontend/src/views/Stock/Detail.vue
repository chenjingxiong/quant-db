<template>
  <div class="stock-detail">
    <el-page-header @back="goBack" :content="`${symbol} - 股票详情`" />

    <el-row :gutter="20" class="mt-4">
      <!-- 股票基本信息 -->
      <el-col :span="24">
        <el-card>
          <div class="stock-header">
            <div>
              <h2 class="text-2xl font-bold">{{ stockInfo.name || symbol }}</h2>
              <p class="text-gray-500">{{ symbol }} | {{ stockInfo.market }}</p>
            </div>
            <div class="text-right">
              <div class="text-3xl font-bold" :class="getRowClass(quote?.change_percent)">
                {{ quote?.close?.toFixed(2) || '-' }}
              </div>
              <div class="text-lg" :class="getRowClass(quote?.change_percent)">
                {{ quote?.change_percent?.toFixed(2) || '-' }}%
              </div>
            </div>
          </div>

          <el-divider />

          <!-- 详细行情 -->
          <el-row :gutter="20">
            <el-col :span="4">
              <div class="detail-item">
                <span class="label">开盘</span>
                <span class="value">{{ quote?.open?.toFixed(2) || '-' }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="detail-item">
                <span class="label">最高</span>
                <span class="value text-red-500">{{ quote?.high?.toFixed(2) || '-' }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="detail-item">
                <span class="label">最低</span>
                <span class="value text-green-500">{{ quote?.low?.toFixed(2) || '-' }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="detail-item">
                <span class="label">成交量</span>
                <span class="value">{{ formatVolume(quote?.volume) }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="detail-item">
                <span class="label">成交额</span>
                <span class="value">{{ formatAmount(quote?.amount) }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="detail-item">
                <span class="label">换手率</span>
                <span class="value">{{ quote?.turnover?.toFixed(2) || '-' }}%</span>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- K线图表 -->
    <el-row :gutter="20" class="mt-4">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold">K线图</span>
              <el-radio-group v-model="interval" @change="loadBars">
                <el-radio-button label="1min">1分</el-radio-button>
                <el-radio-button label="5min">5分</el-radio-button>
                <el-radio-button label="15min">15分</el-radio-button>
                <el-radio-button label="1day">日K</el-radio-button>
                <el-radio-button label="1week">周K</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div id="kline-chart" style="height: 400px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stockApi } from '@/api'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const symbol = computed(() => route.params.symbol)
const quote = ref(null)
const stockInfo = ref({})
const interval = ref('1day')
const bars = ref([])
let chart = null

const getRowClass = (changePercent) => {
  if (!changePercent) return ''
  return changePercent > 0 ? 'text-red-500' : changePercent < 0 ? 'text-green-500' : ''
}

const formatVolume = (volume) => {
  if (!volume) return '-'
  return volume > 100000000 ? (volume / 100000000).toFixed(2) + '亿' :
         volume > 10000 ? (volume / 10000).toFixed(2) + '万' : volume
}

const formatAmount = (amount) => {
  if (!amount) return '-'
  return amount > 100000000 ? (amount / 100000000).toFixed(2) + '亿' :
         amount > 10000 ? (amount / 10000).toFixed(2) + '万' : amount.toFixed(2)
}

const loadQuote = async () => {
  try {
    const data = await stockApi.getQuotes(symbol.value)
    quote.value = data[0] || null
  } catch (error) {
    console.error('Load quote failed:', error)
  }
}

const loadBars = async () => {
  try {
    const data = await stockApi.getBars(symbol.value, interval.value, null, null, 200)
    bars.value = data || []
    renderChart()
  } catch (error) {
    ElMessage.error('加载K线数据失败')
  }
}

const renderChart = () => {
  if (!chart) {
    chart = echarts.init(document.getElementById('kline-chart'))
  }

  const dates = bars.value.map(b => b.ts)
  const values = bars.value.map(b => [b.open, b.close, b.low, b.high])
  const volumes = bars.value.map(b => b.volume)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    grid: [
      { left: '10%', right: '10%', top: '10%', height: '50%' },
      { left: '10%', right: '10%', top: '65%', height: '15%' }
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: 'category', data: dates, gridIndex: 1 }
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { show: false } },
      { scale: true, gridIndex: 1, splitLine: { show: false } }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      { show: true, xAxisIndex: [0, 1], type: 'slider', top: '90%', start: 50, end: 100 }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: values,
        itemStyle: {
          color: '#ef232a',
          color0: '#14b143',
          borderColor: '#ef232a',
          borderColor0: '#14b143'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: {
          color: '#7fbe9e'
        }
      }
    ]
  }

  chart.setOption(option, true)
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  loadQuote()
  loadBars()

  // 定时刷新
  const intervalId = setInterval(loadQuote, 3000)

  window.addEventListener('resize', () => chart?.resize())

  return () => {
    clearInterval(intervalId)
    chart?.dispose()
  }
})
</script>

<style scoped>
.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
}

.detail-item .label {
  color: #999;
}

.detail-item .value {
  font-weight: bold;
}

.text-red-500 {
  color: #f56c6c;
}

.text-green-500 {
  color: #67c23a;
}
</style>
