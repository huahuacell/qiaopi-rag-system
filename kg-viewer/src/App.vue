<template>
  <AppShell
    v-model:base-url="baseUrl"
    :backend-status="backendStatus"
    :refreshing="refreshing"
    @refresh="refreshAll"
  >
    <KnowledgeGraphView
      :base-url="baseUrl"
      :refresh-key="refreshKey"
      @status-change="handleStatusChange"
    />
  </AppShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import AppShell from './components/AppShell.vue'
import KnowledgeGraphView from './views/KnowledgeGraphView.vue'

const savedBaseUrl = window.localStorage.getItem('kg-viewer-api-base-url')
const baseUrl = ref(savedBaseUrl || 'http://localhost:8000')
const refreshKey = ref(0)
const status = ref('checking')
const refreshing = ref(false)

const backendStatus = computed(() => status.value)

watch(baseUrl, (value) => {
  window.localStorage.setItem('kg-viewer-api-base-url', value)
})

function refreshAll() {
  refreshing.value = true
  status.value = 'checking'
  refreshKey.value += 1
  window.setTimeout(() => {
    refreshing.value = false
  }, 500)
}

function handleStatusChange(nextStatus) {
  status.value = nextStatus
  refreshing.value = false
}
</script>
