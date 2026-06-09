<template>
  <div class="stock-list">
    <el-card>
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold text-lg">股票列表</span>
          <div class="flex gap-2">
            <el-select v-model="marketFilter" placeholder="选择市场" style="width: 120px">
              <el-option label="全部" value="" />
              <el-option label="上海" value="SH" />
              <el-option label="深圳" value="SZ" />
            </el-select>
            <el-input
              v-model="searchText"
              placeholder="搜索股票代码"
              style="width: 200px"
            />
            <el-button type="primary" @click="searchStocks">搜索</el-button>
            <el-button @click="refreshQuotes">刷新行情</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="stockList"
        stripe
        height="calc(100vh - 300px)"
        @row-click="goToDetail"
      >
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="market" label="市场" width="80" />
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
        <el-table-column prop="volume" label="成交量" width="120">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="成交额" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="open" label="开盘" width="100">
          <template #default="{ row }">
            {{ row.open?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="high" label="最高" width="100">
          <template #default="{ row }">
            {{ row.high?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="low" label="最低" width="100">
          <template #default="{ row }">
            {{ row.low?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-center mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockApi } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const stockList = ref([])
const marketFilter = ref('')
const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

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

const loadStocks = async () => {
  try {
    const data = await stockApi.getList(marketFilter.value, pageSize.value)
    stockList.value = data.symbols || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error('加载股票列表失败')
  }
}

const refreshQuotes = async () => {
  if (stockList.value.length === 0) return
  try {
    const symbols = stockList.value.slice(0, 50).map(s => s.symbol).join(',')
    const quotes = await stockApi.getQuotes(symbols)
    // 更新行情数据
    stockList.value = stockList.value.map(stock => {
      const quote = quotes.find(q => q.symbol === stock.symbol)
      return quote ? { ...stock, ...quote } : stock
    })
    ElMessage.success('行情已刷新')
  } catch (error) {
    ElMessage.error('刷新行情失败')
  }
}

const searchStocks = () => {
  if (searchText.value) {
    const filtered = stockList.value.filter(s =>
      s.symbol.includes(searchText.value) || s.name.includes(searchText.value)
    )
    stockList.value = filtered
  } else {
    loadStocks()
  }
}

const goToDetail = (row) => {
  router.push(`/stocks/${row.symbol}`)
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadStocks()
}

onMounted(() => {
  loadStocks()
  // 定时刷新行情
  const interval = setInterval(refreshQuotes, 5000)
  return () => clearInterval(interval)
})
</script>

<style scoped>
.text-red-500 {
  color: #f56c6c;
}

.text-green-500 {
  color: #67c23a;
}

.el-table :deep(.el-table__row) {
  cursor: pointer;
}

.el-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
