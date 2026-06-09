<template>
  <div ref="chartRef" class="bar-chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  xKey: {
    type: String,
    default: 'name'
  },
  series: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '400px'
  },
  showLegend: {
    type: Boolean,
    default: true
  },
  showTooltip: {
    type: Boolean,
    default: true
  },
  showGrid: {
    type: Boolean,
    default: true
  },
  horizontal: {
    type: Boolean,
    default: false
  },
  stacked: {
    type: Boolean,
    default: false
  },
  colors: {
    type: Array,
    default: () => ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']
  },
  animation: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['click', 'hover'])

const chartRef = ref(null)
let chartInstance = null

// 解析数据
const parseData = () => {
  if (!props.data || props.data.length === 0) {
    return { xData: [], seriesData: [] }
  }

  const xData = props.data.map(item => item[props.xKey])
  
  const seriesData = props.series.map(seriesConfig => {
    return {
      name: seriesConfig.name,
      type: 'bar',
      data: props.data.map(item => item[seriesConfig.key]),
      barMaxWidth: seriesConfig.barMaxWidth || 50,
      barGap: seriesConfig.barGap || '10%',
      label: seriesConfig.showLabel ? {
        show: true,
        position: props.horizontal ? 'right' : 'top'
      } : undefined,
      emphasis: {
        focus: 'series'
      }
    }
  })

  return { xData, seriesData }
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return
  
  const { xData, seriesData } = parseData()
  
  if (xData.length === 0) {
    chartInstance.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center'
      }
    })
    return
  }

  const option = {
    backgroundColor: '#fff',
    title: props.title ? {
      text: props.title,
      left: 'center'
    } : undefined,
    tooltip: props.showTooltip ? {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    } : undefined,
    legend: props.showLegend ? {
      data: props.series.map(s => s.name),
      bottom: 10
    } : undefined,
    grid: props.showGrid ? {
      left: '3%',
      right: '4%',
      bottom: props.showLegend ? '15%' : '3%',
      containLabel: true
    } : undefined,
    xAxis: props.horizontal ? {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: '#999'
        }
      },
      axisLabel: {
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#eee'
        }
      }
    } : {
      type: 'category',
      data: xData,
      axisLine: {
        lineStyle: {
          color: '#999'
        }
      },
      axisLabel: {
        color: '#666',
        rotate: props.data.length > 10 ? 45 : 0
      }
    },
    yAxis: props.horizontal ? {
      type: 'category',
      data: xData,
      axisLine: {
        lineStyle: {
          color: '#999'
        }
      },
      axisLabel: {
        color: '#666'
      }
    } : {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: '#999'
        }
      },
      axisLabel: {
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#eee'
        }
      }
    },
    series: seriesData,
    color: props.colors,
    animation: props.animation
  }

  chartInstance.setOption(option)
}

// 处理点击事件
const handleClick = (params) => {
  emit('click', params)
}

// 处理悬停事件
const handleShowTip = (params) => {
  emit('hover', params)
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
watch(() => [props.title, props.series, props.showLegend, props.showTooltip, props.horizontal], () => {
  nextTick(() => {
    updateChart()
  })
})

onMounted(() => {
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
    
    if (chartInstance) {
      chartInstance.on('click', handleClick)
      chartInstance.on('mouseover', handleShowTip)
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.off('click', handleClick)
    chartInstance.off('mouseover', handleShowTip)
    chartInstance.dispose()
    chartInstance = null
  }
})

// 暴露方法
defineExpose({
  getChart: () => chartInstance,
  updateData: updateChart,
  resize: handleResize
})
</script>

<style scoped>
.bar-chart {
  width: v-bind(width);
  height: v-bind(height);
}
</style>
