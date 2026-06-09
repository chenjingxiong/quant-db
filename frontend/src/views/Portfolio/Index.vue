<template>
  <div class="portfolio-page">
    <h2>投资组合管理</h2>

    <!-- 创建组合 -->
    <el-card class="create-card">
      <template #header>创建新组合</template>
      <el-form :inline="true">
        <el-form-item label="名称">
          <el-input v-model="newPortfolio.name" placeholder="组合名称" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="newPortfolio.initial_capital" :min="10000" :step="100000" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="createPortfolio">创建</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 组合列表 -->
    <el-card class="list-card">
      <template #header>我的组合</template>
      <el-table :data="portfolios" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="total_assets" label="总资产" width="120" />
        <el-table-column prop="cash" label="现金" width="120" />
        <el-table-column prop="position_count" label="持仓数" width="80" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row.id)">查看详情</el-button>
            <el-button size="small" type="primary" @click="showBuyDialog(scope.row.id)">买入</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 组合详情 -->
    <el-card v-if="detail" class="detail-card">
      <template #header>组合绩效 - {{ detail.name }}</template>
      <el-row :gutter="20">
        <el-col :span="6"><el-statistic title="总资产" :value="detail.total_assets" /></el-col>
        <el-col :span="6"><el-statistic title="累计收益率" :value="(detail.cumulative_return * 100).toFixed(2)" suffix="%" /></el-col>
        <el-col :span="6"><el-statistic title="日收益率" :value="(detail.daily_return * 100).toFixed(2)" suffix="%" /></el-col>
        <el-col :span="6"><el-statistic title="持仓数" :value="detail.position_count" /></el-col>
      </el-row>
      <el-table :data="detail.positions" stripe style="margin-top: 20px">
        <el-table-column prop="symbol" label="代码" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="quantity" label="数量" />
        <el-table-column prop="cost_price" label="成本价" />
        <el-table-column prop="current_price" label="现价" />
        <el-table-column prop="market_value" label="市值" />
        <el-table-column prop="profit_loss_percent" label="盈亏%" />
      </el-table>
    </el-card>

    <!-- 买入对话框 -->
    <el-dialog v-model="buyDialogVisible" title="买入股票">
      <el-form :model="buyForm" label-width="80px">
        <el-form-item label="股票代码">
          <el-input v-model="buyForm.symbol" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="buyForm.quantity" :min="100" :step="100" />
        </el-form-item>
        <el-form-item label="价格">
          <el-input-number v-model="buyForm.price" :min="0.01" :step="0.1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="buyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="executeBuy">确认买入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { portfolioApi } from '../../api'

const portfolios = ref([])
const detail = ref(null)
const buyDialogVisible = ref(false)
const currentPortfolioId = ref(null)

const newPortfolio = ref({ name: '', initial_capital: 1000000 })
const buyForm = ref({ symbol: '', quantity: 100, price: 10 })

async function loadPortfolios() {
  try {
    portfolios.value = await portfolioApi.getList()
  } catch (e) { portfolios.value = [] }
}

async function createPortfolio() {
  try {
    await portfolioApi.create(newPortfolio.value)
    newPortfolio.value = { name: '', initial_capital: 1000000 }
    await loadPortfolios()
  } catch (e) { console.error('创建失败:', e) }
}

async function viewDetail(id) {
  try {
    detail.value = await portfolioApi.getPerformance(id)
  } catch (e) { console.error('获取详情失败:', e) }
}

function showBuyDialog(id) {
  currentPortfolioId.value = id
  buyForm.value = { symbol: '', quantity: 100, price: 10 }
  buyDialogVisible.value = true
}

async function executeBuy() {
  try {
    await portfolioApi.addPosition(currentPortfolioId.value, buyForm.value)
    buyDialogVisible.value = false
    await loadPortfolios()
    if (detail.value) await viewDetail(detail.value.portfolio_id)
  } catch (e) { console.error('买入失败:', e) }
}

onMounted(() => { loadPortfolios() })
</script>

<style scoped>
.portfolio-page { padding: 20px; }
.create-card, .list-card, .detail-card { margin-bottom: 20px; }
</style>
