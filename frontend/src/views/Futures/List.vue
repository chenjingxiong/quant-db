<template>
  <div class="futures-list">
    <el-card>
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold text-lg">期货合约</span>
          <div class="flex gap-2">
            <el-select v-model="exchangeFilter" placeholder="选择交易所" style="width: 150px" @change="loadFutures">
              <el-option label="全部" value="" />
              <el-option label="中金所" value="CFFEX" />
              <el-option label="上期所" value="SHFE" />
              <el-option label="大商所" value="DCE" />
              <el-option label="郑商所" value="CZCE" />
            </el-select>
            <el-button @click="refreshQuotes">刷新行情</el-button>
          </div>
        </div>
      </template>

      <el-table :data="futuresList" stripe height="calc(100vh - 300px)">
        <el-table-column prop="symbol" label="合约" width="120" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column label="最新价" width="100">
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
        <el-table-column prop="open_interest" label="持仓量" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { futuresApi } from '@/api'
import { ElMessage } from 'element-plus'

const futuresList = ref([])
const exchangeFilter = ref('')

const getRowClass = (changePercent) => {
  if (!changePercent) return ''
  return changePercent > 0 ? 'text-red-500' : changePercent < 0 ? 'text-green-500' : ''
}

const loadFutures = async () => {
  try {
    const data = await futuresApi.getList(exchangeFilter.value)
    futuresList.value = data.contracts || []
  } catch (error) {
    ElMessage.error('加载期货列表失败')
  }
}

const refreshQuotes = async () => {
  if (futuresList.value.length === 0) return
  try {
    const symbols = futuresList.value.slice(0, 50).map(s => s.symbol).join(',')
    const quotes = await futuresApi.getQuotes(symbols)
    futuresList.value = futuresList.value.map(future => {
      const quote = quotes.find(q => q.symbol === future.symbol)
      return quote ? { ...future, ...quote } : future
    })
    ElMessage.success('行情已刷新')
  } catch (error) {
    ElMessage.error('刷新行情失败')
  }
}

onMounted(() => {
  loadFutures()
  const interval = setInterval(refreshQuotes, 5000)
  return () => clearInterval(interval)
})
</script>

<style scoped>
.text-red-500 { color: #f56c6c; }
.text-green-500 { color: #67c23a; }
</style>
