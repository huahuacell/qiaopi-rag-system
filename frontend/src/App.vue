<template>
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
    </el-aside>

    <el-container>
      <el-header class="topbar" :class="{ 'is-product-view': !showRuntimeStatus }">
        <div class="topbar-heading">
          <div class="topbar-kicker">QIAOPI DIGITAL ARCHIVE</div>
          <div class="topbar-title">{{ currentTitle }}</div>
          <div v-if="showRuntimeStatus" class="topbar-meta"><span>API</span>{{ apiBaseUrl }}</div>
        </div>
        <el-tag v-if="showRuntimeStatus" :type="demoMode ? 'warning' : 'success'" effect="plain">
          {{ demoMode ? '显式演示模式' : '正式接口模式' }}
        </el-tag>
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
import brandLogo from './assets/nav/1.png'
import SeaRouteNavigation from './components/SeaRouteNavigation.vue'
import { apiBaseUrl, demoMode } from './config/runtime'

const route = useRoute()

const titles = {
  '/dashboard': '数据看板',
  '/search': '检索工作台',
  '/plain-interpretation': '白话解读',
  '/style-transfer': '侨批风格转换',
  '/nlp': '在线 NLP',
  '/knowledge-graph': '知识图谱',
  '/analysis': '情感分类'
}

const isWelcomeRoute = computed(() => route.name === 'welcome')
const showRuntimeStatus = computed(() => route.path !== '/analysis')

const currentTitle = computed(() => {
  if (route.path.startsWith('/records/')) return '记录详情'
  return titles[route.path] || '侨批 RAG 系统'
})
</script>
