<template>
  <div class="kg-product-canvas">
    <div v-if="nodes.length" ref="chartRef" class="kg-product-chart"></div>
    <el-empty v-else description="暂无可展示的图谱节点" />
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  EDGE_TYPE_LABELS,
  NODE_COLORS,
  NODE_TYPE_LABELS,
  edgeTypeLabel,
  nodeDisplayLabel,
  nodeType
} from '../utils/graphPresentation'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  selectedNodeId: { type: String, default: '' }
})

const emit = defineEmits(['select-node', 'select-edge'])
const chartRef = ref(null)
let chart

function renderChart() {
  if (!chartRef.value || !props.nodes.length) return
  chart = chart || echarts.init(chartRef.value)
  const types = [...new Set(props.nodes.map((node) => nodeType(node)))]
  chart.setOption(
    {
      backgroundColor: 'transparent',
      animationDuration: 700,
      tooltip: {
        trigger: 'item',
        confine: true,
        borderColor: '#d9cfbd',
        backgroundColor: '#fffdf7',
        textStyle: { color: '#25322f', fontSize: 12 },
        formatter(params) {
          if (params.dataType === 'edge') {
            const edge = params.data.raw
            return [
              `<strong>${edgeTypeLabel(edge)}</strong>`,
              edge.record_id ? `记录：${escapeHtml(edge.record_id)}` : '',
              edge.evidence_text ? `证据：${escapeHtml(edge.evidence_text)}` : '',
              edge.source_id ? `来源：${escapeHtml(edge.source_id)}` : ''
            ]
              .filter(Boolean)
              .join('<br/>')
          }
          const node = params.data.raw
          return [
            `<strong>${escapeHtml(nodeDisplayLabel(node))}</strong>`,
            `类型：${escapeHtml(NODE_TYPE_LABELS[nodeType(node)] || nodeType(node))}`,
            `节点：${escapeHtml(node.id)}`,
            node.source_id ? `来源：${escapeHtml(node.source_id)}` : ''
          ].join('<br/>')
        }
      },
      legend: {
        type: 'scroll',
        bottom: 0,
        data: types.map((type) => NODE_TYPE_LABELS[type] || type),
        textStyle: { color: '#61706c', fontSize: 11 }
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          top: 10,
          bottom: 42,
          categories: types.map((type) => ({
            name: NODE_TYPE_LABELS[type] || type,
            itemStyle: { color: NODE_COLORS[type] || '#6f7c78' }
          })),
          force: {
            repulsion: 260,
            edgeLength: [92, 180],
            gravity: 0.06,
            friction: 0.25
          },
          label: {
            show: true,
            position: 'right',
            color: '#25322f',
            fontSize: 11,
            formatter: (params) => params.data.name
          },
          edgeLabel: { show: false },
          lineStyle: {
            color: '#9ba8a2',
            opacity: 0.62,
            width: 1.2,
            curveness: 0.12
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { color: '#a74432', width: 2.2, opacity: 0.9 }
          },
          data: props.nodes.map((node) => ({
            id: node.id,
            name: nodeDisplayLabel(node),
            category: NODE_TYPE_LABELS[nodeType(node)] || nodeType(node),
            value: node.id,
            raw: node,
            symbol: nodeType(node) === 'record' || nodeType(node) === 'metadata_record'
              ? 'roundRect'
              : 'circle',
            symbolSize: symbolSize(nodeType(node)),
            itemStyle: {
              color: NODE_COLORS[nodeType(node)] || '#6f7c78',
              borderColor: node.id === props.selectedNodeId ? '#a74432' : '#fffdf7',
              borderWidth: node.id === props.selectedNodeId ? 4 : 2,
              shadowBlur: node.id === props.selectedNodeId ? 14 : 5,
              shadowColor: 'rgba(15, 74, 67, 0.15)'
            }
          })),
          links: props.edges.map((edge) => ({
            source: edge.source,
            target: edge.target,
            name: EDGE_TYPE_LABELS[edge.type] || edge.type,
            raw: edge,
            lineStyle: {
              width: Math.max(1, Math.min(3, Number(edge.confidence || 0.5) * 2.2))
            }
          }))
        }
      ]
    },
    true
  )
  chart.off('click')
  chart.on('click', (params) => {
    if (params.dataType === 'node') emit('select-node', params.data.raw)
    if (params.dataType === 'edge') emit('select-edge', params.data.raw)
  })
  chart.resize()
}

function symbolSize(type) {
  if (type === 'record') return 44
  if (type === 'metadata_record') return 38
  if (type === 'evidence') return 18
  if (type === 'amount') return 28
  return 32
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function resizeChart() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', resizeChart)
})

watch(
  () => [props.nodes, props.edges, props.selectedNodeId],
  async () => {
    await nextTick()
    renderChart()
  },
  { deep: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})
</script>
