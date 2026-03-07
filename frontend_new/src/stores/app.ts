import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 侧边栏折叠状态
  const isCollapsed = ref(false)
  
  // 切换折叠
  function toggleCollapse() {
    isCollapsed.value = !isCollapsed.value
  }
  
  return {
    isCollapsed,
    toggleCollapse
  }
})
