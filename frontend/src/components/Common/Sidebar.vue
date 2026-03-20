<template>
  <aside class="app-sidebar" :class="{ 'sidebar-collapse': collapse }">
    <!-- 菜单 -->
    <el-scrollbar class="sidebar-scroll">
      <el-menu
        :default-active="activeMenu"
        :collapse="collapse"
        :collapse-transition="false"
        :router="true"
        :unique-opened="true"
      >
        <!-- 首页 -->
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>

        <!-- 数据菜单组 -->
        <el-sub-menu index="data">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>数据概览</span>
          </template>
          <el-menu-item index="/stocks">
            <el-icon><TrendCharts /></el-icon>
            <template #title>股票数据</template>
          </el-menu-item>
          <el-menu-item index="/futures">
            <el-icon><Coin /></el-icon>
            <template #title>期货数据</template>
          </el-menu-item>
          <el-menu-item index="/indices">
            <el-icon><DataLine /></el-icon>
            <template #title>指数数据</template>
          </el-menu-item>
          <el-menu-item index="/sectors">
            <el-icon><Grid /></el-icon>
            <template #title>板块数据</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- 采集管理 -->
        <el-sub-menu index="collect">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>采集管理</span>
          </template>
          <el-menu-item index="/collect">
            <el-icon><Monitor /></el-icon>
            <template #title>采集状态</template>
          </el-menu-item>
          <el-menu-item index="/collect/config">
            <el-icon><Operation /></el-icon>
            <template #title>采集配置</template>
          </el-menu-item>
          <el-menu-item index="/collect/logs">
            <el-icon><Document /></el-icon>
            <template #title>采集日志</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- 用户菜单 -->
        <el-sub-menu v-if="showUserMenu" index="user">
          <template #title>
            <el-icon><User /></el-icon>
            <span>用户中心</span>
          </template>
          <el-menu-item index="/profile">
            <el-icon><UserFilled /></el-icon>
            <template #title>个人资料</template>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <template #title>系统设置</template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-scrollbar>

    <!-- 折叠按钮 -->
    <div class="sidebar-footer" @click="handleToggleCollapse">
      <el-icon>
        <ArrowLeft v-if="!collapse" />
        <ArrowRight v-else />
      </el-icon>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  House,
  DataAnalysis,
  TrendCharts,
  Coin,
  DataLine,
  Grid,
  Setting,
  Monitor,
  Operation,
  Document,
  User,
  UserFilled,
  ArrowLeft,
  ArrowRight
} from '@element-plus/icons-vue'

const props = defineProps({
  // 是否折叠
  collapse: {
    type: Boolean,
    default: false
  },
  // 是否显示用户菜单
  showUserMenu: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['collapse-change'])

const route = useRoute()
const activeMenu = computed(() => route.path)

// 切换折叠状态
const handleToggleCollapse = () => {
  emit('collapse-change', !props.collapse)
}
</script>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: 220px;
  height: 100%;
  background-color: #304156;
  transition: width 0.3s;
}

.sidebar-collapse {
  width: 64px;
}

.sidebar-scroll {
  flex: 1;
  height: calc(100% - 50px);
}

.sidebar-scroll :deep(.el-menu) {
  border-right: none;
  background-color: #304156;
}

.sidebar-scroll :deep(.el-menu-item),
.sidebar-scroll :deep(.el-sub-menu__title) {
  color: #bfcbd9;
}

.sidebar-scroll :deep(.el-menu-item:hover),
.sidebar-scroll :deep(.el-sub-menu__title:hover) {
  background-color: #263445;
}

.sidebar-scroll :deep(.el-menu-item.is-active) {
  background-color: #409eff !important;
  color: #fff !important;
}

.sidebar-scroll :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #409eff !important;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 50px;
  background-color: #263445;
  color: #bfcbd9;
  cursor: pointer;
  transition: background-color 0.3s;
}

.sidebar-footer:hover {
  background-color: #3a4a5c;
}

.sidebar-footer .el-icon {
  font-size: 20px;
}

/* 折叠状态样式 */
.sidebar-collapse .sidebar-scroll :deep(.el-menu--collapse) {
  width: 64px;
}

.sidebar-collapse .sidebar-scroll :deep(.el-menu--collapse .el-sub-menu) {
  width: 64px;
}
</style>
