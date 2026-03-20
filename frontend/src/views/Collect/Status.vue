<template>
  <div class="collect-status">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold text-lg">采集任务</span>
              <el-button type="primary" size="small" @click="showAddDialog">添加任务</el-button>
            </div>
          </template>

          <el-table :data="tasks" stripe>
            <el-table-column prop="task_id" label="任务ID" width="150" />
            <el-table-column prop="name" label="任务名称" width="200" />
            <el-table-column prop="data_type" label="数据类型" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="启用" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" @change="toggleTask(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="total_collected" label="已采集" width="100" />
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" @click="viewTask(row)">详情</el-button>
                <el-button size="small" type="danger" @click="stopTask(row)">停止</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span class="font-bold">统计信息</span>
          </template>
          <div class="stats">
            <div class="stat-item">
              <span class="label">总任务数:</span>
              <span class="value">{{ stats.total_tasks || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">运行中:</span>
              <span class="value text-green-500">{{ stats.running_tasks || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">已暂停:</span>
              <span class="value text-orange-500">{{ stats.paused_tasks || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">缓存大小:</span>
              <span class="value">{{ stats.cache_size || 0 }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加任务对话框 -->
    <el-dialog v-model="addDialogVisible" title="添加采集任务" width="500px">
      <el-form :model="newTask" label-width="100px">
        <el-form-item label="任务名称">
          <el-input v-model="newTask.name" placeholder="输入任务名称" />
        </el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="newTask.data_type" style="width: 100%">
            <el-option label="股票" value="stock" />
            <el-option label="期货" value="futures" />
            <el-option label="指数" value="index" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据源">
          <el-select v-model="newTask.data_source" style="width: 100%">
            <el-option label="pytdx" value="pytdx" />
            <el-option label="modtdx" value="modtdx" />
          </el-select>
        </el-form-item>
        <el-form-item label="采集标的">
          <el-input v-model="newTask.symbols" placeholder="逗号分隔，如 000001,600000" />
        </el-form-item>
        <el-form-item label="采集周期">
          <el-select v-model="newTask.interval" style="width: 100%">
            <el-option label="1分钟" value="1min" />
            <el-option label="5分钟" value="5min" />
            <el-option label="1天" value="1day" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addTask">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { collectApi } from '@/api'
import { ElMessage } from 'element-plus'

const tasks = ref([])
const stats = ref({})
const addDialogVisible = ref(false)
const newTask = ref({
  name: '',
  data_type: 'stock',
  data_source: 'pytdx',
  symbols: '',
  interval: '1min'
})

const getStatusType = (status) => {
  const types = {
    running: 'success',
    success: 'info',
    failed: 'danger',
    pending: 'warning',
    stopped: 'info',
    paused: 'warning'
  }
  return types[status] || 'info'
}

const loadTasks = async () => {
  try {
    const data = await collectApi.getStatus()
    tasks.value = data
  } catch (error) {
    console.error('Load tasks failed:', error)
  }
}

const loadStats = async () => {
  try {
    const data = await collectApi.getStats()
    stats.value = {
      ...data.scheduler,
      cache_size: data.database?.total_inserted || 0
    }
  } catch (error) {
    console.error('Load stats failed:', error)
  }
}

const showAddDialog = () => {
  addDialogVisible.value = true
}

const addTask = async () => {
  try {
    await collectApi.start({
      ...newTask.value,
      symbols: newTask.value.symbols.split(',').map(s => s.trim())
    })
    ElMessage.success('任务已添加')
    addDialogVisible.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error('添加任务失败')
  }
}

const toggleTask = async (task) => {
  try {
    if (task.enabled) {
      await collectApi.resume(task.task_id)
    } else {
      await collectApi.stop(task.task_id)
    }
    ElMessage.success('操作成功')
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const viewTask = (task) => {
  ElMessage.info(`任务详情: ${task.task_id}`)
}

const stopTask = async (task) => {
  try {
    await collectApi.stop(task.task_id)
    ElMessage.success('任务已停止')
    loadTasks()
  } catch (error) {
    ElMessage.error('停止任务失败')
  }
}

onMounted(() => {
  loadTasks()
  loadStats()
  const interval = setInterval(() => {
    loadTasks()
    loadStats()
  }, 5000)
  return () => clearInterval(interval)
})
</script>

<style scoped>
.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-item .label {
  color: #666;
}

.stat-item .value {
  font-weight: bold;
}

.text-green-500 { color: #67c23a; }
.text-orange-500 { color: #e6a23c; }
</style>
