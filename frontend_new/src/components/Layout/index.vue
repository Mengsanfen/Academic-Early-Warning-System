<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="layout-aside">
      <Sidebar :is-collapsed="isCollapsed" />
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <Header :is-collapsed="isCollapsed" @toggle="toggleCollapse" />
      </el-header>
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const appStore = useAppStore()
const isCollapsed = computed(() => appStore.isCollapsed)

function toggleCollapse() {
  appStore.toggleCollapse()
}
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
  width: 100%;
}

.layout-aside {
  background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
  transition: width 0.3s ease;
  overflow: hidden;
}

.layout-header {
  height: 60px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  padding: 0 20px;
  z-index: 10;
}

.layout-main {
  background: #f5f7fa;
  padding: 0;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
