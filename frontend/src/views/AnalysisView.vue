<template>
  <section v-loading="loading" class="page-stack">
    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="analysis-grid">
      <WordCloudPanel title="词云" :words="wordCloud" />
      <RelationGraph title="关系图谱" :nodes="relationNodes" :links="relationLinks" />
      <RelationGraph title="小型知识图谱" :nodes="knowledgeNodes" :links="knowledgeLinks" />
      <section class="analysis-panel storytelling">
        <div class="panel-heading-row">
          <h3>文化叙事</h3>
          <el-tag effect="plain">草稿</el-tag>
        </div>
        <p>
          一封从新加坡寄往潮州的侨批，把移民劳作、家庭生计、亲属责任和水客传递连接在一起。
          后续 RAG 层会把这些有证据支撑的记录转化为可解释的叙事摘要。
        </p>
        <div class="story-metrics">
          <StatCard title="来源地类型" :value="stats.origin_places?.length || 0" tone="blue" />
          <StatCard title="亲属关系类型" :value="stats.kinship_distribution?.length || 0" tone="green" />
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchDashboardStats } from '../api/dashboard'
import RelationGraph from '../components/RelationGraph.vue'
import StatCard from '../components/StatCard.vue'
import WordCloudPanel from '../components/WordCloudPanel.vue'
import fallbackStats from '../mock/dashboard.json'

const stats = ref(fallbackStats)
const loading = ref(false)
const error = ref('')

const wordCloud = computed(() => [
  { label: '母亲', size: 34, color: '#2f7d7e' },
  { label: '八元', size: 30, color: '#d96c4a' },
  { label: '新加坡', size: 32, color: '#2f6fb0' },
  { label: '潮州', size: 28, color: '#6f5aa8' },
  { label: '米粮', size: 24, color: '#b77b28' },
  { label: '药费', size: 22, color: '#697386' },
  { label: '水客', size: 20, color: '#3d6d5c' },
  { label: '家用', size: 26, color: '#884a39' }
])

const relationNodes = computed(() => [
  { name: '陈生', symbolSize: 48 },
  { name: '母亲', symbolSize: 44 },
  { name: '新加坡', symbolSize: 42 },
  { name: '广东潮州', symbolSize: 42 },
  { name: '八元', symbolSize: 38 }
])

const relationLinks = computed(() => [
  { source: '陈生', target: '母亲', name: '汇款给' },
  { source: '陈生', target: '新加坡', name: '来源地' },
  { source: '母亲', target: '广东潮州', name: '目的地' },
  { source: '陈生', target: '八元', name: '寄出' }
])

const knowledgeNodes = computed(() => [
  { name: '侨批文本', symbolSize: 54 },
  { name: '亲属责任', symbolSize: 40 },
  { name: '汇款', symbolSize: 40 },
  { name: '迁移路线', symbolSize: 40 },
  { name: '家庭支持', symbolSize: 40 }
])

const knowledgeLinks = computed(() => [
  { source: '侨批文本', target: '亲属责任' },
  { source: '侨批文本', target: '汇款' },
  { source: '侨批文本', target: '迁移路线' },
  { source: '汇款', target: '家庭支持' }
])

async function loadStats() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await fetchDashboardStats()
  } catch {
    stats.value = fallbackStats
    error.value = '后端不可用，已加载分析页本地 mock 数据。'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>
