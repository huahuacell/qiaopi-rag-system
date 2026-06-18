<template>
  <section class="chart-panel">
    <div class="panel-heading-row">
      <div>
        <h2>地点流向</h2>
        <p class="panel-meta">{{ flowSummary }}</p>
      </div>
      <div class="panel-controls">
        <el-input-number v-model="limit" size="small" :min="1" :max="200" controls-position="right" />
        <el-button size="small" :loading="loading" @click="loadFlows">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
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

    <el-table
      v-loading="loading"
      :data="flows"
      class="flow-table"
      empty-text="暂无地点流向"
      stripe
    >
      <el-table-column prop="origin_place" label="出发地" min-width="160" />
      <el-table-column prop="destination_place" label="目的地" min-width="180" />
      <el-table-column prop="count" label="数量" width="90" sortable />
      <el-table-column label="样例批信" min-width="260">
        <template #default="{ row }">
          <div class="sample-records">
            <el-tag
              v-for="recordId in row.record_ids_sample"
              :key="recordId"
              size="small"
              effect="plain"
            >
              {{ recordId }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import { getPlaceFlows } from '../api/graphApi'

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

const flows = ref([])
const limit = ref(50)
const loading = ref(false)
const error = ref('')

const flowSummary = computed(() => `${flows.value.length} 组出发地与目的地`)

async function loadFlows() {
  loading.value = true
  error.value = ''
  try {
    const payload = await getPlaceFlows(props.baseUrl, limit.value)
    flows.value = payload.flows || []
  } catch (requestError) {
    flows.value = []
    error.value = `地点流向暂不可用：${requestError.message}`
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.baseUrl, props.refreshKey],
  () => loadFlows()
)

onMounted(loadFlows)
</script>
