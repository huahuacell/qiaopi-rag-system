<template>
  <section class="analysis-panel">
    <div class="panel-heading-row">
      <h3>{{ title }}</h3>
      <el-tag effect="plain">图谱</el-tag>
    </div>
    <div ref="chartRef" class="relation-chart"></div>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, default: '关系图谱' },
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart

function renderChart() {
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption({
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        label: { show: true },
        force: { repulsion: 120, edgeLength: 90 },
        data: props.nodes,
        links: props.links,
        lineStyle: { color: '#8aa0b8', width: 1.5 },
        itemStyle: { color: '#2f7d7e' }
      }
    ]
  })
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

watch(() => [props.nodes, props.links], renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
})
</script>
