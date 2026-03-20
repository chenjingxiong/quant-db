<template>
  <div class="sector-list">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold">行业板块</span>
            </div>
          </template>
          <el-table :data="industrySectors" stripe @row-click="showSectorDetail">
            <el-table-column prop="name" label="板块名称" />
            <el-table-column label="涨跌幅" width="100">
              <template #default="{ row }">
                <span :class="getRowClass(row.change_percent)">
                  {{ row.change_percent?.toFixed(2) || '-' }}%
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold">概念板块</span>
            </div>
          </template>
          <el-table :data="conceptSectors" stripe @row-click="showSectorDetail">
            <el-table-column prop="name" label="板块名称" />
            <el-table-column label="涨跌幅" width="100">
              <template #default="{ row }">
                <span :class="getRowClass(row.change_percent)">
                  {{ row.change_percent?.toFixed(2) || '-' }}%
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span class="font-bold">板块详情</span>
          </template>
          <div v-if="selectedSector">
            <h3 class="text-lg font-bold mb-2">{{ selectedSector.name }}</h3>
            <p class="mb-2">涨跌幅: <span :class="getRowClass(selectedSector.change_percent)">{{ selectedSector.change_percent?.toFixed(2) }}%</span></p>
            <p>上涨家数: {{ selectedSector.up_count }}</p>
            <p>下跌家数: {{ selectedSector.down_count }}</p>
          </div>
          <div v-else class="text-gray-500 text-center py-8">
            点击左侧板块查看详情
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { sectorApi } from '@/api'

const industrySectors = ref([
  { name: '银行', code: 'BK0001', change_percent: 0.5, up_count: 20, down_count: 10 },
  { name: '证券', code: 'BK0002', change_percent: -0.3, up_count: 8, down_count: 15 },
  { name: '医药', code: 'BK0005', change_percent: 1.2, up_count: 35, down_count: 12 },
])

const conceptSectors = ref([
  { name: '人工智能', code: 'GN0001', change_percent: 2.5, up_count: 25, down_count: 5 },
  { name: '新能源汽车', code: 'GN0002', change_percent: 1.8, up_count: 30, down_count: 8 },
  { name: '芯片', code: 'GN0003', change_percent: -0.5, up_count: 10, down_count: 20 },
])

const selectedSector = ref(null)

const getRowClass = (changePercent) => {
  if (!changePercent) return ''
  return changePercent > 0 ? 'text-red-500' : changePercent < 0 ? 'text-green-500' : ''
}

const showSectorDetail = (row) => {
  selectedSector.value = row
}
</script>

<style scoped>
.text-red-500 { color: #f56c6c; }
.text-green-500 { color: #67c23a; }
.el-table :deep(.el-table__row) { cursor: pointer; }
</style>
