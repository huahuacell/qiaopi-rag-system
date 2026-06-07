<template>
  <section v-loading="loading" class="page-stack">
    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="stat-grid">
      <StatCard title="元数据记录" :value="stats.total_records || 0" tone="blue" />
      <StatCard title="文本记录" :value="stats.text_records || 0" tone="green" />
      <StatCard
        title="主要来源地"
        :value="stats.origin_places?.[0]?.label || 'Pending'"
        :caption="originCaption"
        tone="coral"
      />
      <StatCard
        title="高频亲属关系"
        :value="stats.kinship_distribution?.[0]?.label || 'Pending'"
        :caption="kinshipCaption"
        tone="gold"
      />
    </div>

    <div class="chart-grid">
      <section class="chart-panel">
        <div class="panel-heading-row">
          <h3>来源地分布</h3>
          <el-tag effect="plain">记录</el-tag>
        </div>
        <div ref="originChartRef" class="dashboard-chart"></div>
      </section>

      <section class="chart-panel">
        <div class="panel-heading-row">
          <h3>亲属关系分布</h3>
          <el-tag effect="plain">实体</el-tag>
        </div>
        <div ref="kinshipChartRef" class="dashboard-chart"></div>
      </section>

      <section class="chart-panel wide">
        <div class="panel-heading-row">
          <h3>年代分布</h3>
          <el-tag effect="plain">文本集</el-tag>
        </div>
        <div ref="timelineChartRef" class="dashboard-chart"></div>
      </section>
    </div>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { fetchDashboardStats } from '../api/dashboard'
import StatCard from '../components/StatCard.vue'
import fallbackStats from '../mock/dashboard.json'

const stats = ref({})
const loading = ref(false)
const error = ref('')
const originChartRef = ref(null)
const kinshipChartRef = ref(null)
const timelineChartRef = ref(null)
let originChart
let kinshipChart
let timelineChart

const originCaption = computed(() => {
  const item = stats.value.origin_places?.[0]
  return item ? `${item.value.toLocaleString()} 条记录` : ''
})

const kinshipCaption = computed(() => {
  const item = stats.value.kinship_distribution?.[0]
  return item ? `${item.value.toLocaleString()} 次提及` : ''
})

function toBarOption(title, items, color) {
  return {
    grid: { left: 54, right: 20, top: 20, bottom: 42 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: items.map((item) => item.label),
      axisLabel: { interval: 0, rotate: 20 }
    },
    yAxis: { type: 'value' },
    series: [{ name: title, type: 'bar', data: items.map((item) => item.value), itemStyle: { color } }]
  }
}

function toLineOption(items) {
  return {
    grid: { left: 54, right: 24, top: 24, bottom: 40 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: items.map((item) => item.label) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '文本',
        type: 'line',
        smooth: true,
        symbolSize: 9,
        data: items.map((item) => item.value),
        lineStyle: { color: '#2f7d7e', width: 3 },
        itemStyle: { color: '#d96c4a' },
        areaStyle: { color: 'rgba(47, 125, 126, 0.12)' }
      }
    ]
  }
}

function renderCharts() {
  if (!originChartRef.value || !kinshipChartRef.value || !timelineChartRef.value) return
  originChart = originChart || echarts.init(originChartRef.value)
  kinshipChart = kinshipChart || echarts.init(kinshipChartRef.value)
  timelineChart = timelineChart || echarts.init(timelineChartRef.value)

  originChart.setOption(toBarOption('来源地', stats.value.origin_places || [], '#2f6fb0'))
  kinshipChart.setOption(toBarOption('亲属关系', stats.value.kinship_distribution || [], '#2f7d7e'))
  timelineChart.setOption(toLineOption(stats.value.timeline || []))
}

async function loadStats() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await fetchDashboardStats()
  } catch {
    stats.value = fallbackStats
    error.value = '后端不可用，已加载数据看板本地 mock 数据。'
  } finally {
    loading.value = false
    await nextTick()
    renderCharts()
  }
}

onMounted(() => {
  loadStats()
  window.addEventListener('resize', renderCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderCharts)
  originChart?.dispose()
  kinshipChart?.dispose()
  timelineChart?.dispose()
})
</script>
