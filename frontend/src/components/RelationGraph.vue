<template>
  <article class="analysis-card analysis-graph-card">
    <div class="analysis-card-marker"></div>
    <div class="analysis-card-header">
      <h2>{{ title }}</h2>
      <span class="analysis-badge">{{ badge }}</span>
    </div>
    <div class="analysis-graph-field">
      <div ref="chartRef" class="relation-chart"></div>
    </div>
    <p v-if="note" class="analysis-card-note">{{ note }}</p>
  </article>
</template>

<script setup>
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, default: '关系图谱' },
  badge: { type: String, default: 'Entity Graph' },
  note: { type: String, default: '' },
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart

function renderChart() {
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption({
    backgroundColor: 'transparent',
    animationDuration: 900,
    tooltip: {
      trigger: 'item',
      borderWidth: 1,
      borderColor: '#DDD6C8',
      backgroundColor: '#FFFCF4',
      textStyle: {
        color: '#1F2A28',
        fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif',
        fontSize: 12
      },
      extraCssText: 'box-shadow:0 8px 20px rgba(54,43,24,.10);border-radius:2px;'
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: false,
        top: 16,
        bottom: 22,
        left: 18,
        right: 18,
        data: props.nodes,
        links: props.links,
        force: {
          repulsion: 140,
          edgeLength: 88,
          gravity: 0.08
        },
        label: {
          show: true,
          position: 'bottom',
          distance: 8,
          color: '#1F2A28',
          fontSize: 12,
          fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif',
          backgroundColor: '#FFFCF4',
          borderColor: '#DDD6C8',
          borderWidth: 1,
          borderRadius: 2,
          padding: [3, 6]
        },
        edgeLabel: {
          show: false
        },
        lineStyle: {
          color: '#8D9A91',
          width: 1.3,
          opacity: 0.72,
          curveness: 0.04
        },
        itemStyle: {
          color: '#0F4A43',
          borderColor: '#FFFCF4',
          borderWidth: 2,
          shadowBlur: 8,
          shadowColor: 'rgba(15, 74, 67, 0.12)'
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 2,
            color: '#A74432'
          }
        }
      }
    ]
  })
  chart.resize()
}

function handleResize() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', handleResize)
})

watch(() => [props.nodes, props.links], renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>
