<template>
<<<<<<< Updated upstream
  <el-container class="app-shell">
    <el-aside class="app-sidebar" width="248px">
      <div class="brand-block">
        <div class="brand-mark">QP</div>
        <div>
          <div class="brand-title">侨批 RAG</div>
          <div class="brand-subtitle">NLP 工作台</div>
        </div>
      </div>

      <el-menu :default-active="route.path" router class="nav-menu">
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <span>检索</span>
        </el-menu-item>
        <el-menu-item index="/records/CSQP-SFHC-TEXT-001">
          <el-icon><Document /></el-icon>
          <span>记录详情</span>
        </el-menu-item>
        <el-menu-item index="/plain-interpretation">
          <el-icon><Reading /></el-icon>
          <span>白话解读</span>
        </el-menu-item>
        <el-menu-item index="/style-transfer">
          <el-icon><EditPen /></el-icon>
          <span>风格转换</span>
        </el-menu-item>
        <el-menu-item index="/analysis">
          <el-icon><Connection /></el-icon>
          <span>分析</span>
        </el-menu-item>
      </el-menu>
=======
  <router-view v-if="isWelcomeRoute" />

  <el-container v-else class="app-shell">
    <el-aside class="app-sidebar" width="272px">
      <div class="brand-block">
        <div class="brand-mark has-image">
          <img :src="brandLogo" alt="侨批记忆档案馆标识" />
        </div>
        <div class="brand-copy">
          <div class="brand-code">QIAOPI · RAG</div>
          <div class="brand-title">侨批记忆档案馆</div>
          <div class="brand-subtitle">跨洋家书数字化平台</div>
        </div>
      </div>

      <SeaRouteNavigation />
>>>>>>> Stashed changes
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <div class="topbar-title">{{ currentTitle }}</div>
          <div class="topbar-meta">本地 API：http://localhost:8000</div>
        </div>
        <el-tag type="success" effect="light">Mock 优先脚手架</el-tag>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
<<<<<<< Updated upstream
=======
import brandLogo from './assets/nav/1.png'
import SeaRouteNavigation from './components/SeaRouteNavigation.vue'
import { apiBaseUrl, demoMode } from './config/runtime'
>>>>>>> Stashed changes

const route = useRoute()

const titles = {
  '/': '数据看板',
  '/search': '检索工作台',
  '/plain-interpretation': '白话解读',
  '/style-transfer': '侨批风格转换',
  '/analysis': '分析工作台'
}

const currentTitle = computed(() => {
  if (route.path.startsWith('/records/')) return '记录详情'
  return titles[route.path] || '侨批 RAG 系统'
})
</script>
