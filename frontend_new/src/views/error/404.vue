<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-code">404</div>
      <div class="error-desc">
        <h2>页面未找到</h2>
        <p>抱歉，您访问的页面不存在或已被移除</p>
      </div>
      <div class="error-actions">
        <el-button type="primary" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
        <el-button @click="goBack">
          <el-icon><Back /></el-icon>
          返回上页
        </el-button>
      </div>
    </div>
    <div class="error-illustration">
      <svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
        <!-- Background shapes -->
        <circle cx="200" cy="150" r="120" fill="#f5f7fa" />
        <circle cx="200" cy="150" r="80" fill="#e4e7ed" />

        <!-- 404 Text -->
        <text x="200" y="170" text-anchor="middle" font-size="72" font-weight="bold" fill="#409eff">
          404
        </text>

        <!-- Decorative elements -->
        <circle cx="80" cy="60" r="15" fill="#67c23a" opacity="0.6" />
        <circle cx="320" cy="80" r="10" fill="#e6a23c" opacity="0.6" />
        <circle cx="340" cy="200" r="20" fill="#f56c6c" opacity="0.4" />
        <rect x="60" y="220" width="30" height="30" rx="5" fill="#909399" opacity="0.3" transform="rotate(15 75 235)" />

        <!-- Question marks -->
        <text x="100" y="100" font-size="24" fill="#c0c4cc" opacity="0.5">?</text>
        <text x="300" y="120" font-size="20" fill="#c0c4cc" opacity="0.5">?</text>
        <text x="280" y="250" font-size="28" fill="#c0c4cc" opacity="0.5">?</text>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { HomeFilled, Back } from '@element-plus/icons-vue'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped lang="scss">
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  padding: 20px;

  .error-content {
    text-align: center;
    z-index: 1;
    margin-right: 60px;

    .error-code {
      font-size: 120px;
      font-weight: 700;
      line-height: 1;
      background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 20px;
    }

    .error-desc {
      margin-bottom: 40px;

      h2 {
        margin: 0 0 12px 0;
        font-size: 28px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      p {
        margin: 0;
        font-size: 16px;
        color: var(--el-text-color-secondary);
      }
    }

    .error-actions {
      display: flex;
      gap: 16px;
      justify-content: center;
    }
  }

  .error-illustration {
    svg {
      width: 400px;
      height: 300px;
    }
  }
}

@media (max-width: 768px) {
  .error-page {
    flex-direction: column;

    .error-content {
      margin-right: 0;
      margin-bottom: 40px;

      .error-code {
        font-size: 80px;
      }

      .error-desc h2 {
        font-size: 22px;
      }
    }

    .error-illustration {
      svg {
        width: 280px;
        height: 210px;
      }
    }
  }
}
</style>
