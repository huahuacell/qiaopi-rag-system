export const THEME_LABELS = {
  health: '健康问候',
  health_care: '健康问候',
  safety_report: '平安报告',
  safety: '平安消息',
  remittance: '批款汇款',
  instruction: '嘱托叮咛',
  family_affection: '亲情思念',
  study: '读书教育',
  debt: '债务借贷',
  marriage: '婚姻家庭',
  work: '工作谋生',
  funeral: '丧葬祭祀',
  home_building: '建房置业'
}

export const NODE_TYPE_LABELS = {
  record: '侨批',
  metadata_record: '目录',
  person: '人物',
  place: '地点',
  amount: '金额',
  date: '日期',
  theme: '主题',
  evidence: '证据'
}

export const EDGE_TYPE_LABELS = {
  SENT_BY: '寄批人',
  RECEIVED_BY: '收批人',
  MENTIONS_PERSON: '涉及人物',
  MENTIONS_PLACE: '涉及地点',
  SENT_FROM: '发自',
  SENT_TO: '寄往',
  HAS_AMOUNT: '批款',
  HAS_DATE: '日期',
  HAS_THEME: '主题',
  SUPPORTED_BY: '证据',
  LINKED_TO_METADATA: '关联目录'
}

export function getNodeDisplayLabel(node) {
  const type = getNodeType(node)
  if (type === 'record') {
    return shortRecordId(node?.id || node?.record_id || node?.label)
  }
  if (type === 'metadata_record') {
    return shortMetadataId(node?.id || node?.label) || '目录记录'
  }
  if (type === 'evidence') {
    return '证据片段'
  }
  if (type === 'theme') {
    return getThemeLabel(node)
  }
  return String(node?.label || node?.normalized_label || node?.id || '')
}

export function getNodeTooltip(node) {
  const properties = node?.properties || {}
  const lines = [
    `节点类型：${getNodeCategoryLabel(node)}`,
    `节点ID：${node?.id || ''}`,
    `显示名称：${getNodeDisplayLabel(node)}`,
    `原始标签：${node?.label || ''}`,
    `标准标签：${node?.normalized_label || ''}`
  ]

  if (properties.kinship_type) lines.push(`亲属类型：${properties.kinship_type}`)
  if (properties.raw_labels) lines.push(`原始称谓：${formatList(properties.raw_labels)}`)

  const evidenceText = firstText(
    node?.evidence_text,
    properties.evidence_text,
    properties.evidence_texts,
    getNodeType(node) === 'evidence' ? node?.label : ''
  )
  if (evidenceText) lines.push(`证据文本：${evidenceText}`)

  return lines.filter(Boolean).join('\n')
}

export function getEdgeDisplayLabel(edge) {
  const edgeType = edge?.edge_type || edge?.type || edge?.label || ''
  return EDGE_TYPE_LABELS[edgeType] || edgeType
}

export function getNodeCategoryLabel(node) {
  const type = getNodeType(node)
  return NODE_TYPE_LABELS[type] || type || '未知'
}

export function shortenText(text, maxLength) {
  const value = String(text || '').trim()
  if (!value || value.length <= maxLength) return value
  return `${value.slice(0, Math.max(0, maxLength))}…`
}

function getThemeLabel(node) {
  const value = stripNodePrefix(node?.normalized_label || node?.label || node?.id)
  return THEME_LABELS[value] || value
}

function getNodeType(node) {
  return node?.node_type || node?.type || node?.category || ''
}

function shortRecordId(value) {
  const text = stripNodePrefix(value)
  const match = text.match(/(TEXT-\d+)$/)
  return match ? match[1] : shortenText(text, 12)
}

function shortMetadataId(value) {
  const text = stripNodePrefix(value)
  const match = text.match(/(META-\d+)$/)
  return match ? match[1] : ''
}

function stripNodePrefix(value) {
  return String(value || '').replace(/^[a-z_]+:/i, '').trim()
}

function formatList(value) {
  if (Array.isArray(value)) return value.join('、')
  return String(value || '')
}

function firstText(...values) {
  for (const value of values) {
    if (Array.isArray(value)) {
      const joined = value.filter(Boolean).join('；')
      if (joined) return joined
      continue
    }
    const text = String(value || '').trim()
    if (text) return text
  }
  return ''
}
