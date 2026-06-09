<template>
  <div class="backtest-page">
    <h2>策略回测</h2>

    <!-- 回测配置 -->
    <el-card class="config-card">
      <template #header>回测配置</template>
      <el-form :model="config" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="证券代码">
              <el-input v-model="config.symbol" placeholder="如 000001" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="策略">
              <el-select v-model="config.strategy">
                <el-option label="双均线策略" value="DualMA" />
                <el-option label="RSI策略" value="RSI" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="初始资金">
              <el-input-number v-model="config.initial_capital" :min="10000" :step="100000" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="手续费率">
              <el-input-number v-model="config.commission_rate" :min="0" :max="0.01" :step="0.0001" :precision="4" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="K线数量">
              <el-input-number v-model="config.limit" :min="50" :max="5000" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="K线周期">
              <el-select v-model="config.interval">
                <el-option label="日线" value="1day" />
                <el-option label="周线" value="1week" />
                <el-option label="60分钟" value="60min" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="runBacktest" :loading="loading">开始回测</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 回测结果 -->
    <el-card v-if="result" class="result-card">
      <template #header>回测结果 - {{ result.strategy_name }}</template>
      <el-row :gutter="20" class="metrics-row">
        <el-col :span="4"><el-statistic title="初始资金" :value="result.initial_capital" /></el-col>
        <el-col :span="4"><el-statistic title="最终资金" :value="result.final_capital?.toFixed(2)" /></el-col>
        <el-col :span="4"><el-statistic title="总收益率" :value="(result.total_return * 100).toFixed(2)" suffix="%" /></el-col>
        <el-col :span="4"><el-statistic title="年化收益" :value="(result.annual_return * 100).toFixed(2)" suffix="%" /></el-col>
        <el-col :span="4"><el-statistic title="最大回撤" :value="(result.max_drawdown * 100).toFixed(2)" suffix="%" /></el-col>
        <el-col :span="4"><el-statistic title="夏普比率" :value="result.sharpe_ratio?.toFixed(2)" /></el-col>
      </el-row>
      <el-row :gutter="20" class="metrics-row">
        <el-col :span="4"><el-statistic title="胜率" :value="(result.win_rate * 100).toFixed(1)" suffix="%" /></el-col>
        <el-col :span="4"><el-statistic title="盈亏比" :value="result.profit_loss_ratio?.toFixed(2)" /></el-col>
        <el-col :span="4"><el-statistic title="总交易数" :value="result.total_trades" /></el-col>
        <el-col :span="4"><el-statistic title="盈利次数" :value="result.winning_trades" /></el-col>
        <el-col :span="4"><el-statistic title="亏损次数" :value="result.losing_trades" /></el-col>
      </el-row>

      <!-- 交易记录 -->
      <h3 style="margin-top: 20px">交易记录</h3>
      <el-table :data="result.trades" stripe max-height="400">
        <el-table-column prop="timestamp" label="时间" width="120" />
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="side" label="方向" width="80">
          <template #default="scope">
            <el-tag :type="scope.row.side === 'buy' ? 'success' : 'danger'">
              {{ scope.row.side === 'buy' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="100" />
        <el-table-column prop="quantity" label="数量" width="100" />
        <el-table-column prop="pnl" label="盈亏" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { backtestApi } from '../../api'

const loading = ref(false)
const result = ref(null)

const config = ref({
  symbol: '000001',
  strategy: 'DualMA',
  initial_capital: 1000000,
  commission_rate: 0.0003,
  limit: 500,
  interval: '1day'
})

async function runBacktest() {
  loading.value = true
  try {
    result.value = await backtestApi.run(config.value)
  } catch (e) {
    console.error('回测失败:', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.backtest-page { padding: 20px; }
.config-card, .result-card { margin-bottom: 20px; }
.metrics-row { margin-bottom: 20px; }
</style>
