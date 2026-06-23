<template>
  <section v-loading="loading" class="archive-dashboard-page">
    <div class="archive-dashboard-bg" aria-hidden="true">
      <span class="archive-bg-line line-a"></span>
      <span class="archive-bg-line line-b"></span>
      <span class="archive-bg-seal seal-a">批</span>
      <span class="archive-bg-seal seal-b">档</span>
      <span class="archive-bg-wash"></span>
    </div>

    <nav class="archive-breadcrumb" aria-label="数据看板路径">
      <span>侨批 RAG</span>
      <i>›</i>
      <span>数据资产</span>
      <i>›</i>
      <strong>概览看板</strong>
    </nav>

    <section class="archive-dashboard-header">
      <div class="archive-header-grain" aria-hidden="true"></div>
      <div class="archive-header-rule" aria-hidden="true"></div>
      <div class="archive-header-seal" aria-hidden="true">档</div>
      <div class="archive-vertical-title" aria-hidden="true">
        <span v-for="char in '侨批数字档案馆'" :key="char">{{ char }}</span>
      </div>

      <div class="archive-header-content">
        <div class="archive-label-row">
          <i></i>
          <span>数据导览 · Archive Overview</span>
          <b></b>
          <em>QP-RAG-DATA-001</em>
        </div>

        <h1>侨批数据资产概览</h1>
        <p>
          从元数据、文本记录、来源地、亲属称谓与年代分布出发，观察侨批文献中的跨海流动、家书关系与侨乡记忆，为检索、释读与生成任务提供数据基础。
        </p>

        <div class="archive-header-meta">
          <span class="archive-stamp-tag">本地演示数据</span>
          <span class="archive-stamp-tag">样本规模 · {{ totalSampleCount }} 条</span>
          <strong>最后更新 · 2025-01-15</strong>
        </div>
      </div>
    </section>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
      class="archive-dashboard-alert"
    />

    <div class="archive-kpi-grid">
      <article v-for="card in kpiCards" :key="card.index" class="archive-kpi-card">
        <div class="archive-kpi-grain" aria-hidden="true"></div>
        <div class="archive-kpi-head">
          <span>{{ card.index }}</span>
          <strong>{{ card.title }}</strong>
        </div>
        <div class="archive-kpi-value" :class="{ 'is-text': card.isText }">{{ card.value }}</div>
        <p>{{ card.description }}</p>
        <b aria-hidden="true">{{ card.index }}</b>
      </article>
    </div>

    <section class="archive-analysis-section">
      <header class="archive-section-head">
        <div>
          <span></span>
          <h2>侨批文献分布分析</h2>
        </div>
        <p>从来源地、亲属称谓与年代维度观察侨批文本的结构特征。</p>
        <em>Distribution · 分布</em>
      </header>

      <div class="archive-chart-grid">
        <section class="archive-chart-card">
          <div class="archive-chart-grain" aria-hidden="true"></div>
          <div class="archive-chart-grid-bg" aria-hidden="true"></div>

          <div class="archive-chart-content">
            <span class="archive-stamp-tag">Origin · 来源地</span>
            <h3>来源地分布</h3>
            <p>观察侨批记录中的主要来源地结构，体现跨地域流动线索。</p>

            <div class="archive-mini-stat-list">
              <div v-for="(item, index) in originPlaces" :key="item.label" class="archive-mini-stat">
                <span>{{ index + 1 }}</span>
                <strong>{{ item.label }}</strong>
                <i>
                  <b :style="{ width: `${barPercent(item.value, maxOriginValue)}%` }"></b>
                </i>
                <em>{{ item.value?.toLocaleString?.() || item.value }}</em>
              </div>
            </div>

            <div ref="originChartRef" class="archive-dashboard-chart"></div>
          </div>
        </section>

        <section class="archive-chart-card">
          <div class="archive-chart-grain" aria-hidden="true"></div>
          <div class="archive-chart-grid-bg" aria-hidden="true"></div>

          <div class="archive-chart-content">
            <span class="archive-stamp-tag">Kinship · 亲属称谓</span>
            <h3>亲属关系分布</h3>
            <p>呈现文本中高频出现的家庭称谓，反映家书关系网络。</p>

            <div class="archive-mini-stat-list">
              <div v-for="(item, index) in relationshipDistribution" :key="item.label" class="archive-mini-stat">
                <span>{{ index + 1 }}</span>
                <strong>{{ item.label }}</strong>
                <i>
                  <b :style="{ width: `${barPercent(item.value, maxKinshipValue)}%` }"></b>
                </i>
                <em>{{ item.value?.toLocaleString?.() || item.value }}</em>
              </div>
            </div>

            <div ref="kinshipChartRef" class="archive-dashboard-chart"></div>
          </div>
        </section>

        <section class="archive-chart-card archive-chart-card-wide">
          <div class="archive-chart-grain" aria-hidden="true"></div>
          <div class="archive-chart-grid-bg" aria-hidden="true"></div>

          <div class="archive-chart-content">
            <span class="archive-stamp-tag">Timeline · 年代脉络</span>
            <h3>年代分布</h3>
            <p>展示文本样例在不同年代中的分布趋势，辅助理解侨批材料的时间背景。</p>

            <div class="archive-era-strip">
              <div v-for="item in timelineDistribution" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <em>条文本</em>
              </div>
              <div class="archive-era-unknown" title="年代不详（原始数据未标注年份）">
                <span>年代不详</span>
                <strong>{{ unknownYearCount }}</strong>
                <em>条文本</em>
              </div>
            </div>

            <div ref="timelineChartRef" class="archive-dashboard-chart archive-timeline-chart"></div>
          </div>
        </section>
      </div>
    </section>

    <aside class="archive-insight-note">
      <div class="archive-insight-grain" aria-hidden="true"></div>
      <div class="archive-insight-seal" aria-hidden="true">证</div>

      <div class="archive-insight-content">
        <div class="archive-insight-heading">
          <span class="archive-stamp-tag red">Insight</span>
          <strong>数据解读</strong>
          <i></i>
        </div>
        <p>
          当前样例数据中，新加坡、香港等地名体现了侨批跨地域流动特征；亲属关系以母亲、父亲等家庭称谓为主，说明侨批文本不仅是汇款记录，也是维系家庭关系与侨乡记忆的重要书信材料。
        </p>
        <em>— 侨批 RAG 系统 · 样本分析 · 2025</em>
      </div>
    </aside>

    <footer class="archive-dashboard-footer">
      <div>
        <span>批</span>
        <strong>侨批 RAG 智能档案工作台</strong>
        <i>·</i>
        <em>本地演示版本 · 仅供研究参考</em>
      </div>
      <p>QP-RAG · ARCHIVE WORKSTATION</p>
    </footer>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { fetchDashboardDistributions, fetchDashboardStats } from '../api/dashboard'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackStats from '../mock/dashboard.json'
import {
  formatRelationshipDistribution,
  originAxisLabelOption,
  splitYearDistribution
} from '../utils/dashboardPresentation'

const stats = ref({})
const distributions = ref({})
const loading = ref(false)
const error = ref('')
const originChartRef = ref(null)
const kinshipChartRef = ref(null)
const timelineChartRef = ref(null)
let originChart
let kinshipChart
let timelineChart
let resizeFrame = 0

const metadataRecordCount = computed(() => stats.value.metadata_record_count ?? stats.value.total_records ?? 0)
const textRecordCount = computed(() => stats.value.total_text_records ?? stats.value.text_records ?? 0)
const originPlaces = computed(() => distributions.value.top_places || stats.value.origin_places || [])
const relationshipDistribution = computed(() => formatRelationshipDistribution(
  distributions.value.relationship_distribution || stats.value.kinship_distribution || []
))
const rawTimelineDistribution = computed(
  () => distributions.value.year_distribution || stats.value.timeline || []
)
const timelinePresentation = computed(() => splitYearDistribution(rawTimelineDistribution.value))
const timelineDistribution = computed(() => timelinePresentation.value.years)
const unknownYearCount = computed(() => timelinePresentation.value.unknownCount)

const totalSampleCount = computed(() => {
  const total = Number(metadataRecordCount.value || 0) + Number(textRecordCount.value || 0)
  return total.toLocaleString()
})

const originCaption = computed(() => {
  const item = originPlaces.value[0]
  return item ? `呈现侨批跨海流动中的高频地点，${item.value.toLocaleString()} 条记录` : '呈现侨批跨海流动中的高频地点'
})

const kinshipCaption = computed(() => {
  const item = relationshipDistribution.value[0]
  return item ? `反映侨批家书中的家庭关系线索，${item.value.toLocaleString()} 次提及` : '反映侨批家书中的家庭关系线索'
})

const kpiCards = computed(() => [
  {
    index: '01',
    title: '元数据记录',
    value: Number(metadataRecordCount.value || 0).toLocaleString(),
    description: '支撑来源地、时间、人物关系等条件筛选'
  },
  {
    index: '02',
    title: '文本记录',
    value: Number(textRecordCount.value || 0).toLocaleString(),
    description: '用于白话释读、证据匹配与风格生成'
  },
  {
    index: '03',
    title: '主要来源地',
    value: originPlaces.value[0]?.label || 'Pending',
    description: originCaption.value,
    isText: true
  },
  {
    index: '04',
    title: '高频亲属关系',
    value: relationshipDistribution.value[0]?.label || 'Pending',
    description: kinshipCaption.value,
    isText: true
  }
])

const maxOriginValue = computed(() => maxValue(originPlaces.value))
const maxKinshipValue = computed(() => maxValue(relationshipDistribution.value))

function maxValue(items) {
  return Math.max(...items.map((item) => Number(item.value || 0)), 1)
}

function barPercent(value, max) {
  return Math.max(6, Math.round((Number(value || 0) / Number(max || 1)) * 100))
}

function archiveTooltip(unit = '条') {
  return {
    trigger: 'axis',
    confine: true,
    backgroundColor: '#FFFCF4',
    borderColor: '#DDD6C8',
    borderWidth: 1,
    padding: [8, 13],
    extraCssText: 'border-radius:2px;box-shadow:2px 3px 10px rgba(15,74,67,0.07);',
    textStyle: {
      color: '#1F2A28',
      fontFamily: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
      fontSize: 12
    },
    formatter(params) {
      const item = Array.isArray(params) ? params[0] : params
      const value = Number(item.value || 0).toLocaleString()
      const displayLabel = escapeTooltipText(item.name)
      const rawLabel = escapeTooltipText(item.data?.rawLabel)
      const rawLabelLine = rawLabel && rawLabel !== displayLabel
        ? `<div style="font-family:JetBrains Mono, Consolas, monospace;font-size:10px;color:#6F7C78;margin-top:2px;">原始字段：${rawLabel}</div>`
        : ''
      return `
        <div style="font-family:'Noto Sans SC',sans-serif;font-size:12px;color:#1F2A28;font-weight:600;margin-bottom:3px;">${displayLabel}</div>
        ${rawLabelLine}
        <div style="font-family:'Noto Serif SC',serif;font-size:15px;color:#0F4A43;font-weight:600;">${value} ${unit}</div>
      `
    }
  }
}

function escapeTooltipText(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function toBarOption(title, items, color = '#0F4A43') {
  const isKinship = title === '亲属关系'
  const isOrigin = title === '来源地'
  const axisLabelLayout = isOrigin
    ? originAxisLabelOption()
    : {
        interval: 0,
        rotate: isKinship ? 24 : 0,
        hideOverlap: true,
        width: isKinship ? 72 : 90,
        overflow: 'truncate',
        formatter: (value) => value.length > 8 ? `${value.slice(0, 8)}…` : value
      }
  return {
    animation: true,
    animationDuration: 700,
    color: [color],
    grid: { left: 44, right: 14, top: 14, bottom: isKinship || isOrigin ? 58 : 38, containLabel: true },
    tooltip: archiveTooltip(isKinship ? '次' : '条'),
    xAxis: {
      type: 'category',
      data: items.map((item) => item.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#DDD6C8' } },
      axisLabel: {
        ...axisLabelLayout,
        color: '#6F7C78',
        fontSize: 11,
        fontFamily: '"Noto Sans SC", sans-serif'
      }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(15,74,67,0.065)', type: 'dashed' } },
      axisLabel: {
        color: '#6F7C78',
        fontSize: 11,
        fontFamily: '"Noto Sans SC", sans-serif',
        formatter: (value) => (value >= 1000 ? `${Math.round(value / 1000)}k` : value)
      }
    },
    series: [
      {
        name: title,
        type: 'bar',
        barWidth: 24,
        data: items.map((item) => isKinship
          ? { value: item.value, rawLabel: item.rawLabel }
          : item.value),
        itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#1A6B61' },
            { offset: 1, color }
          ])
        },
        emphasis: {
          itemStyle: { color: '#0F4A43' }
        }
      }
    ]
  }
}

function toLineOption(items) {
  return {
    animation: true,
    animationDuration: 900,
    animationEasing: 'cubicOut',
    color: ['#0F4A43'],
    grid: { left: 42, right: 24, top: 18, bottom: 34, containLabel: true },
    tooltip: archiveTooltip('条文本'),
    xAxis: {
      type: 'category',
      data: items.map((item) => item.label),
      boundaryGap: false,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#DDD6C8' } },
      axisLabel: {
        color: '#6F7C78',
        fontSize: 11,
        fontFamily: '"Noto Sans SC", sans-serif'
      }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(15,74,67,0.065)', type: 'dashed' } },
      axisLabel: {
        color: '#6F7C78',
        fontSize: 11,
        fontFamily: '"Noto Sans SC", sans-serif'
      }
    },
    series: [
      {
        name: '文本',
        type: 'line',
        smooth: true,
        symbolSize: 9,
        data: items.map((item) => item.value),
        lineStyle: { color: '#0F4A43', width: 2 },
        itemStyle: { color: '#A74432', borderColor: '#FFFCF4', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(15,74,67,0.20)' },
            { offset: 1, color: 'rgba(15,74,67,0.02)' }
          ])
        }
      }
    ]
  }
}

function renderCharts() {
  if (!originChartRef.value || !kinshipChartRef.value || !timelineChartRef.value) return
  originChart = originChart || echarts.init(originChartRef.value)
  kinshipChart = kinshipChart || echarts.init(kinshipChartRef.value)
  timelineChart = timelineChart || echarts.init(timelineChartRef.value)

  resizeCharts()
  originChart.setOption(toBarOption('来源地', originPlaces.value, '#0F4A43'), true)
  kinshipChart.setOption(toBarOption('亲属关系', relationshipDistribution.value, '#0F4A43'), true)
  timelineChart.setOption(toLineOption(timelineDistribution.value), true)
}

function resizeCharts() {
  originChart?.resize()
  kinshipChart?.resize()
  timelineChart?.resize()
}

function scheduleResizeCharts() {
  if (resizeFrame) return
  resizeFrame = requestAnimationFrame(() => {
    resizeFrame = 0
    resizeCharts()
  })
}

async function loadStats() {
  loading.value = true
  error.value = ''
  try {
    const [statsPayload, distributionsPayload] = await Promise.all([
      fetchDashboardStats(),
      fetchDashboardDistributions()
    ])
    stats.value = statsPayload
    distributions.value = distributionsPayload
  } catch (requestError) {
    if (demoMode) {
      stats.value = fallbackStats
      distributions.value = {}
      error.value = demoFailureMessage('数据看板请求')
    } else {
      stats.value = {}
      distributions.value = {}
      error.value = apiFailureMessage(requestError, '数据看板请求')
    }
  } finally {
    loading.value = false
    await nextTick()
    renderCharts()
  }
}

onMounted(() => {
  loadStats()
  window.addEventListener('resize', scheduleResizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', scheduleResizeCharts)
  if (resizeFrame) {
    cancelAnimationFrame(resizeFrame)
    resizeFrame = 0
  }
  originChart?.dispose()
  kinshipChart?.dispose()
  timelineChart?.dispose()
})
</script>
