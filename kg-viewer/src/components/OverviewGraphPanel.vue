<template>
  <section class="chart-panel graph-card">
    <div class="panel-heading-row">
      <div>
        <h2>图谱总览</h2>
        <p class="panel-meta">{{ graphSummary }}</p>
      </div>
      <el-button size="small" :loading="loading" @click="loadGraph">
        <el-icon><Refresh /></el-icon>
        <span>刷新</span>
      </el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div v-loading="loading" class="graph-shell">
      <div v-show="hasGraph" ref="chartRef" class="kg-chart overview-chart"></div>
      <el-empty v-if="!loading && !hasGraph" :image-size="96" description="暂无图谱总览" />
    </div>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import { getOverviewGraph } from '../api/graphApi'
import { buildGraphOption } from './graphOptions'

const props = defineProps({
  baseUrl: {
    type: String,
    required: true
  },
  refreshKey: {
    type: Number,
    required: true
  }
})

const graph = ref({ nodes: [], edges: [], summary: {} })
const loading = ref(false)
const error = ref('')
const chartRef = ref(null)
let chart

const hasGraph = computed(() => graph.value.nodes.length > 0)
const graphSummary = computed(() => {
  const summary = graph.value.summary || {}
  if (!hasGraph.value) return '有限规模的图谱预览'
  return `${summary.returned_nodes || graph.value.nodes.length} 个节点 / ${summary.returned_edges || graph.value.edges.length} 条关系`
})

function resizeChart() {
  chart?.resize()
}

async function loadGraph() {
  loading.value = true
  error.value = ''
  try {
    graph.value = await getOverviewGraph(props.baseUrl)
    await nextTick()
    renderGraph()
  } catch (requestError) {
    graph.value = { nodes: [], edges: [], summary: {} }
    error.value = `图谱总览暂不可用：${requestError.message}`
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!chartRef.value || !hasGraph.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption(buildGraphOption(graph.value, '图谱总览'), true)
  resizeChart()
}

watch(
  () => [props.baseUrl, props.refreshKey],
  () => loadGraph()
)

onMounted(() => {
  loadGraph()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})
</script>
