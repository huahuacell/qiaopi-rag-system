import {
  getDisplayLabel,
  getNodeTypeDisplay,
  getRelationDisplay,
  getVisualNodeType
} from './graphLabelMap.js'

export const NODE_TYPE_LABELS = {
  record: '侨批记录',
  record_group: '侨批与侨汇',
  metadata_record: '目录元数据',
  person: '人物',
  kinship: '亲属称谓',
  place: '地点',
  overseas_place: '海外侨居地',
  hometown_place: '侨乡家园',
  amount: '金额',
  date: '日期',
  theme: '主题',
  evidence: '证据片段'
}

export const EDGE_TYPE_LABELS = {
  SENT_BY: '写信人',
  RECEIVED_BY: '收信人',
  MENTIONS_PERSON: '提及人物',
  MENTIONS_PLACE: '提及地点',
  MENTIONS_LOCATION: '提及地点',
  SENT_FROM: '寄出地',
  SENT_TO: '寄达地',
  HAS_AMOUNT: '涉及金额',
  HAS_DATE: '发生时间',
  HAS_THEME: '表达主题',
  SUPPORTED_BY: '证据支持',
  LINKED_TO_METADATA: '关联目录',
  KINSHIP_ADDRESS: '使用称谓',
  COMMUNICATES_WITH: '写信给',
  FLOW_ORIGIN: '从此寄出',
  FLOW_DESTINATION: '寄达此地',
  REMITTANCE_FLOW: '侨汇流向'
}

export const NODE_COLORS = {
  record: '#0f4a43',
  record_group: '#315f59',
  metadata_record: '#a74432',
  person: '#2f514c',
  kinship: '#a94b35',
  place: '#72856b',
  overseas_place: '#2f6c68',
  hometown_place: '#8b7d45',
  amount: '#b17b42',
  date: '#6f7c78',
  theme: '#876448',
  evidence: '#d8c9ad'
}

export function nodeType(node = {}) {
  return node.visualType || getVisualNodeType(node)
}

export function nodeTypeLabel(node = {}) {
  return NODE_TYPE_LABELS[nodeType(node)] || getNodeTypeDisplay(node)
}

export function edgeTypeLabel(edge = {}) {
  const type =
    edge.displayType || edge.rawType || edge.type || edge.label || edge.edge_type || ''
  return EDGE_TYPE_LABELS[type] || getRelationDisplay(type)
}

export function nodeDisplayLabel(node = {}) {
  return node.displayLabel || getDisplayLabel(node)
}

export function recordIdsFromGraph(node = {}, graph = {}) {
  const ids = new Set()
  if (node.record_id) ids.add(node.record_id)
  if (nodeType(node) === 'record') ids.add(stripPrefix(node.id))

  for (const edge of graph.edges || []) {
    if (edge.record_id) ids.add(edge.record_id)
  }
  for (const item of graph.nodes || []) {
    if (item.record_id) ids.add(item.record_id)
    if (nodeType(item) === 'record') ids.add(stripPrefix(item.id))
  }
  return [...ids].filter((value) => value.startsWith('CSQP-SFHC-TEXT-')).sort()
}

export function evidenceTracesFromGraph(graph = {}) {
  const traces = []
  const seen = new Set()

  for (const edge of graph.edges || []) {
    const values = [
      edge.evidence_text,
      ...(Array.isArray(edge.properties?.evidence_texts)
        ? edge.properties.evidence_texts
        : [])
    ]
    for (const value of values) {
      const text = String(value || '').trim()
      if (!text) continue
      const key = `${edge.record_id}|${edge.type}|${text}`
      if (seen.has(key)) continue
      seen.add(key)
      traces.push({
        recordId: edge.record_id || '',
        relation: edgeTypeLabel(edge),
        text,
        sourceTable: edge.source_table || '',
        sourceId: edge.source_id || ''
      })
    }
  }
  return traces.slice(0, 20)
}

export function metadataIdFromNode(node = {}) {
  if (nodeType(node) !== 'metadata_record') return ''
  return (
    node.source_id ||
    node.properties?.metadata_id ||
    stripPrefix(node.id || node.normalized_label)
  )
}

export function evidenceIdFromNode(node = {}) {
  if (nodeType(node) !== 'evidence') return ''
  return node.source_id || node.normalized_label || ''
}

export function graphQualityState(quality = {}) {
  const failures = [
    Number(quality.duplicate_logical_edge_count || 0),
    Number(quality.orphan_edge_count || 0),
    Number(quality.missing_node_provenance_count || 0),
    Number(quality.missing_edge_provenance_count || 0)
  ].reduce((sum, value) => sum + value, 0)
  return {
    healthy: failures === 0,
    failureCount: failures,
    label: failures === 0 ? '构建质量通过' : `发现 ${failures} 项结构问题`
  }
}

export function filterGraph(payload = {}, includeEvidence = true) {
  const nodes = (payload.nodes || []).filter(
    (node) => includeEvidence || nodeType(node) !== 'evidence'
  )
  const nodeIds = new Set(nodes.map((node) => node.id))
  return {
    nodes,
    edges: (payload.edges || []).filter(
      (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
    )
  }
}

function stripPrefix(value) {
  return String(value || '').replace(/^[a-z_]+:/i, '')
}

function shorten(value, length) {
  const text = String(value || '').trim()
  return text.length > length ? `${text.slice(0, length)}…` : text
}
