<template>
  <section class="chart-panel graph-card">
    <div class="panel-heading-row">
      <div>
        <h2>批信关系图</h2>
        <p class="panel-meta">{{ graphSummary }}</p>
      </div>
      <div class="panel-controls">
        <el-input
          v-model="recordId"
          class="record-input"
          size="small"
          placeholder="输入 record_id"
          @keyup.enter="loadGraph"
        />
        <el-button size="small" type="primary" :loading="loading" @click="loadGraph">
          <el-icon><Search /></el-icon>
          <span>载入</span>
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div v-loading="loading" class="graph-shell">
      <div v-show="hasGraph" ref="chartRef" class="kg-chart"></div>
      <el-empty v-if="!loading && !hasGraph" :image-size="96" description="暂无批信关系图" />
    </div>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

import { getRecordGraph } from '../api/graphApi'
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

const recordId = ref('CSQP-SFHC-TEXT-017')
const graph = ref({ nodes: [], edges: [] })
const loading = ref(false)
const error = ref('')
const chartRef = ref(null)
let chart

const hasGraph = computed(() => graph.value.nodes.length > 0)
const graphSummary = computed(() => {
  if (!hasGraph.value) return '以单封批信为中心的局部关系'
  return `${graph.value.nodes.length} 个节点 / ${graph.value.edges.length} 条关系`
})

function resizeChart() {
  chart?.resize()
}

async function loadGraph() {
  if (!recordId.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    graph.value = await getRecordGraph(props.baseUrl, recordId.value.trim())
    await nextTick()
    renderGraph()
  } catch (requestError) {
    graph.value = { nodes: [], edges: [] }
    error.value = `批信关系图暂不可用：${requestError.message}`
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!chartRef.value || !hasGraph.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption(toGraphOption(graph.value, '批信关系图'), true)
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

function toGraphOption(payload, title) {
  return buildGraphOption(payload, title)
}
</script>
