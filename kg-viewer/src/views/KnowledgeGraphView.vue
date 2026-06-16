<template>
  <section class="page-stack">
    <GraphStatsCards
      id="stats"
      :base-url="baseUrl"
      :refresh-key="refreshKey"
      @status-change="$emit('status-change', $event)"
    />

    <OverviewGraphPanel
      id="overview"
      :base-url="baseUrl"
      :refresh-key="refreshKey"
    />

    <RecordGraphPanel
      id="record-graph"
      :base-url="baseUrl"
      :refresh-key="refreshKey"
    />

    <PlaceFlowTable
      id="place-flows"
      :base-url="baseUrl"
      :refresh-key="refreshKey"
    />

    <NodeNeighborPanel
      id="node-neighbors"
      :base-url="baseUrl"
      :refresh-key="refreshKey"
    />
  </section>
</template>

<script setup>
import GraphStatsCards from '../components/GraphStatsCards.vue'
import NodeNeighborPanel from '../components/NodeNeighborPanel.vue'
import OverviewGraphPanel from '../components/OverviewGraphPanel.vue'
import PlaceFlowTable from '../components/PlaceFlowTable.vue'
import RecordGraphPanel from '../components/RecordGraphPanel.vue'

defineProps({
  baseUrl: {
    type: String,
    required: true
  },
  refreshKey: {
    type: Number,
    required: true
  }
})

defineEmits(['status-change'])
</script>
