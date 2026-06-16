<template>
  <section class="chart-panel graph-card">
    <div class="panel-heading-row">
      <div>
        <h2>节点邻居</h2>
        <p class="panel-meta">{{ graphSummary }}</p>
      </div>
      <div class="panel-controls neighbor-controls">
        <el-input
          v-model="nodeId"
          class="node-input"
          size="small"
          placeholder="输入 node_id"
          @keyup.enter="loadGraph"
        />
        <el-input-number v-model="depth" size="small" :min="1" :max="2" controls-position="right" />
        <el-input-number v-model="limit" size="small" :min="1" :max="200" controls-position="right" />
        <el-button size="small" type="primary" :loading="loading" @click="loadGraph">
          <el-icon><Connection /></el-icon>
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
      <el-empty v-if="!loading && !hasGraph" :image-size="96" description="暂无节点邻居" />
    </div>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Connection } from '@element-plus/icons-vue'

import { getNodeNeighbors } from '../api/graphApi'
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

const nodeId = ref('person:母亲')
const depth = ref(1)
const limit = ref(50)
const graph = ref({ nodes: [], edges: [] })
const loading = ref(false)
const error = ref('')
const chartRef = ref(null)
let chart

const hasGraph = computed(() => graph.value.nodes.length > 0)
const graphSummary = computed(() => {
  if (!hasGraph.value) return '局部入边与出边关系'
  return `${graph.value.nodes.length} 个节点 / ${graph.value.edges.length} 条关系`
})

function resizeChart() {
  chart?.resize()
}

async function loadGraph() {
  if (!nodeId.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    graph.value = await getNodeNeighbors(props.baseUrl, nodeId.value.trim(), depth.value, limit.value)
    await nextTick()
    renderGraph()
  } catch (requestError) {
    graph.value = { nodes: [], edges: [] }
    error.value = `节点邻居暂不可用：${requestError.message}`
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!chartRef.value || !hasGraph.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption(buildGraphOption(graph.value, '节点邻居'), true)
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
