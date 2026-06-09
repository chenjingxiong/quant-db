<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <el-container>
      <!-- 头部 -->
      <el-header class="bg-white shadow-sm">
        <div class="flex items-center justify-between h-full">
          <div class="flex items-center">
            <h1 class="text-xl font-bold text-blue-600">量化金融数据采集系统</h1>
          </div>
          <el-menu
            :default-active="activeMenu"
            mode="horizontal"
            router
            class="flex-1 ml-10"
          >
            <el-menu-item index="/dashboard">仪表盘</el-menu-item>
            <el-menu-item index="/stocks">股票</el-menu-item>
            <el-menu-item index="/futures">期货</el-menu-item>
            <el-menu-item index="/indices">指数</el-menu-item>
            <el-menu-item index="/sectors">板块</el-menu-item>
            <el-menu-item index="/collect">采集管理</el-menu-item>
          </el-menu>
        </div>
      </el-header>

      <!-- 主体内容 -->
      <el-main>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>

      <!-- 底部 -->
      <el-footer class="bg-white border-t">
        <div class="text-center text-gray-500 text-sm">
          &copy; 2024 量化金融数据采集系统 | Powered by Vue3 + FastAPI
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.el-header {
  padding: 0 20px;
  height: 60px !important;
  line-height: 60px;
}

.el-main {
  padding: 20px;
}

.el-footer {
  height: 50px !important;
  line-height: 50px;
}
</style>
