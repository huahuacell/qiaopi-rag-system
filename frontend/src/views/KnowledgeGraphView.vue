<template>
  <section class="kg-product-page">
    <header class="kg-product-hero">
      <div class="kg-hero-seal" aria-hidden="true">侨批</div>
      <div>
        <p>侨批数字档案馆 · 关系与信路</p>
        <h1>侨批关系图谱与来源追溯</h1>
        <span>
          从人物亲缘、书信往来与跨海侨汇中阅读侨批，并以原文片段保留每一条关系的来源。
        </span>
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
        <span>图谱节点数</span>
        <strong>{{ formatNumber(stats.node_count) }}</strong>
        <small>{{ formatDistribution(stats.node_type_distribution, 'node') }}</small>
      </article>
      <article>
        <span>图谱关系数</span>
        <strong>{{ formatNumber(stats.edge_count) }}</strong>
        <small>{{ formatDistribution(stats.edge_type_distribution, 'edge') }}</small>
      </article>
      <article>
        <span>可追溯证据数</span>
        <strong>{{ formatNumber(stats.quality?.traceable_evidence_node_count) }}</strong>
        <small>原文摘录均可回到所属侨批记录</small>
      </article>
      <article :class="{ warning: !qualityState.healthy }">
        <span>构建质量状态</span>
        <strong>{{ qualityState.healthy ? '通过' : '待核' }}</strong>
        <small>{{ qualityState.label }}</small>
      </article>
    </section>

    <div class="kg-product-layout">
      <main class="kg-product-main">
        <section ref="graphCardRef" class="kg-graph-card">
          <header class="kg-card-heading kg-graph-heading">
            <div>
              <span class="kg-section-kicker">档案关系视图</span>
              <h2>{{ graphTitle }}</h2>
              <p>{{ graphDescription }}</p>
            </div>
            <div class="kg-visible-count">
              <strong>{{ displayGraph.nodes.length }}</strong>
              <span>节点</span>
              <i></i>
              <strong>{{ displayGraph.edges.length }}</strong>
              <span>关系</span>
            </div>
          </header>

          <nav class="kg-view-tabs" aria-label="图谱视图切换">
            <button
              type="button"
              :class="{ active: currentView === 'kinship' }"
              @click="switchView('kinship')"
            >
              <span>人物与称谓</span>
              亲缘通信图谱
            </button>
            <button
              type="button"
              :class="{ active: currentView === 'flow' }"
              @click="switchView('flow')"
            >
              <span>海外与侨乡</span>
              侨批流动图谱
            </button>
            <button
              type="button"
              class="record-drill-tab"
              :class="{ active: currentView === 'record' }"
              @click="switchToRecord(recordId)"
            >
              <span>证据钻取</span>
              单封记录子图
            </button>
          </nav>

          <div class="kg-filter-bar">
            <el-input
              v-model="searchQuery"
              clearable
              placeholder="搜索人物、地点、记录编号或主题"
              @keyup.enter="focusSearchResult"
            />
            <el-select v-model="themeFilter" clearable placeholder="全部主题">
              <el-option
                v-for="option in filterOptions.themes"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
            <el-select v-model="yearFilter" clearable placeholder="全部年份">
              <el-option
                v-for="year in filterOptions.years"
                :key="year"
                :label="`${year} 年`"
                :value="year"
              />
            </el-select>
            <label class="kg-evidence-toggle">
              <input v-model="evidenceOnly" type="checkbox" />
              <span>只看有证据关系</span>
            </label>
            <div class="kg-toolbar-actions">
              <button type="button" @click="resetGraphView">重置视图</button>
              <button type="button" @click="expandGraph">展开相关记录</button>
              <button type="button" @click="exportGraphImage">导出截图</button>
            </div>
          </div>

          <div v-if="currentView === 'record'" class="kg-record-drill-bar">
            <span>侨批编号</span>
            <el-input
              v-model="recordId"
              placeholder="输入记录编号"
              @keyup.enter="switchToRecord(recordId)"
            />
            <el-button :loading="graphLoading" @click="switchToRecord(recordId)">
              调取证据子图
            </el-button>
          </div>

          <div v-loading="graphLoading" class="kg-canvas-wrap">
            <Transition name="kg-graph-fade" mode="out-in">
              <KnowledgeGraphCanvas
                :key="currentView"
                ref="canvasRef"
                :nodes="displayGraph.nodes"
                :edges="displayGraph.edges"
                :view-mode="currentView"
                :selected-node-id="selectedNode?.id || ''"
                :selected-edge-id="selectedEdge?.id || ''"
                @select-node="selectNode"
                @select-edge="selectEdge"
              />
            </Transition>
          </div>

          <footer class="kg-graph-footer">
            <div class="kg-mini-legend">
              <span v-for="item in activeLegend" :key="item.type">
                <i :style="{ background: item.color }"></i>{{ item.label }}
              </span>
            </div>
            <p>
              节点仅显示简短中文名称；完整原文、技术代码与来源字段收纳在右侧证据卡中。
            </p>
          </footer>
        </section>
      </main>

      <aside
        class="kg-trace-panel"
        :style="tracePanelHeight ? { height: `${tracePanelHeight}px` } : undefined"
      >
        <header>
          <span>可信证据链</span>
          <h2>档案证据卡</h2>
          <p>点击节点或信路，阅读其关联记录与原文依据。</p>
        </header>

        <div v-if="!selectedNode && !selectedEdge" class="kg-trace-empty">
          <div aria-hidden="true">据</div>
          <strong>等待选择一条档案线索</strong>
          <p>可从人物、亲属称谓、地点、金额、主题或流动边开始。</p>
        </div>

        <template v-else>
          <section class="kg-trace-identity">
            <div class="kg-trace-title-row">
              <span>{{ selectedTypeLabel }}</span>
              <em>{{ evidenceStatus }}</em>
            </div>
            <h3>{{ selectedDisplayLabel }}</h3>
            <p v-if="selectedSecondaryCode">{{ selectedSecondaryCode }}</p>
          </section>

          <section class="kg-trace-section kg-basic-facts">
            <h3>档案摘要</h3>
            <dl>
              <div>
                <dt>相关侨批</dt>
                <dd>{{ selectedContext.recordIds.length || '暂无' }}</dd>
              </div>
              <div>
                <dt>主题</dt>
                <dd>{{ joinedValue(selectedContext.themes, '暂无主题标注') }}</dd>
              </div>
              <div>
                <dt>地点</dt>
                <dd>{{ joinedValue(selectedContext.places, '未知地点') }}</dd>
              </div>
              <div>
                <dt>金额</dt>
                <dd>{{ joinedValue(selectedContext.amounts, '未标注金额') }}</dd>
              </div>
              <div v-if="selectedFlowSummary">
                <dt>信路</dt>
                <dd>{{ selectedFlowSummary }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="sourceDetail" class="kg-trace-section">
            <h3>{{ sourceDetail.title }}</h3>
            <dl class="kg-source-detail">
              <div v-for="item in sourceDetail.items" :key="item.label">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value || '暂无标注' }}</dd>
              </div>
            </dl>
          </section>

          <section v-loading="traceLoading" class="kg-trace-section">
            <div class="kg-section-title-row">
              <h3>原文证据</h3>
              <span>{{ mergedEvidence.length }} 条</span>
            </div>
            <div v-if="mergedEvidence.length" class="kg-evidence-traces">
              <button
                v-for="(trace, index) in mergedEvidence"
                :key="`${trace.sourceId}-${trace.recordId}-${index}`"
                type="button"
                @click="trace.recordId && switchToRecord(trace.recordId)"
              >
                <span>{{ trace.relation || '证据支持' }}</span>
                <blockquote>{{ trace.text }}</blockquote>
                <small>
                  {{ trace.recordId || '无记录编号' }}
                  <template v-if="trace.sourceTable"> · {{ trace.sourceTable }}</template>
                </small>
              </button>
            </div>
            <p v-else>暂无可直接展示的原文片段，可进入相关侨批继续核查。</p>
          </section>

          <section class="kg-trace-section">
            <div class="kg-section-title-row">
              <h3>相关侨批</h3>
              <span>{{ selectedContext.recordIds.length }} 封</span>
            </div>
            <div v-if="selectedContext.recordIds.length" class="kg-record-links">
              <button
                v-for="relatedRecordId in selectedContext.recordIds.slice(0, 10)"
                :key="relatedRecordId"
                type="button"
                @click="switchToRecord(relatedRecordId)"
              >
                <strong>{{ relatedRecordId }}</strong>
                <span>{{ recordSummary(relatedRecordId) }}</span>
                <em>查看证据子图 →</em>
              </button>
            </div>
            <p v-else>该线索当前没有可追溯的全文记录。</p>
          </section>

          <details class="kg-technical-details">
            <summary>来源字段与技术标识</summary>
            <dl>
              <div>
                <dt>来源表</dt>
                <dd>{{ selectedItem.source_table || '派生展示关系' }}</dd>
              </div>
              <div>
                <dt>来源编号</dt>
                <dd>{{ selectedItem.source_id || selectedItem.id || '—' }}</dd>
              </div>
              <div v-if="selectedItem.rawType || selectedItem.type">
                <dt>原始代码</dt>
                <dd>{{ selectedItem.rawType || selectedItem.type }}</dd>
              </div>
            </dl>
          </details>
        </template>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

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
  EDGE_TYPE_LABELS,
  NODE_COLORS,
  NODE_TYPE_LABELS,
  edgeTypeLabel,
  evidenceIdFromNode,
  evidenceTracesFromGraph,
  graphQualityState,
  metadataIdFromNode,
  nodeDisplayLabel,
  nodeType,
  nodeTypeLabel
} from '../utils/graphPresentation'
import {
  getNodeTypeDisplay,
  getRelationDisplay,
  getThemeDisplay
} from '../utils/graphLabelMap'
import {
  filterTransformedGraph,
  graphFilterOptions,
  selectedGraphContext,
  transformGraphForFlow,
  transformGraphForKinshipCommunication,
  transformGraphForRecord
} from '../utils/graphTransforms'

const recordId = ref('CSQP-SFHC-TEXT-063')
const stats = ref({})
const overviewGraph = ref({ nodes: [], edges: [] })
const recordGraph = ref({ nodes: [], edges: [] })
const placeFlows = ref([])
const currentView = ref('kinship')
const selectedNode = ref(null)
const selectedEdge = ref(null)
const neighborGraph = ref({ nodes: [], edges: [] })
const neighborEvidence = ref([])
const sourceDetail = ref(null)
const recordSummaries = ref({})
const searchQuery = ref('')
const themeFilter = ref('')
const yearFilter = ref('')
const evidenceOnly = ref(false)
const nodeLimit = ref(36)
const statsLoading = ref(false)
const graphLoading = ref(false)
const traceLoading = ref(false)
const error = ref('')
const canvasRef = ref(null)
const graphCardRef = ref(null)
const tracePanelHeight = ref(0)
let traceRequestId = 0
let graphCardResizeObserver

const qualityState = computed(() => graphQualityState(stats.value.quality))
const filterOptions = computed(() =>
  graphFilterOptions({
    nodes: [...(overviewGraph.value.nodes || []), ...(recordGraph.value.nodes || [])],
    edges: [...(overviewGraph.value.edges || []), ...(recordGraph.value.edges || [])]
  })
)
const transformedGraph = computed(() => {
  if (currentView.value === 'flow') {
    return transformGraphForFlow(overviewGraph.value, placeFlows.value, {
      maxFlows: nodeLimit.value > 64 ? 22 : 14
    })
  }
  if (currentView.value === 'record') {
    return transformGraphForRecord(recordGraph.value)
  }
  return transformGraphForKinshipCommunication(overviewGraph.value, {
    maxNodes: nodeLimit.value + 24
  })
})
const displayGraph = computed(() =>
  filterTransformedGraph(transformedGraph.value, {
    query: searchQuery.value,
    theme: themeFilter.value,
    year: yearFilter.value,
    evidenceOnly: evidenceOnly.value
  })
)
const selectedItem = computed(() => selectedNode.value || selectedEdge.value || {})
const selectedContext = computed(() => {
  const local = selectedGraphContext(selectedItem.value, transformedGraph.value)
  const neighbor = selectedGraphContext(selectedItem.value, {
    nodes: neighborGraph.value.nodes || [],
    edges: neighborGraph.value.edges || []
  })
  return {
    recordIds: unique([...local.recordIds, ...neighbor.recordIds]),
    themes: unique([...local.themes, ...neighbor.themes]),
    places: unique([...local.places, ...neighbor.places]),
    amounts: unique([...local.amounts, ...neighbor.amounts]),
    evidence: [...local.evidence, ...neighbor.evidence],
    relatedNodes: [...local.relatedNodes, ...neighbor.relatedNodes]
  }
})
const mergedEvidence = computed(() =>
  uniqueEvidence([...selectedContext.value.evidence, ...neighborEvidence.value]).slice(0, 20)
)
const graphTitle = computed(() => {
  if (currentView.value === 'flow') return '侨批流动时空图谱'
  if (currentView.value === 'record') return `单封记录证据子图 · ${recordId.value}`
  return '亲缘通信图谱'
})
const graphDescription = computed(() => {
  if (currentView.value === 'flow') {
    return '以海外侨居地、侨批记录与侨乡家园呈现跨海书信和侨汇流向。'
  }
  if (currentView.value === 'record') {
    return '保留单封侨批的完整字段与证据节点，作为关系网络的钻取层。'
  }
  return '人物居中、称谓相伴，串联写信、收信、寄款与主题语境。'
})
const selectedTypeLabel = computed(() =>
  selectedNode.value ? nodeTypeLabel(selectedNode.value) : edgeTypeLabel(selectedEdge.value)
)
const selectedDisplayLabel = computed(() =>
  selectedNode.value
    ? nodeDisplayLabel(selectedNode.value)
    : edgeTypeLabel(selectedEdge.value)
)
const selectedSecondaryCode = computed(() => {
  if (selectedNode.value?.visualType === 'theme' && selectedNode.value.themeCode) {
    return `主题代码：${selectedNode.value.themeCode}`
  }
  return ''
})
const evidenceStatus = computed(() =>
  mergedEvidence.value.length ? '有原文证据支持' : '待补充原文证据'
)
const selectedFlowSummary = computed(() => {
  const properties = selectedItem.value.properties || {}
  if (!properties.origin_place && !properties.destination_place) return ''
  return `${properties.origin_place || '未知海外地点'} → ${
    properties.destination_place || '未知侨乡'
  }`
})
const activeLegend = computed(() => {
  const types =
    currentView.value === 'flow'
      ? ['overseas_place', 'record', 'hometown_place']
      : currentView.value === 'record'
        ? ['record', 'person', 'kinship', 'place', 'amount', 'theme', 'evidence']
        : ['person', 'kinship', 'record', 'amount', 'theme', 'place']
  return types.map((type) => ({
    type,
    label: NODE_TYPE_LABELS[type],
    color: NODE_COLORS[type]
  }))
})

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatDistribution(distribution = {}, kind) {
  const entries = Object.entries(distribution)
  if (!entries.length) return '暂无分布'
  return entries
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3)
    .map(([label, count]) => {
      const display =
        kind === 'edge'
          ? EDGE_TYPE_LABELS[label] || getRelationDisplay(label)
          : NODE_TYPE_LABELS[label] || getNodeTypeDisplay(label)
      return `${display} ${count}`
    })
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

async function loadOverviewData() {
  graphLoading.value = true
  error.value = ''
  try {
    const [graphResponse, flowResponse] = await Promise.all([
      fetchGraphOverview({ limitNodes: 200, limitEdges: 300 }),
      fetchPlaceFlows(80)
    ])
    overviewGraph.value = graphResponse
    placeFlows.value = flowResponse.flows || []
  } catch (requestError) {
    if (demoMode) {
      overviewGraph.value = buildFallbackRecordGraph(recordId.value)
      placeFlows.value = [
        {
          origin_place: '泰国',
          destination_place: '广东饶平',
          count: 1,
          record_ids_sample: [recordId.value]
        }
      ]
      error.value = demoFailureMessage('全局图谱请求')
    } else {
      error.value = apiFailureMessage(requestError, '全局图谱请求')
    }
  } finally {
    graphLoading.value = false
  }
}

async function switchToRecord(value) {
  const activeRecordId = String(value || '').trim()
  if (!activeRecordId) return
  recordId.value = activeRecordId
  graphLoading.value = true
  error.value = ''
  clearSelection()
  try {
    recordGraph.value = await fetchRecordGraph(activeRecordId)
  } catch (requestError) {
    if (demoMode) {
      recordGraph.value = buildFallbackRecordGraph(activeRecordId)
      error.value = demoFailureMessage('记录子图请求')
    } else {
      recordGraph.value = { nodes: [], edges: [] }
      error.value = apiFailureMessage(requestError, '记录子图请求')
    }
  } finally {
    currentView.value = 'record'
    graphLoading.value = false
  }

  await nextTick()
  const recordNode = transformGraphForRecord(recordGraph.value).nodes.find(
    (node) => nodeType(node) === 'record'
  )
  if (recordNode) {
    await selectNode(recordNode, { skipRecordDrill: true })
    canvasRef.value?.focusNode(recordNode.id)
  }
}

function switchView(view) {
  if (view === 'record') {
    switchToRecord(recordId.value)
    return
  }
  currentView.value = view
  clearSelection()
}

function clearSelection() {
  traceRequestId += 1
  selectedNode.value = null
  selectedEdge.value = null
  neighborGraph.value = { nodes: [], edges: [] }
  neighborEvidence.value = []
  sourceDetail.value = null
}

async function selectNode(node, options = {}) {
  if (nodeType(node) === 'record' && currentView.value !== 'record' && !options.skipRecordDrill) {
    const activeRecordId =
      node.record_id || String(node.id || '').replace(/^record:/, '')
    await switchToRecord(activeRecordId)
    return
  }

  const requestId = ++traceRequestId
  selectedNode.value = node
  selectedEdge.value = null
  sourceDetail.value = null
  neighborGraph.value = { nodes: [], edges: [] }
  neighborEvidence.value = []

  const localRecordIds = selectedGraphContext(node, transformedGraph.value).recordIds
  loadRecordSummaries(localRecordIds)

  if (node.synthetic || String(node.id || '').startsWith('flow-')) return

  traceLoading.value = true
  try {
    const neighbors = await fetchNodeNeighbors(node.id, { depth: 2, limit: 140 })
    if (requestId !== traceRequestId) return
    neighborGraph.value = neighbors
    neighborEvidence.value = evidenceTracesFromGraph(neighbors)
    loadRecordSummaries(selectedGraphContext(node, neighbors).recordIds)
    sourceDetail.value = await loadDirectSourceWithFallback(node)
  } catch (requestError) {
    if (requestId !== traceRequestId) return
    const fallbackNeighbors = demoMode
      ? buildFallbackNeighborGraph(node.id, recordGraph.value.nodes?.length
          ? recordGraph.value
          : overviewGraph.value)
      : null
    if (fallbackNeighbors) {
      neighborGraph.value = fallbackNeighbors
      neighborEvidence.value = evidenceTracesFromGraph(fallbackNeighbors)
      sourceDetail.value = await loadDirectSourceWithFallback(node)
      if (!error.value) error.value = demoFailureMessage('节点证据追溯请求')
    } else {
      error.value = apiFailureMessage(requestError, '节点证据追溯请求')
    }
  } finally {
    if (requestId === traceRequestId) traceLoading.value = false
  }
}

function selectEdge(edge) {
  traceRequestId += 1
  selectedEdge.value = edge
  selectedNode.value = null
  sourceDetail.value = null
  neighborGraph.value = { nodes: [], edges: [] }
  neighborEvidence.value = []
  const context = selectedGraphContext(edge, transformedGraph.value)
  loadRecordSummaries(context.recordIds)
}

async function loadDirectSource(node) {
  if (nodeType(node) === 'record') {
    const activeRecordId = node.record_id || node.id.replace(/^record:/, '')
    const detail = await fetchRecordDetail(activeRecordId)
    return {
      title: '侨批基本信息',
      recordId: activeRecordId,
      items: [
        { label: '题名', value: detail.title_reference || detail.title },
        { label: '写信人', value: detail.sender || '未知人物' },
        { label: '收信人', value: detail.recipient || '未知人物' },
        { label: '时间', value: detail.date_text || detail.date_standard || '未知日期' },
        { label: '来源地', value: detail.origin_place || '未知地点' },
        { label: '寄达地', value: detail.destination_place || '未知地点' }
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
        { label: '证据类型', value: getThemeDisplay(evidence.evidence_type) },
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
        { label: '题名', value: detail.title_clean || detail.title_raw },
        { label: '写信人', value: detail.sender_raw || '未知人物' },
        { label: '收信人', value: detail.recipient_raw || '未知人物' },
        { label: '时间', value: detail.date_text || detail.date_standard || '未知日期' },
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

async function loadRecordSummaries(recordIds) {
  const pendingIds = unique(recordIds)
    .filter((id) => !recordSummaries.value[id])
    .slice(0, 8)
  if (!pendingIds.length) return

  const results = await Promise.allSettled(
    pendingIds.map(async (id) => ({ id, detail: await fetchRecordDetail(id) }))
  )
  const next = { ...recordSummaries.value }
  for (const result of results) {
    if (result.status !== 'fulfilled') continue
    const { id, detail } = result.value
    next[id] =
      detail.title_reference ||
      detail.title ||
      [detail.sender, detail.recipient].filter(Boolean).join(' 致 ') ||
      '侨批档案记录'
  }
  recordSummaries.value = next
}

function recordSummary(id) {
  if (recordSummaries.value[id]) return recordSummaries.value[id]
  const recordNode = [
    ...(overviewGraph.value.nodes || []),
    ...(recordGraph.value.nodes || [])
  ].find((node) => node.record_id === id && node.type === 'record')
  return recordNode?.properties?.title_reference || '点击查看该侨批的完整档案'
}

function focusSearchResult() {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return
  const node = displayGraph.value.nodes.find((item) =>
    (item.searchableKeywords || []).some((keyword) => keyword.includes(query))
  )
  if (!node) return
  selectNode(node, { skipRecordDrill: true })
  nextTick(() => canvasRef.value?.focusNode(node.id))
}

function resetGraphView() {
  searchQuery.value = ''
  themeFilter.value = ''
  yearFilter.value = ''
  evidenceOnly.value = false
  nodeLimit.value = 36
  clearSelection()
  nextTick(() => canvasRef.value?.resetView())
}

function expandGraph() {
  nodeLimit.value = nodeLimit.value > 36 ? 36 : 56
}

function exportGraphImage() {
  const imageUrl = canvasRef.value?.exportImage()
  if (!imageUrl) return
  const link = document.createElement('a')
  link.href = imageUrl
  link.download = `${graphTitle.value.replace(/[·\s]+/g, '-')}.png`
  link.click()
}

function joinedValue(values, fallback) {
  return values.length ? values.slice(0, 6).join('、') : fallback
}

function unique(values = []) {
  return [...new Set(values.map((value) => String(value || '').trim()).filter(Boolean))]
}

function uniqueEvidence(values = []) {
  const map = new Map()
  for (const value of values) {
    const key = `${value.recordId}|${value.text}`
    if (value.text && !map.has(key)) map.set(key, value)
  }
  return [...map.values()]
}

onMounted(async () => {
  await Promise.all([loadStats(), loadOverviewData()])
  await nextTick()
  syncTracePanelHeight()
  graphCardResizeObserver = new ResizeObserver(syncTracePanelHeight)
  if (graphCardRef.value) graphCardResizeObserver.observe(graphCardRef.value)
  window.addEventListener('resize', syncTracePanelHeight)
})

function syncTracePanelHeight() {
  tracePanelHeight.value =
    window.innerWidth > 1180 ? Math.round(graphCardRef.value?.offsetHeight || 0) : 0
}

onBeforeUnmount(() => {
  graphCardResizeObserver?.disconnect()
  window.removeEventListener('resize', syncTracePanelHeight)
})
</script>
