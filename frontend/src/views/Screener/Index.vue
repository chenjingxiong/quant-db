<template>
  <div class="screener-page">
    <h2>智能选股</h2>

    <!-- 选股条件配置 -->
    <el-card class="config-card">
      <template #header>筛选条件</template>
      <el-form :model="config" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="市盈率">
              <el-input-number v-model="config.peMax" :min="0" :max="500" placeholder="最大PE" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="市净率">
              <el-input-number v-model="config.pbMax" :min="0" :max="50" placeholder="最大PB" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="ROE(%)">
              <el-input-number v-model="config.roeMin" :min="-50" :max="100" placeholder="最小ROE" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="涨跌幅(%)">
              <el-input-number v-model="config.changeMin" :min="-20" :max="20" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="排序字段">
              <el-select v-model="config.sortBy">
                <el-option label="涨跌幅" value="change_percent" />
                <el-option label="市盈率" value="pe" />
                <el-option label="ROE" value="roe" />
                <el-option label="换手率" value="turnover_rate" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="返回数量">
              <el-input-number v-model="config.limit" :min="10" :max="500" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="runScreener" :loading="loading">执行选股</el-button>
          <el-button @click="resetConfig">重置条件</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 选股结果 -->
    <el-card v-if="results.length" class="result-card">
      <template #header>选股结果 ({{ results.length }} 只)</template>
      <el-table :data="results" stripe>
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="price" label="价格" width="80" />
        <el-table-column prop="change_percent" label="涨跌幅%" width="100" />
        <el-table-column prop="pe" label="PE" width="80" />
        <el-table-column prop="pb" label="PB" width="80" />
        <el-table-column prop="roe" label="ROE%" width="80" />
        <el-table-column prop="turnover_rate" label="换手率%" width="100" />
        <el-table-column prop="volume_ratio" label="量比" width="80" />
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button size="small" type="primary" @click="addToWatchlist(scope.row)">
              加自选
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 自选股列表 -->
    <el-card class="watchlist-card">
      <template #header>自选股</template>
      <el-table :data="watchlist" stripe>
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="notes" label="备注" />
        <el-table-column prop="added_at" label="添加时间" width="180" />
        <el-table-column label="操作" width="80">
          <template #default="scope">
            <el-button size="small" type="danger" @click="removeFromWatchlist(scope.row.symbol)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { screenerApi } from '../../api'

const loading = ref(false)
const results = ref([])
const watchlist = ref([])

const config = ref({
  peMax: 30,
  pbMax: 5,
  roeMin: 15,
  changeMin: -20,
  sortBy: 'roe',
  limit: 50
})

async function runScreener() {
  loading.value = true
  try {
    const res = await screenerApi.run({
      basic: {
        pe: { operator: '<=', value: config.value.peMax },
        pb: { operator: '<=', value: config.value.pbMax },
        change_percent: { operator: '>=', value: config.value.changeMin }
      },
      financial: {
        roe: { operator: '>=', value: config.value.roeMin }
      },
      logic: 'and',
      sort_by: config.value.sortBy,
      sort_order: 'desc',
      limit: config.value.limit
    })
    results.value = res.stocks || []
  } catch (e) {
    console.error('选股失败:', e)
  } finally {
    loading.value = false
  }
}

function resetConfig() {
  config.value = { peMax: 30, pbMax: 5, roeMin: 15, changeMin: -20, sortBy: 'roe', limit: 50 }
}

async function loadWatchlist() {
  try {
    const res = await screenerApi.getWatchlist()
    watchlist.value = res || []
  } catch (e) {
    watchlist.value = []
  }
}

async function addToWatchlist(stock) {
  try {
    await screenerApi.addToWatchlist({ symbol: stock.symbol, name: stock.name })
    await loadWatchlist()
  } catch (e) {
    console.error('添加自选失败:', e)
  }
}

async function removeFromWatchlist(symbol) {
  try {
    await screenerApi.removeFromWatchlist(symbol)
    await loadWatchlist()
  } catch (e) {
    console.error('删除自选失败:', e)
  }
}

onMounted(() => {
  loadWatchlist()
})
</script>

<style scoped>
.screener-page { padding: 20px; }
.config-card, .result-card, .watchlist-card { margin-bottom: 20px; }
</style>
