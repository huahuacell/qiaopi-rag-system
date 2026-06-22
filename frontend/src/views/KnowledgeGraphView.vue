<template>
  <section class="kg-product-page">
    <header class="kg-product-hero">
      <div>
        <p>KNOWLEDGE GRAPH · 正式产品链路</p>
        <h1>侨批关系图谱与来源追溯</h1>
        <span>
          图谱节点来自 SQLite 派生表。点击人物、地点、金额、证据或目录节点，
          可追溯到原始记录、证据片段和元数据来源。
        </span>
      </div>
      <div class="kg-product-owner">
        <small>正式产品</small>
        <strong>frontend/</strong>
        <em>独立 kg-viewer/ 仅作诊断沙盒</em>
      </div>
    </header>

    <el-alert
      v-if="error"
      :title="error"
      :type="demoMode ? 'warning' : 'error'"
      show-icon
      :closable="false"
      class="kg-product-alert"
    />

    <section class="kg-stat-grid" v-loading="statsLoading">
      <article>
        <span>图谱节点</span>
        <strong>{{ formatNumber(stats.node_count) }}</strong>
        <small>{{ formatDistribution(stats.node_type_distribution) }}</small>
      </article>
      <article>
        <span>图谱关系</span>
        <strong>{{ formatNumber(stats.edge_count) }}</strong>
        <small>{{ formatDistribution(stats.edge_type_distribution) }}</small>
      </article>
      <article>
        <span>可追溯证据节点</span>
        <strong>{{ formatNumber(stats.quality?.traceable_evidence_node_count) }}</strong>
        <small>来源：qiaopi_evidence_spans</small>
      </article>
      <article :class="{ warning: !qualityState.healthy }">
        <span>构建质量</span>
        <strong>{{ qualityState.healthy ? '通过' : qualityState.failureCount }}</strong>
        <small>{{ qualityState.label }}</small>
      </article>
    </section>

    <div class="kg-product-layout">
      <main class="kg-product-main">
        <section class="kg-graph-card">
          <header class="kg-card-heading">
            <div>
              <h2>{{ graphTitle }}</h2>
              <p>{{ displayGraph.nodes.length }} 个节点 / {{ displayGraph.edges.length }} 条关系</p>
            </div>
            <div class="kg-graph-controls">
              <el-switch
                v-model="showEvidenceNodes"
                active-text="显示证据节点"
              />
              <el-input
                v-model="recordId"
                placeholder="输入 record_id"
                @keyup.enter="loadRecordGraph"
              />
              <el-button type="primary" :loading="graphLoading" @click="loadRecordGraph">
                记录子图
              </el-button>
              <el-button :loading="graphLoading" @click="loadOverviewGraph">
                全局概览
              </el-button>
            </div>
          </header>

          <div v-loading="graphLoading">
            <KnowledgeGraphCanvas
              :nodes="displayGraph.nodes"
              :edges="displayGraph.edges"
              :selected-node-id="selectedNode?.id || ''"
              @select-node="selectNode"
              @select-edge="selectEdge"
            />
          </div>

          <div class="kg-node-index" aria-label="当前图谱节点索引">
            <button
              v-for="node in nodeIndex"
              :key="node.id"
              type="button"
              :class="{ active: selectedNode?.id === node.id }"
              @click="selectNode(node)"
            >
              <span>{{ nodeTypeLabel(node) }}</span>
              {{ nodeDisplayLabel(node) }}
            </button>
          </div>

          <footer class="kg-graph-legend-note">
            图中关系线宽仅表示边置信度。目录元数据用于浏览和关联，不作为全文 RAG 证据。
          </footer>
        </section>

        <section class="kg-flow-card">
          <header class="kg-card-heading">
            <div>
              <h2>侨批地点流向</h2>
              <p>由记录节点的 SENT_FROM / SENT_TO 关系聚合</p>
            </div>
          </header>
          <el-table :data="placeFlows" v-loading="flowsLoading" size="small">
            <el-table-column prop="origin_place" label="来源地" min-width="130" />
            <el-table-column prop="destination_place" label="目的地" min-width="130" />
            <el-table-column prop="count" label="记录数" width="90" />
            <el-table-column label="记录追溯" min-width="260">
              <template #default="{ row }">
                <router-link
                  v-for="record in row.record_ids_sample"
                  :key="record"
                  class="kg-inline-link"
                  :to="`/records/${record}`"
                >
                  {{ record }}
                </router-link>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </main>

      <aside class="kg-trace-panel">
        <header>
          <span>TRACE</span>
          <h2>节点来源追溯</h2>
        </header>

        <div v-if="!selectedNode && !selectedEdge" class="kg-trace-empty">
          点击图中的节点或关系，查看来源记录、证据和元数据。
        </div>

        <template v-else-if="selectedNode">
          <section class="kg-trace-identity">
            <el-tag effect="plain">{{ nodeTypeLabel(selectedNode) }}</el-tag>
            <h3>{{ nodeDisplayLabel(selectedNode) }}</h3>
            <code>{{ selectedNode.id }}</code>
            <dl>
              <div>
                <dt>来源表</dt>
                <dd>{{ selectedNode.source_table || '—' }}</dd>
              </div>
              <div>
                <dt>来源 ID</dt>
                <dd>{{ selectedNode.source_id || '—' }}</dd>
              </div>
              <div>
                <dt>关联记录</dt>
                <dd>{{ selectedNode.record_id || '全局共享节点' }}</dd>
              </div>
            </dl>
          </section>

          <section v-loading="traceLoading" class="kg-trace-section">
            <h3>关联侨批记录</h3>
            <div v-if="relatedRecordIds.length" class="kg-record-links">
              <router-link
                v-for="relatedRecordId in relatedRecordIds"
                :key="relatedRecordId"
                :to="`/records/${relatedRecordId}`"
              >
                {{ relatedRecordId }}
                <span>查看记录与证据 →</span>
              </router-link>
            </div>
            <p v-else>该节点当前没有可追溯的全文记录。</p>
          </section>

          <section v-if="sourceDetail" class="kg-trace-section">
            <h3>{{ sourceDetail.title }}</h3>
            <dl class="kg-source-detail">
              <div v-for="item in sourceDetail.items" :key="item.label">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value || '—' }}</dd>
              </div>
            </dl>
            <router-link
              v-if="sourceDetail.recordId"
              class="kg-primary-link"
              :to="`/records/${sourceDetail.recordId}`"
            >
              打开正式记录详情
            </router-link>
          </section>

          <section class="kg-trace-section">
            <h3>关系证据</h3>
            <div v-if="evidenceTraces.length" class="kg-evidence-traces">
              <article v-for="(trace, index) in evidenceTraces" :key="`${trace.sourceId}-${index}`">
                <strong>{{ trace.relation }}</strong>
                <p>{{ trace.text }}</p>
                <small>
                  {{ trace.recordId || '无记录 ID' }} ·
                  {{ trace.sourceTable || '未知来源表' }} ·
                  {{ trace.sourceId || '无来源 ID' }}
                </small>
              </article>
            </div>
            <p v-else>该节点邻居关系未返回文本证据。</p>
          </section>
        </template>

        <section v-else class="kg-trace-section">
          <h3>{{ edgeTypeLabel(selectedEdge) }}</h3>
          <p>{{ selectedEdge.evidence_text || '该关系没有单独的文本证据。' }}</p>
          <dl class="kg-source-detail">
            <div>
              <dt>来源表</dt>
              <dd>{{ selectedEdge.source_table || '—' }}</dd>
            </div>
            <div>
              <dt>来源 ID</dt>
              <dd>{{ selectedEdge.source_id || '—' }}</dd>
            </div>
            <div>
              <dt>记录 ID</dt>
              <dd>{{ selectedEdge.record_id || '—' }}</dd>
            </div>
          </dl>
          <router-link
            v-if="selectedEdge.record_id"
            class="kg-primary-link"
            :to="`/records/${selectedEdge.record_id}`"
          >
            查看关系所属记录
          </router-link>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import {
  fetchGraphOverview,
  fetchGraphStats,
  fetchNodeNeighbors,
  fetchPlaceFlows,
  fetchRecordGraph
} from '../api/graph'
import { fetchMetadataDetail, fetchMetadataLinkedText } from '../api/metadata'
import { fetchRecordDetail, fetchRecordEvidence } from '../api/records'
import KnowledgeGraphCanvas from '../components/KnowledgeGraphCanvas.vue'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import {
  buildFallbackNeighborGraph,
  buildFallbackRecordGraph,
  buildFallbackSourceDetail
} from '../utils/graphFallback'
import {
  edgeTypeLabel,
  evidenceIdFromNode,
  evidenceTracesFromGraph,
  filterGraph,
  graphQualityState,
  metadataIdFromNode,
  nodeDisplayLabel,
  nodeType,
  nodeTypeLabel,
  recordIdsFromGraph
} from '../utils/graphPresentation'

const recordId = ref('CSQP-SFHC-TEXT-063')
const stats = ref({})
const graph = ref({ nodes: [], edges: [] })
const graphMode = ref('record')
const placeFlows = ref([])
const selectedNode = ref(null)
const selectedEdge = ref(null)
const neighborGraph = ref({ nodes: [], edges: [] })
const relatedRecordIds = ref([])
const evidenceTraces = ref([])
const sourceDetail = ref(null)
const showEvidenceNodes = ref(true)
const statsLoading = ref(false)
const graphLoading = ref(false)
const flowsLoading = ref(false)
const traceLoading = ref(false)
const error = ref('')
let traceRequestId = 0

const displayGraph = computed(() => filterGraph(graph.value, showEvidenceNodes.value))
const nodeIndex = computed(() => {
  const priorities = {
    record: 1,
    metadata_record: 2,
    evidence: 3,
    person: 4,
    place: 5,
    amount: 6,
    date: 7,
    theme: 8
  }
  return [...displayGraph.value.nodes]
    .sort(
      (left, right) =>
        (priorities[nodeType(left)] || 99) - (priorities[nodeType(right)] || 99)
    )
    .slice(0, 36)
})
const qualityState = computed(() => graphQualityState(stats.value.quality))
const graphTitle = computed(() =>
  graphMode.value === 'record'
    ? `记录子图 · ${recordId.value}`
    : '全局关系概览'
)

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatDistribution(distribution = {}) {
  const entries = Object.entries(distribution)
  if (!entries.length) return '暂无分布'
  return entries
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3)
    .map(([label, count]) => `${label} ${count}`)
    .join(' · ')
}

async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await fetchGraphStats()
  } catch (requestError) {
    error.value = apiFailureMessage(requestError, '图谱统计请求')
  } finally {
    statsLoading.value = false
  }
}

async function loadFlows() {
  flowsLoading.value = true
  try {
    const response = await fetchPlaceFlows(30)
    placeFlows.value = response.flows || []
  } catch (requestError) {
    error.value = apiFailureMessage(requestError, '地点流向请求')
  } finally {
    flowsLoading.value = false
  }
}

async function loadRecordGraph() {
  const value = recordId.value.trim()
  if (!value) return
  graphLoading.value = true
  error.value = ''
  clearSelection()
  try {
    graph.value = await fetchRecordGraph(value)
    graphMode.value = 'record'
    const recordNode = graph.value.nodes?.find((node) => nodeType(node) === 'record')
    if (recordNode) await selectNode(recordNode)
  } catch (requestError) {
    if (demoMode) {
      graph.value = buildFallbackRecordGraph(value)
      graphMode.value = 'record'
      error.value = demoFailureMessage('记录子图请求')
      const recordNode = graph.value.nodes.find((node) => nodeType(node) === 'record')
      if (recordNode) await selectNode(recordNode)
    } else {
      graph.value = { nodes: [], edges: [] }
      error.value = apiFailureMessage(requestError, '记录子图请求')
    }
  } finally {
    graphLoading.value = false
  }
}

async function loadOverviewGraph() {
  graphLoading.value = true
  error.value = ''
  clearSelection()
  try {
    graph.value = await fetchGraphOverview({ limitNodes: 90, limitEdges: 160 })
    graphMode.value = 'overview'
  } catch (requestError) {
    graph.value = { nodes: [], edges: [] }
    error.value = apiFailureMessage(requestError, '图谱概览请求')
  } finally {
    graphLoading.value = false
  }
}

function clearSelection() {
  selectedNode.value = null
  selectedEdge.value = null
  neighborGraph.value = { nodes: [], edges: [] }
  relatedRecordIds.value = []
  evidenceTraces.value = []
  sourceDetail.value = null
}

async function selectNode(node) {
  const requestId = ++traceRequestId
  selectedNode.value = node
  selectedEdge.value = null
  traceLoading.value = true
  sourceDetail.value = null
  try {
    const neighbors = await fetchNodeNeighbors(node.id, { depth: 1, limit: 100 })
    if (requestId !== traceRequestId) return
    applyNeighborGraph(node, neighbors)
    try {
      const detail = await loadDirectSourceWithFallback(node)
      if (requestId !== traceRequestId) return
      sourceDetail.value = detail
    } catch (sourceError) {
      if (requestId !== traceRequestId) return
      sourceDetail.value = null
      error.value = apiFailureMessage(sourceError, '节点源数据请求')
    }
  } catch (requestError) {
    if (requestId !== traceRequestId) return
    const fallbackNeighbors = demoMode
      ? buildFallbackNeighborGraph(node.id, graph.value)
      : null
    if (fallbackNeighbors) {
      applyNeighborGraph(node, fallbackNeighbors)
      sourceDetail.value = await loadDirectSourceWithFallback(node)
      if (!error.value) error.value = demoFailureMessage('节点追溯请求')
    } else {
      neighborGraph.value = { nodes: [], edges: [] }
      relatedRecordIds.value = recordIdsFromGraph(node, {})
      evidenceTraces.value = []
      error.value = apiFailureMessage(requestError, '节点追溯请求')
    }
  } finally {
    if (requestId === traceRequestId) traceLoading.value = false
  }
}

function applyNeighborGraph(node, neighbors) {
  neighborGraph.value = neighbors
  relatedRecordIds.value = recordIdsFromGraph(node, neighbors)
  evidenceTraces.value = evidenceTracesFromGraph(neighbors)
}

function selectEdge(edge) {
  traceRequestId += 1
  selectedEdge.value = edge
  selectedNode.value = null
  relatedRecordIds.value = edge.record_id ? [edge.record_id] : []
  evidenceTraces.value = []
  sourceDetail.value = null
  traceLoading.value = false
}

async function loadDirectSource(node) {
  if (nodeType(node) === 'record') {
    const activeRecordId = node.record_id || node.id.replace(/^record:/, '')
    const detail = await fetchRecordDetail(activeRecordId)
    return {
      title: '记录源数据',
      recordId: activeRecordId,
      items: [
        { label: '题名', value: detail.title_reference || detail.title },
        { label: '寄批人', value: detail.sender },
        { label: '收批人', value: detail.recipient },
        { label: '日期', value: detail.date_text || detail.date_standard }
      ]
    }
  }

  if (nodeType(node) === 'evidence' && node.record_id) {
    const response = await fetchRecordEvidence(node.record_id)
    const evidenceId = evidenceIdFromNode(node)
    const evidence = (response.evidence || []).find(
      (item) => item.evidence_id === evidenceId
    )
    if (!evidence) return null
    return {
      title: '原始证据片段',
      recordId: node.record_id,
      items: [
        { label: '证据 ID', value: evidence.evidence_id },
        { label: '证据类型', value: evidence.evidence_type },
        { label: '来源字段', value: evidence.source_column },
        { label: '原文', value: evidence.evidence_text }
      ]
    }
  }

  if (nodeType(node) === 'metadata_record') {
    const metadataId = metadataIdFromNode(node)
    const [detail, linked] = await Promise.all([
      fetchMetadataDetail(metadataId),
      fetchMetadataLinkedText(metadataId)
    ])
    return {
      title: '目录元数据',
      recordId: linked.linked_record_id || '',
      items: [
        { label: '元数据 ID', value: metadataId },
        { label: '题名', value: detail.title_clean || detail.title_raw },
        { label: '寄件人', value: detail.sender_raw },
        { label: '收件人', value: detail.recipient_raw },
        { label: '日期', value: detail.date_text || detail.date_standard },
        { label: '全文关联', value: linked.linked_record_id || '未关联全文' }
      ]
    }
  }
  return null
}

async function loadDirectSourceWithFallback(node) {
  try {
    return await loadDirectSource(node)
  } catch (requestError) {
    if (!demoMode) throw requestError
    if (!error.value) error.value = demoFailureMessage('节点源数据请求')
    return buildFallbackSourceDetail(node)
  }
}

onMounted(async () => {
  await Promise.all([loadStats(), loadFlows(), loadRecordGraph()])
})
</script>
