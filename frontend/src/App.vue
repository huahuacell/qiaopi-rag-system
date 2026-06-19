<template>
  <router-view v-if="isWelcomeRoute" />

  <el-container v-else class="app-shell">
    <el-aside class="app-sidebar" width="248px">
      <div class="brand-block">
        <div class="brand-mark">QP</div>
        <div class="brand-copy">
          <div class="brand-code">QIAOPI · RAG</div>
          <div class="brand-title">侨批 RAG</div>
          <div class="brand-subtitle">智能档案工作台</div>
        </div>
      </div>

      <div class="nav-caption">档案功能目录</div>
      <el-menu :default-active="route.path" router class="nav-menu">
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>系统首页</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
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
        <el-menu-item index="/knowledge-graph">
          <el-icon><Share /></el-icon>
          <span>知识图谱</span>
        </el-menu-item>
        <el-menu-item index="/analysis">
          <el-icon><Connection /></el-icon>
          <span>分析</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar-heading">
          <div class="topbar-kicker">QIAOPI DIGITAL ARCHIVE</div>
          <div class="topbar-title">{{ currentTitle }}</div>
          <div class="topbar-meta"><span>API</span>{{ apiBaseUrl }}</div>
        </div>
        <el-tag :type="demoMode ? 'warning' : 'success'" effect="plain">
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
import { apiBaseUrl, demoMode } from './config/runtime'

const route = useRoute()

const titles = {
  '/dashboard': '数据看板',
  '/search': '检索工作台',
  '/plain-interpretation': '白话解读',
  '/style-transfer': '侨批风格转换',
  '/knowledge-graph': '知识图谱',
  '/analysis': '分析工作台'
}

const isWelcomeRoute = computed(() => route.name === 'welcome')

const currentTitle = computed(() => {
  if (route.path.startsWith('/records/')) return '记录详情'
  return titles[route.path] || '侨批 RAG 系统'
})
</script>
