<template>
  <div class="index-list">
    <el-card>
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold text-lg">股票指数</span>
          <el-button @click="refreshQuotes">刷新行情</el-button>
        </div>
      </template>

      <el-table :data="indexList" stripe>
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column label="最新点" width="120">
          <template #default="{ row }">
            <span :class="getRowClass(row.change_percent)">
              {{ row.close?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="100">
          <template #default="{ row }">
            <span :class="getRowClass(row.change_percent)">
              {{ row.change_percent?.toFixed(2) || '-' }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="volume" label="成交量" width="120" />
        <el-table-column prop="amount" label="成交额" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { indexApi } from '@/api'
import { ElMessage } from 'element-plus'

const indexList = ref([
  { code: '000001', name: '上证指数', market: 'SH' },
  { code: '399001', name: '深证成指', market: 'SZ' },
  { code: '399006', name: '创业板指', market: 'SZ' },
  { code: '000300', name: '沪深300', market: 'SH' },
  { code: '000905', name: '中证500', market: 'SH' },
])

const getRowClass = (changePercent) => {
  if (!changePercent) return ''
  return changePercent > 0 ? 'text-red-500' : changePercent < 0 ? 'text-green-500' : ''
}

const refreshQuotes = async () => {
  try {
    const symbols = indexList.value.map(i => i.code).join(',')
    const data = await indexApi.getQuotes(symbols)
    if (data.quotes) {
      indexList.value = indexList.value.map(idx => {
        const quote = data.quotes.find(q => q.symbol === idx.code)
        return quote ? { ...idx, ...quote } : idx
      })
    }
    ElMessage.success('行情已刷新')
  } catch (error) {
    ElMessage.error('刷新行情失败')
  }
}

onMounted(() => {
  refreshQuotes()
  const interval = setInterval(refreshQuotes, 5000)
  return () => clearInterval(interval)
})
</script>

<style scoped>
.text-red-500 { color: #f56c6c; }
.text-green-500 { color: #67c23a; }
</style>
