<template>
  <div class="kg-shell">
    <div class="envelope-field" aria-hidden="true">
      <span
        v-for="index in 7"
        :key="index"
        class="envelope-float"
        :style="{ '--float-index': index }"
      ></span>
    </div>

    <nav
      class="anchor-charm"
      aria-label="知识图谱锚点导航"
      :style="{ '--active-index': activeIndex }"
    >
      <span class="anchor-thread" aria-hidden="true"></span>
      <span class="anchor-pen" aria-hidden="true"></span>
      <button
        v-for="item in navItems"
        :key="item.id"
        class="anchor-bead"
        :class="{ 'is-active': activeNavId === item.id }"
        type="button"
        :aria-label="item.label"
        :title="item.label"
        @click="scrollToSection(item.id)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <el-container class="kg-app-container">
      <el-header class="topbar">
        <div class="topbar-brand">
          <div class="brand-mark">侨</div>
          <div class="topbar-title-group">
            <div class="topbar-title">侨批知识图谱</div>
            <div class="topbar-meta">SQLite 关系档案</div>
          </div>
        </div>

        <div class="topbar-controls">
          <el-input
            v-model="apiBase"
            class="api-input"
            size="small"
            aria-label="API 基础地址"
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
          <el-tag :type="statusType" effect="light">{{ statusLabel }}</el-tag>
          <el-button size="small" type="primary" :loading="refreshing" @click="$emit('refresh')">
            <el-icon><Refresh /></el-icon>
            <span>刷新</span>
          </el-button>
        </div>
      </el-header>

      <el-main class="kg-main">
        <slot />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  Collection,
  DataBoard,
  Files,
  Link,
  Location,
  Refresh,
  Share
} from '@element-plus/icons-vue'

const props = defineProps({
  baseUrl: {
    type: String,
    required: true
  },
  backendStatus: {
    type: String,
    default: 'checking'
  },
  refreshing: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:baseUrl', 'refresh'])
const activeNavId = ref('stats')

const navItems = [
  { id: 'stats', label: '侨批图谱', icon: Collection },
  { id: 'overview', label: '总览', icon: DataBoard },
  { id: 'record-graph', label: '批信关系', icon: Files },
  { id: 'place-flows', label: '地点流向', icon: Location },
  { id: 'node-neighbors', label: '节点邻居', icon: Share }
]

const apiBase = computed({
  get: () => props.baseUrl,
  set: (value) => emit('update:baseUrl', value)
})

const activeIndex = computed(() => {
  const index = navItems.findIndex((item) => item.id === activeNavId.value)
  return index >= 0 ? index : 0
})

const statusLabel = computed(() => {
  if (props.backendStatus === 'ok') return '后端已连接'
  if (props.backendStatus === 'error') return '后端不可用'
  return '连接中'
})

const statusType = computed(() => {
  if (props.backendStatus === 'ok') return 'success'
  if (props.backendStatus === 'error') return 'danger'
  return 'warning'
})

function scrollToSection(id) {
  activeNavId.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function updateActiveAnchor() {
  const anchorLine = window.innerHeight * 0.34
  let current = navItems[0].id

  for (const item of navItems) {
    const element = document.getElementById(item.id)
    if (!element) continue
    if (element.getBoundingClientRect().top <= anchorLine) {
      current = item.id
    }
  }

  activeNavId.value = current
}

onMounted(() => {
  updateActiveAnchor()
  window.addEventListener('scroll', updateActiveAnchor, { passive: true })
  window.addEventListener('resize', updateActiveAnchor)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateActiveAnchor)
  window.removeEventListener('resize', updateActiveAnchor)
})
</script>
