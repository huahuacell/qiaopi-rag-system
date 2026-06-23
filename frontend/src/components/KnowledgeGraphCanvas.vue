<template>
  <div class="kg-product-canvas" :class="`is-${viewMode}`">
    <div v-if="viewMode === 'flow' && nodes.length" class="kg-flow-lanes" aria-hidden="true">
      <span>海外侨居地</span>
      <span>侨批与侨汇</span>
      <span>侨乡家园</span>
    </div>
    <div v-if="nodes.length" ref="chartRef" class="kg-product-chart"></div>
    <el-empty v-else description="当前筛选下暂无可展示的图谱节点" />
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
import { truncateDisplayLabel } from '../utils/graphLabelMap'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  selectedNodeId: { type: String, default: '' },
  selectedEdgeId: { type: String, default: '' },
  viewMode: { type: String, default: 'kinship' }
})

const emit = defineEmits(['select-node', 'select-edge'])
const chartRef = ref(null)
let chart

function renderChart() {
  if (!chartRef.value || !props.nodes.length) {
    chart?.clear()
    return
  }
  chart = chart || echarts.init(chartRef.value)
  const types = [...new Set(props.nodes.map((node) => nodeType(node)))]
  const isFlow = props.viewMode === 'flow'
  const isKinship = props.viewMode === 'kinship'
  const chartNodes = isFlow ? flowLayoutNodes(props.nodes) : forceLayoutNodes(props.nodes)

  chart.setOption(
    {
      backgroundColor: 'transparent',
      animationDuration: 760,
      animationDurationUpdate: 620,
      animationEasingUpdate: 'cubicInOut',
      tooltip: archiveTooltip(),
      legend: {
        type: 'scroll',
        bottom: 10,
        left: 'center',
        data: types.map((type) => NODE_TYPE_LABELS[type] || type),
        icon: 'roundRect',
        itemWidth: 12,
        itemHeight: 8,
        itemGap: 16,
        textStyle: {
          color: '#65716c',
          fontFamily: '"Noto Serif SC", "Songti SC", serif',
          fontSize: 11
        }
      },
      series: [
        {
          id: 'qiaopi-graph',
          type: 'graph',
          layout: isFlow ? 'none' : 'force',
          roam: true,
          draggable: !isFlow,
          top: isFlow ? 54 : 18,
          right: 18,
          bottom: 54,
          left: 18,
          categories: types.map((type) => ({
            name: NODE_TYPE_LABELS[type] || type,
            itemStyle: { color: NODE_COLORS[type] || '#6f7c78' }
          })),
          force: isFlow
            ? undefined
            : isKinship
              ? {
                  repulsion: 235,
                  edgeLength: [76, 150],
                  gravity: 0.11,
                  friction: 0.46,
                  layoutAnimation: false
                }
              : {
                  repulsion: 170,
                  edgeLength: [62, 118],
                  gravity: 0.18,
                  friction: 0.55,
                  layoutAnimation: false
                },
          label: {
            show: true,
            position: 'right',
            distance: 8,
            color: '#283a36',
            fontFamily: '"Noto Serif SC", "Songti SC", serif',
            fontSize: 11,
            lineHeight: 15,
            width: 92,
            overflow: 'truncate',
            formatter: (params) => params.data.shortName
          },
          edgeLabel: {
            show: false,
            color: '#6d6358',
            fontSize: 10,
            padding: [2, 5],
            borderRadius: 2,
            backgroundColor: 'rgba(250, 246, 236, 0.94)',
            formatter: (params) => params.data.name
          },
          lineStyle: {
            color: 'source',
            opacity: isFlow ? 0.54 : isKinship ? 0.44 : 0.38,
            width: isKinship ? 1.45 : 1.35,
            curveness: isFlow ? 0.16 : 0.1
          },
          select: {
            itemStyle: {
              borderColor: '#ad4935',
              borderWidth: 5,
              shadowBlur: 20,
              shadowColor: 'rgba(167, 68, 50, 0.3)'
            }
          },
          emphasis: {
            focus: 'adjacency',
            scale: 1.1,
            label: { show: true, color: '#173f39', fontWeight: 700 },
            edgeLabel: { show: true },
            lineStyle: {
              color: '#a74432',
              width: 3,
              opacity: 0.9,
              shadowBlur: 8,
              shadowColor: 'rgba(167, 68, 50, 0.28)'
            }
          },
          blur: {
            itemStyle: { opacity: 0.18 },
            label: { opacity: 0.2 },
            lineStyle: { opacity: 0.06 }
          },
          selectedMode: 'single',
          universalTransition: true,
          data: chartNodes,
          links: props.edges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            name: edge.displayLabel || EDGE_TYPE_LABELS[edge.rawType || edge.type] || edgeTypeLabel(edge),
            raw: edge,
            lineStyle: {
              width: edgeWidth(edge),
              color:
                edge.id === props.selectedEdgeId
                  ? '#a74432'
                  : isFlow
                    ? '#617d70'
                    : undefined,
              opacity: edge.id === props.selectedEdgeId ? 0.95 : undefined
            }
          }))
        }
      ]
    },
    { notMerge: true, lazyUpdate: false }
  )

  chart.off('click')
  chart.on('click', (params) => {
    if (params.dataType === 'node') emit('select-node', params.data.raw)
    if (params.dataType === 'edge') emit('select-edge', params.data.raw)
  })
  chart.resize()
}

function archiveTooltip() {
  return {
    trigger: 'item',
    confine: true,
    enterable: false,
    borderColor: '#cdbfaa',
    borderWidth: 1,
    padding: [12, 14],
    extraCssText:
      'max-width:320px;border-radius:4px;box-shadow:0 14px 36px rgba(49,43,34,.16);',
    backgroundColor: 'rgba(255, 252, 242, 0.98)',
    textStyle: {
      color: '#2f3b37',
      fontFamily: '"Noto Serif SC", "Songti SC", serif',
      fontSize: 12,
      lineHeight: 20
    },
    formatter(params) {
      if (params.dataType === 'edge') {
        const edge = params.data.raw
        const count = edge.properties?.count || edge.weight
        return [
          `<div class="kg-chart-tooltip-title">${escapeHtml(edgeTypeLabel(edge))}</div>`,
          count ? `相关数量：${escapeHtml(count)}` : '',
          edge.record_id ? `侨批记录：${escapeHtml(edge.record_id)}` : '',
          edge.evidence_text
            ? `原文证据：${escapeHtml(truncateDisplayLabel(edge.evidence_text, 44))}`
            : '证据状态：可在右侧档案卡查看'
        ]
          .filter(Boolean)
          .join('<br/>')
      }
      const node = params.data.raw
      const properties = node.properties || {}
      const count =
        properties.deduplicated_count ||
        properties.count ||
        properties.record_ids?.length ||
        1
      const rawCode =
        node.visualType === 'theme' && node.themeCode
          ? `主题代码：${escapeHtml(node.themeCode)}`
          : ''
      return [
        `<div class="kg-chart-tooltip-title">${escapeHtml(nodeDisplayLabel(node))}</div>`,
        `类型：${escapeHtml(NODE_TYPE_LABELS[nodeType(node)] || '未知节点')}`,
        `关联次数：${escapeHtml(count)}`,
        `证据数：${escapeHtml(properties.evidence_count || '点击查看')}`,
        rawCode
      ]
        .filter(Boolean)
        .join('<br/>')
    }
  }
}

function forceLayoutNodes(nodes) {
  const groupedIndex = new Map()
  return nodes.map((node) => {
    const type = nodeType(node)
    const index = groupedIndex.get(type) || 0
    groupedIndex.set(type, index + 1)
    const seed = initialPosition(type, index)
    return chartNode(node, { x: seed.x, y: seed.y })
  })
}

function flowLayoutNodes(nodes) {
  const width = Math.max(chartRef.value?.clientWidth || 900, 680)
  const height = Math.max(chartRef.value?.clientHeight || 610, 500) - 105
  const lanes = {
    overseas_place: nodes.filter((node) => nodeType(node) === 'overseas_place'),
    record: nodes.filter((node) => nodeType(node) === 'record'),
    record_group: nodes.filter((node) => nodeType(node) === 'record_group'),
    hometown_place: nodes.filter((node) => nodeType(node) === 'hometown_place')
  }
  const centers = {
    overseas_place: width * 0.12,
    record: width * 0.48,
    record_group: width * 0.48,
    hometown_place: width * 0.82
  }

  return nodes.map((node) => {
    const type = nodeType(node)
    const lane = type === 'record_group' ? lanes.record_group : lanes[type] || []
    const index = lane.findIndex((item) => item.id === node.id)
    const combinedRecordCount = lanes.record.length + lanes.record_group.length
    const effectiveLane =
      type === 'record' || type === 'record_group'
        ? [...lanes.record, ...lanes.record_group]
        : lane
    const effectiveIndex =
      type === 'record' || type === 'record_group'
        ? effectiveLane.findIndex((item) => item.id === node.id)
        : index
    return chartNode(node, {
      x: centers[type] || width * 0.48,
      y: distributedY(
        effectiveIndex,
        type === 'record' || type === 'record_group'
          ? combinedRecordCount
          : effectiveLane.length,
        height
      ),
      fixed: true
    })
  })
}

function chartNode(node, extra = {}) {
  const type = nodeType(node)
  const selected = node.id === props.selectedNodeId
  return {
    id: node.id,
    name: nodeDisplayLabel(node),
    shortName: compactNodeLabel(node, type),
    category: NODE_TYPE_LABELS[type] || type,
    value: node.id,
    raw: node,
    symbol: nodeSymbol(type),
    symbolSize: symbolSize(node),
    selected,
    label: nodeLabelStyle(type),
    itemStyle: {
      color: NODE_COLORS[type] || '#6f7c78',
      borderColor: selected ? '#a74432' : '#f8f0df',
      borderWidth: selected ? 5 : 2,
      shadowBlur: selected ? 20 : 9,
      shadowOffsetY: 3,
      shadowColor: selected
        ? 'rgba(167, 68, 50, 0.28)'
        : 'rgba(52, 62, 56, 0.16)'
    },
    ...extra
  }
}

function initialPosition(type, index) {
  const angle = (index * 137.5 * Math.PI) / 180
  const radii = {
    person: 28,
    kinship: 66,
    record: 128,
    amount: 105,
    theme: 118,
    place: 145,
    evidence: 155,
    date: 138,
    metadata_record: 160
  }
  const radius = (radii[type] || 125) + (index % 3) * 10
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius
  }
}

function distributedY(index, count, height) {
  if (count <= 1) return height / 2
  const padding = 36
  return padding + (index * (height - padding * 2)) / Math.max(count - 1, 1)
}

function nodeSymbol(type) {
  if (['record', 'record_group', 'metadata_record'].includes(type)) return 'roundRect'
  if (type === 'kinship') return 'diamond'
  if (type === 'amount') return 'rect'
  if (type === 'theme') return 'roundRect'
  return 'circle'
}

function symbolSize(node) {
  const type = nodeType(node)
  const weight = Math.min(Number(node.importance || node.properties?.count || 0), 30)
  if (type === 'record') return [82, 32]
  if (type === 'record_group') return [96, 38]
  if (type === 'metadata_record') return [70, 30]
  if (type === 'evidence') return 24
  if (type === 'amount') return [58, 30]
  if (type === 'theme') return [58, 30]
  if (type === 'kinship') return 36 + weight * 0.25
  if (type === 'person') return 38 + weight * 0.35
  if (['overseas_place', 'hometown_place'].includes(type)) return 46 + weight * 0.2
  return 34 + weight * 0.2
}

function labelLength(type) {
  if (type === 'record') return 15
  if (type === 'record_group') return 10
  if (['overseas_place', 'hometown_place', 'place'].includes(type)) return 8
  return 7
}

function compactNodeLabel(node, type) {
  if (type === 'record') {
    const recordId = String(node.record_id || node.id || '').replace(/^record:/, '')
    const suffix = recordId.match(/(\d{2,4})$/)?.[1]
    return suffix ? `${suffix}号侨批` : '侨批记录'
  }
  return truncateDisplayLabel(nodeDisplayLabel(node), labelLength(type))
}

function nodeLabelStyle(type) {
  if (['record', 'record_group', 'theme', 'amount', 'metadata_record'].includes(type)) {
    return {
      position: 'inside',
      distance: 0,
      width: type === 'record_group' ? 82 : type === 'record' ? 70 : 50,
      overflow: 'truncate',
      color: '#fffaf0',
      fontSize: type === 'record' ? 9 : 10,
      fontWeight: 600,
      align: 'center'
    }
  }
  if (type === 'hometown_place') {
    return { position: 'left', distance: 9, width: 92, overflow: 'truncate' }
  }
  return { position: 'right', distance: 8, width: 92, overflow: 'truncate' }
}

function edgeWidth(edge) {
  const amount = Number(edge.properties?.amount_number || 0)
  const count = Number(edge.properties?.count || edge.weight || 1)
  const confidence = Number(edge.confidence || 0.6)
  if (amount > 0) return Math.min(5, 1.2 + Math.log10(amount + 1))
  return Math.min(4.5, 1 + Math.sqrt(count) * 0.45 + confidence)
}

function focusNode(nodeId) {
  if (!chart) return
  const dataIndex = props.nodes.findIndex((node) => node.id === nodeId)
  if (dataIndex < 0) return
  chart.dispatchAction({ type: 'downplay', seriesIndex: 0 })
  chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex })
  chart.dispatchAction({ type: 'select', seriesIndex: 0, dataIndex })
}

function resetView() {
  if (!chart) return
  chart.dispatchAction({ type: 'restore' })
  renderChart()
}

function exportImage() {
  if (!chart) return ''
  return chart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#f4efe3',
    excludeComponents: ['toolbox']
  })
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
  if (props.viewMode === 'flow') renderChart()
}

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', resizeChart)
})

watch(
  () => [
    props.nodes,
    props.edges,
    props.selectedNodeId,
    props.selectedEdgeId,
    props.viewMode
  ],
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

defineExpose({ exportImage, focusNode, resetView })
</script>
