<template>
  <header class="app-header" :class="{ 'header-fixed': fixed }">
    <div class="header-left">
      <!-- Logo -->
      <div class="logo" @click="handleLogoClick">
        <img v-if="logo" :src="logo" alt="logo" class="logo-img" />
        <span v-else class="logo-text">{{ title }}</span>
      </div>
      
      <!-- 标题 -->
      <h1 v-if="showTitle" class="header-title">{{ title }}</h1>
    </div>
    
    <div class="header-center">
      <!-- 搜索框 -->
      <div v-if="showSearch" class="header-search">
        <el-input
          v-model="searchText"
          placeholder="搜索股票代码/名称"
          :prefix-icon="Search"
          @keyup.enter="handleSearch"
        />
      </div>
    </div>
    
    <div class="header-right">
      <!-- 快捷操作 -->
      <div class="header-actions">
        <!-- 刷新按钮 -->
        <el-tooltip content="刷新数据" placement="bottom">
          <el-button :icon="Refresh" circle @click="handleRefresh" />
        </el-tooltip>
        
        <!-- 全屏按钮 -->
        <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏'" placement="bottom">
          <el-button :icon="isFullscreen ? Close : FullScreen" circle @click="toggleFullscreen" />
        </el-tooltip>
        
        <!-- 通知 -->
        <el-badge :value="notificationCount" :hidden="notificationCount === 0">
          <el-button :icon="Bell" circle @click="handleNotification" />
        </el-badge>
      </div>
      
      <!-- 用户信息 -->
      <div v-if="showUser" class="header-user">
        <el-dropdown @command="handleUserCommand">
          <div class="user-info">
            <el-avatar :size="32" :src="userAvatar">
              {{ userName?.charAt(0) || 'U' }}
            </el-avatar>
            <span class="user-name">{{ userName || '用户' }}</span>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人中心
              </el-dropdown-item>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon>
                系统设置
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, 
  Refresh, 
  FullScreen, 
  Close, 
  Bell, 
  ArrowDown,
  User,
  Setting,
  SwitchButton 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  // 标题
  title: {
    type: String,
    default: '量化金融数据采集系统'
  },
  // Logo图片
  logo: {
    type: String,
    default: ''
  },
  // 是否显示标题
  showTitle: {
    type: Boolean,
    default: true
  },
  // 是否固定头部
  fixed: {
    type: Boolean,
    default: false
  },
  // 是否显示搜索框
  showSearch: {
    type: Boolean,
    default: true
  },
  // 是否显示用户信息
  showUser: {
    type: Boolean,
    default: true
  },
  // 用户名
  userName: {
    type: String,
    default: ''
  },
  // 用户头像
  userAvatar: {
    type: String,
    default: ''
  },
  // 通知数量
  notificationCount: {
    type: [Number, String],
    default: 0
  }
})

const emit = defineEmits([
  'search', 
  'refresh', 
  'notification',
  'command',
  'logo-click'
])

const router = useRouter()
const searchText = ref('')
const isFullscreen = ref(false)

// 处理搜索
const handleSearch = () => {
  if (searchText.value.trim()) {
    emit('search', searchText.value.trim())
    // 跳转到搜索结果页
    router.push({
      path: '/stocks',
      query: { search: searchText.value.trim() }
    })
  }
}

// 处理刷新
const handleRefresh = () => {
  emit('refresh')
  ElMessage.success('数据已刷新')
}

// 处理通知点击
const handleNotification = () => {
  emit('notification')
}

// 处理用户菜单命令
const handleUserCommand = (command) => {
  emit('command', command)
  
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      handleLogout()
      break
  }
}

// 处理Logo点击
const handleLogoClick = () => {
  emit('logo-click')
  router.push('/dashboard')
}

// 退出登录
const handleLogout = () => {
  // 清除登录信息
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  ElMessage.success('已退出登录')
  router.push('/login')
}

// 切换全屏
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
      isFullscreen.value = false
    }
  }
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 20px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.header-fixed {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.logo-img {
  height: 36px;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 40px;
}

.header-search {
  width: 400px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-user {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-name {
  font-size: 14px;
  color: #606266;
}
</style>
