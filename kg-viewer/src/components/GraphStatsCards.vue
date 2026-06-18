<template>
  <section class="section-stack">
    <div class="panel-heading-row">
      <div>
        <h2>图谱统计</h2>
        <p class="panel-meta">SQLite 知识图谱表</p>
      </div>
      <el-button size="small" :loading="loading" @click="loadStats">
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

    <div v-loading="loading" class="stat-grid">
      <section class="stat-card tone-red">
        <div class="stat-label">节点总数</div>
        <div class="stat-value">{{ numberText(stats.node_count) }}</div>
        <div class="stat-caption">qiaopi_kg_nodes</div>
      </section>
      <section class="stat-card tone-blue">
        <div class="stat-label">关系总数</div>
        <div class="stat-value">{{ numberText(stats.edge_count) }}</div>
        <div class="stat-caption">qiaopi_kg_edges</div>
      </section>
      <section class="stat-card tone-teal">
        <div class="stat-label">节点类型</div>
        <div class="stat-value">{{ nodeDistribution.length }}</div>
        <div class="stat-caption">已构建类别</div>
      </section>
      <section class="stat-card tone-gold">
        <div class="stat-label">关系类型</div>
        <div class="stat-value">{{ edgeDistribution.length }}</div>
        <div class="stat-caption">关系语义</div>
      </section>
    </div>

    <div class="distribution-grid">
      <section class="chart-panel">
        <div class="panel-heading-row compact">
          <h3>节点类型分布</h3>
          <el-tag effect="plain">{{ nodeDistribution.length }}</el-tag>
        </div>
        <div v-if="nodeDistribution.length" class="distribution-list">
          <div v-for="item in nodeDistribution" :key="item.rawLabel" class="distribution-row">
            <span>{{ item.label }}</span>
            <strong>{{ numberText(item.value) }}</strong>
          </div>
        </div>
        <el-empty v-else :image-size="80" description="暂无节点统计" />
      </section>

      <section class="chart-panel">
        <div class="panel-heading-row compact">
          <h3>关系类型分布</h3>
          <el-tag effect="plain">{{ edgeDistribution.length }}</el-tag>
        </div>
        <div v-if="edgeDistribution.length" class="distribution-list">
          <div v-for="item in edgeDistribution" :key="item.rawLabel" class="distribution-row">
            <span>{{ item.label }}</span>
            <strong>{{ numberText(item.value) }}</strong>
          </div>
        </div>
        <el-empty v-else :image-size="80" description="暂无关系统计" />
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import { getGraphStats } from '../api/graphApi'

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

const emit = defineEmits(['status-change'])

const stats = ref({
  node_count: 0,
  edge_count: 0,
  node_type_distribution: {},
  edge_type_distribution: {}
})
const loading = ref(false)
const error = ref('')

const nodeDistribution = computed(() => toDistribution(stats.value.node_type_distribution))
const edgeDistribution = computed(() => toDistribution(stats.value.edge_type_distribution, EDGE_TYPE_LABELS))

const NODE_TYPE_LABELS = {
  record: '批信',
  metadata_record: '目录记录',
  person: '人物',
  place: '地点',
  amount: '款项',
  date: '日期',
  theme: '主题',
  evidence: '证据'
}

const EDGE_TYPE_LABELS = {
  SENT_BY: '寄信人',
  RECEIVED_BY: '收信人',
  MENTIONS_PERSON: '提及人物',
  MENTIONS_PLACE: '提及地点',
  SENT_FROM: '寄出地',
  SENT_TO: '寄达地',
  HAS_AMOUNT: '款项',
  HAS_DATE: '日期',
  HAS_THEME: '主题',
  SUPPORTED_BY: '证据支持',
  LINKED_TO_METADATA: '目录链接'
}

function numberText(value) {
  return Number(value || 0).toLocaleString()
}

function toDistribution(distribution, labelMap = NODE_TYPE_LABELS) {
  return Object.entries(distribution || {})
    .map(([rawLabel, value]) => ({ rawLabel, label: labelMap[rawLabel] || rawLabel, value }))
    .sort((a, b) => Number(b.value) - Number(a.value))
}

async function loadStats() {
  loading.value = true
  error.value = ''
  emit('status-change', 'checking')
  try {
    stats.value = await getGraphStats(props.baseUrl)
    emit('status-change', 'ok')
  } catch (requestError) {
    error.value = `图谱统计暂不可用：${requestError.message}`
    emit('status-change', 'error')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.baseUrl, props.refreshKey],
  () => loadStats()
)

onMounted(loadStats)
</script>
