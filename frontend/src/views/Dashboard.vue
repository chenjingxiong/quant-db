<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon bg-blue-500">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">总数据采集</div>
              <div class="stat-value">{{ stats.total_collected || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon bg-green-500">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">运行任务</div>
              <div class="stat-value">{{ stats.running_tasks || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon bg-orange-500">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">等待任务</div>
              <div class="stat-value">{{ stats.pending_tasks || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon bg-purple-500">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">WebSocket连接</div>
              <div class="stat-value">{{ stats.ws_connections || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-row :gutter="20" class="mt-4">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold">采集任务</span>
              <el-button size="small" @click="refreshTasks">刷新</el-button>
            </div>
          </template>
          <el-table :data="tasks" stripe>
            <el-table-column prop="name" label="任务名称" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_collected" label="采集数量" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="font-bold">市场概览</span>
          </template>
          <div class="market-overview">
            <div class="market-item">
              <span class="label">上证指数:</span>
              <span class="value text-red-500">3,056.25 +0.35%</span>
            </div>
            <div class="market-item">
              <span class="label">深证成指:</span>
              <span class="value text-green-500">9,856.32 -0.25%</span>
            </div>
            <div class="market-item">
              <span class="label">创业板指:</span>
              <span class="value text-red-500">1,923.45 +0.55%</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { collectApi } from '@/api'
import { useCollectStore } from '@/store'

const collectStore = useCollectStore()
const tasks = ref([])
const stats = ref({})

const getStatusType = (status) => {
  const types = {
    running: 'success',
    success: 'info',
    failed: 'danger',
    pending: 'warning',
    stopped: 'info',
    paused: 'info'
  }
  return types[status] || 'info'
}

const loadData = async () => {
  try {
    const [statusData, statsData] = await Promise.all([
      collectApi.getStatus(),
      collectApi.getStats()
    ])
    tasks.value = statusData
    stats.value = {
      ...statsData.scheduler,
      ws_connections: 0 // TODO: 从WebSocket store获取
    }
  } catch (error) {
    console.error('Load dashboard data failed:', error)
  }
}

const refreshTasks = () => {
  loadData()
}

onMounted(() => {
  loadData()
  // 定时刷新
  const interval = setInterval(loadData, 5000)
  return () => clearInterval(interval)
})
</script>

<style scoped>
.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  margin-right: 15px;
}

.stat-info {
  flex: 1;
}

.stat-label {
  color: #999;
  font-size: 14px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.market-overview {
  padding: 10px 0;
}

.market-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.market-item:last-child {
  border-bottom: none;
}

.market-item .label {
  color: #666;
}

.market-item .value {
  font-weight: bold;
}

.text-red-500 {
  color: #f56c6c;
}

.text-green-500 {
  color: #67c23a;
}
</style>
