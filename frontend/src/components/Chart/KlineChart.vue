<template>
  <div ref="chartRef" class="kline-chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  symbol: {
    type: String,
    default: ''
  },
  interval: {
    type: String,
    default: '1day'
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '500px'
  },
  showVolume: {
    type: Boolean,
    default: true
  },
  showMa: {
    type: Boolean,
    default: true
  },
  showMacd: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'crosshair'])

const chartRef = ref(null)
let chartInstance = null

// 解析K线数据
const parseData = () => {
  if (!props.data || props.data.length === 0) {
    return { dates: [], values: [], volumes: [] }
  }

  const dates = []
  const values = []
  const volumes = []

  props.data.forEach(item => {
    const ts = item.ts || item.time
    if (ts) {
      const date = new Date(ts)
      dates.push(date.toLocaleDateString())
    } else {
      dates.push('')
    }
    
    values.push([
      item.open,
      item.close,
      item.low,
      item.high
    ])
    
    volumes.push(item.volume || 0)
  })

  return { dates, values, volumes }
}

// 计算MA均线
const calculateMA = (data, dayCount) => {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < dayCount) {
      result.push('-')
      continue
    }
    
    let sum = 0
    for (let j = 0; j < dayCount; j++) {
      sum += data[i - j][1] // 收盘价
    }
    result.push((sum / dayCount).toFixed(2))
  }
  return result
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  
  updateChart()
}

// 更新图表数据
const updateChart = () => {
  if (!chartInstance) return
  
  const { dates, values, volumes } = parseData()
  
  if (values.length === 0) {
    chartInstance.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center'
      }
    })
    return
  }

  const series = []
  const xAxisData = dates
  
  // K线数据
  series.push({
    name: 'K线',
    type: 'candlestick',
    data: values,
    itemStyle: {
      color: '#ef232a',      // 上涨颜色
      color0: '#14b143',     // 下跌颜色
      borderColor: '#ef232a',
      borderColor0: '#14b143'
    }
  })

  // 均线数据
  if (props.showMa) {
    const ma5 = calculateMA(values, 5)
    const ma10 = calculateMA(values, 10)
    const ma20 = calculateMA(values, 20)
    
    series.push({
      name: 'MA5',
      type: 'line',
      data: ma5,
      smooth: true,
      showSymbol: false,
      lineStyle: { opacity: 0.8, width: 1 }
    })
    
    series.push({
      name: 'MA10',
      type: 'line',
      data: ma10,
      smooth: true,
      showSymbol: false,
      lineStyle: { opacity: 0.8, width: 1 }
    })
    
    series.push({
      name: 'MA20',
      type: 'line',
      data: ma20,
      smooth: true,
      showSymbol: false,
      lineStyle: { opacity: 0.8, width: 1 }
    })
  }

  // 成交量
  if (props.showVolume) {
    series.push({
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumes.map((vol, idx) => {
        return {
          value: vol,
          itemStyle: {
            color: values[idx][1] >= values[idx][0] ? '#ef232a' : '#14b143'
          }
        }
      })
    })
  }

  const option = {
    backgroundColor: '#fff',
    animation: true,
    legend: {
      bottom: 10,
      left: 'center',
      data: props.showMa ? ['K线', 'MA5', 'MA10', 'MA20', '成交量'] : ['K线', '成交量']
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999'
        }
      },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        
        const klineData = params.find(p => p.seriesName === 'K线')
        if (!klineData) return ''
        
        const data = klineData.data
        const result = `<div style="font-weight:bold">${klineData.axisValue}</div>`
        result += `<div>开盘: ${data[1]}</div>`
        result += `<div>收盘: ${data[2]}</div>`
        result += `<div>最低: ${data[3]}</div>`
        result += `<div>最高: ${data[4]}</div>`
        
        return result
      }
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
      label: {
        backgroundColor: '#777'
      }
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        height: props.showVolume ? '50%' : '70%'
      },
      {
        left: '10%',
        right: '10%',
        top: '65%',
        height: props.showVolume ? '15%' : '0%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: xAxisData,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 1,
        data: xAxisData,
        boundaryGap: false,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: { show: true }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 50,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        bottom: props.showVolume ? 60 : 10,
        start: 50,
        end: 100
      }
    ],
    series: series
  }

  chartInstance.setOption(option)
}

// 响应窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// 监听数据变化
watch(() => props.data, () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

// 监听参数变化
watch(() => [props.symbol, props.interval, props.showMa, props.showVolume], () => {
  nextTick(() => {
    updateChart()
  })
})

onMounted(() => {
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

// 暴露方法
defineExpose({
  getChart: () => chartInstance,
  updateData: updateChart
})
</script>

<style scoped>
.kline-chart {
  width: v-bind(width);
  height: v-bind(height);
}
</style>
