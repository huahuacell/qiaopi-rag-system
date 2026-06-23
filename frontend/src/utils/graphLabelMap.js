export const themeDisplayMap = {
  remittance: '汇款',
  family_affection: '家庭情感',
  instruction: '嘱托',
  safety: '报平安',
  safety_report: '平安近况',
  business: '经营近况',
  work: '经营生计',
  debt: '债务往来',
  marriage: '婚姻家事',
  funeral: '丧葬家事',
  study: '教育学业',
  health_care: '健康照护',
  home_building: '家园营建',
  hometown: '乡土牵挂',
  other: '其他',
  unknown: '其他主题',
  opening: '书信开篇',
  closing: '书信落款',
  entities: '人物与地点',
  family_care: '家庭关怀',
  livelihood: '生计近况',
  health: '健康问候',
  gratitude: '感恩致意',
  archive_catalog: '档案目录',
  place: '地域信息'
}

const themeTokenDisplayMap = {
  home: '家园',
  building: '营建',
  family: '家庭',
  affection: '情感',
  health: '健康',
  care: '关怀',
  safety: '平安',
  report: '近况',
  work: '生计',
  business: '经营',
  study: '学业',
  education: '教育',
  debt: '债务',
  marriage: '婚姻',
  funeral: '丧葬',
  remittance: '汇款',
  instruction: '嘱托',
  hometown: '乡土',
  place: '地域',
  livelihood: '生计',
  gratitude: '感恩',
  archive: '档案',
  catalog: '目录'
}

export const relationDisplayMap = {
  HAS_THEME: '表达主题',
  MENTIONS_PERSON: '提及人物',
  MENTIONS_LOCATION: '提及地点',
  MENTIONS_PLACE: '提及地点',
  HAS_AMOUNT: '涉及金额',
  HAS_DATE: '发生时间',
  SUPPORTED_BY: '证据支持',
  SENT_BY: '写信人',
  RECEIVED_BY: '收信人',
  SENT_FROM: '寄出地',
  SENT_TO: '寄达地',
  LINKED_TO_METADATA: '关联目录',
  KINSHIP_ADDRESS: '使用称谓',
  COMMUNICATES_WITH: '写信给',
  REMITTANCE_FLOW: '侨汇流向',
  FLOW_ORIGIN: '从此寄出',
  FLOW_DESTINATION: '寄达此地',
  sender: '写信人',
  recipient: '收信人',
  kinship: '亲属称谓',
  location: '地点',
  place: '地点',
  date: '日期',
  amount: '金额'
}

export const nodeTypeDisplayMap = {
  record: '侨批记录',
  record_group: '侨批与侨汇',
  metadata_record: '目录元数据',
  person: '人物',
  kinship: '亲属称谓',
  location: '地点',
  place: '地点',
  overseas_place: '海外侨居地',
  hometown_place: '侨乡家园',
  amount: '金额',
  date: '日期',
  theme: '主题',
  evidence: '证据',
  metadata: '元数据'
}

export const kinshipDisplayMap = {
  mother: '母亲',
  father: '父亲',
  parents: '父母',
  wife: '妻子',
  husband: '丈夫',
  son: '儿子',
  daughter: '女儿',
  elder_brother: '兄长',
  younger_brother: '弟弟',
  brother: '兄弟',
  elder_sister: '姐姐',
  younger_sister: '妹妹',
  sister: '姐妹',
  uncle: '叔伯',
  aunt: '姑姨',
  nephew: '侄辈',
  niece: '侄女',
  grandmother: '祖母',
  grandfather: '祖父',
  spouse: '配偶',
  child: '子女',
  relative: '亲属',
  collective_kinship: '亲属',
  unknown: '亲属称谓',
  none: '人物'
}

const technicalLabelPattern =
  /(^|[;,\s])(sender|recipient|location|evidence|source|record_id|theme|type)=/i

export function rawNodeType(node = {}) {
  return String(node.visualType || node.type || node.category || node.node_type || '')
    .trim()
    .toLowerCase()
}

export function getNodeTypeDisplay(nodeOrType = {}) {
  const type =
    typeof nodeOrType === 'string'
      ? nodeOrType.toLowerCase()
      : rawNodeType(nodeOrType)
  return nodeTypeDisplayMap[type] || '未知节点'
}

export function getRelationDisplay(edgeOrType = {}) {
  const raw =
    typeof edgeOrType === 'string'
      ? edgeOrType
      : edgeOrType.displayType ||
        edgeOrType.type ||
        edgeOrType.label ||
        edgeOrType.edge_type ||
        ''
  return relationDisplayMap[String(raw).trim()] || '关联关系'
}

export function normalizeThemeCode(value) {
  return String(value || '')
    .trim()
    .replace(/^theme[:_-]?/i, '')
    .replace(/\s+/g, '_')
    .toLowerCase()
}

export function getThemeDisplay(value) {
  const code = normalizeThemeCode(value)
  if (themeDisplayMap[code]) return themeDisplayMap[code]

  const inferred = code
    .split(/[_-]+/)
    .map((token) => themeTokenDisplayMap[token])
    .filter(Boolean)
  if (inferred.length) return [...new Set(inferred)].join('')
  return '其他主题'
}

export function isKinshipNode(node = {}) {
  const properties = node.properties || {}
  const personKind = String(properties.person_kind || '').toLowerCase()
  const kinshipType = String(properties.kinship_type || '').toLowerCase()
  return (
    rawNodeType(node) === 'kinship' ||
    personKind === 'kinship_term' ||
    Boolean(kinshipType && kinshipType !== 'none' && kinshipType !== 'unknown')
  )
}

export function getVisualNodeType(node = {}) {
  const type = rawNodeType(node)
  if (type === 'person' && isKinshipNode(node)) return 'kinship'
  return type || 'unknown'
}

export function getDisplayLabel(node = {}) {
  const type = getVisualNodeType(node)
  const properties = node.properties || {}
  const candidates = [
    node.display_name,
    node.zh_label,
    node.name_zh,
    node.displayLabel,
    node.label,
    node.name,
    node.normalized_label
  ]
  const raw = candidates.map(cleanText).find(Boolean) || cleanText(node.id)

  if (type === 'record') {
    return cleanText(node.record_id) || stripNodePrefix(node.id) || '未知侨批'
  }
  if (type === 'record_group') {
    return raw && !technicalLabelPattern.test(raw) ? raw : '侨批与侨汇'
  }
  if (type === 'theme') {
    return getThemeDisplay(raw || stripNodePrefix(node.id))
  }
  if (type === 'evidence') {
    const evidenceType =
      properties.evidence_type || node.evidence_type || stripNodePrefix(node.id)
    const display = getThemeDisplay(evidenceType)
    return display === '其他主题' ? '原文证据' : `${display}证据`
  }
  if (type === 'kinship') {
    const kinshipType = cleanText(properties.kinship_type)
    if (containsChinese(raw) && !technicalLabelPattern.test(raw)) return raw
    return kinshipDisplayMap[kinshipType] || '亲属称谓'
  }
  if (type === 'amount') {
    return raw && !technicalLabelPattern.test(raw) ? raw : '未标注金额'
  }
  if (type === 'date') {
    return raw && !technicalLabelPattern.test(raw) ? formatDateLabel(raw) : '未知日期'
  }
  if (['place', 'location', 'overseas_place', 'hometown_place'].includes(type)) {
    return raw && !technicalLabelPattern.test(raw) ? raw : '未知地点'
  }
  if (type === 'person') {
    return raw && !technicalLabelPattern.test(raw) ? raw : '未知人物'
  }
  if (type === 'metadata_record' || type === 'metadata') {
    return raw && !technicalLabelPattern.test(raw)
      ? raw
      : stripNodePrefix(node.id) || '目录元数据'
  }
  if (raw && !technicalLabelPattern.test(raw) && containsChinese(raw)) return raw
  return fallbackDisplayLabel(type)
}

export function getSearchableKeywords(node = {}) {
  const properties = node.properties || {}
  const values = [
    getDisplayLabel(node),
    node.id,
    node.label,
    node.name,
    node.normalized_label,
    node.record_id,
    properties.theme_tags,
    properties.main_intent,
    properties.kinship_type,
    properties.sender,
    properties.recipient,
    properties.origin_place,
    properties.destination_place,
    ...(Array.isArray(properties.original_labels) ? properties.original_labels : [])
  ]

  if (getVisualNodeType(node) === 'theme') {
    const rawCode = normalizeThemeCode(
      node.label || node.normalized_label || stripNodePrefix(node.id)
    )
    values.push(rawCode, getThemeDisplay(rawCode))
  }

  return values
    .flatMap((value) => String(value || '').split(/[;,|]/))
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean)
}

export function fallbackDisplayLabel(type = '') {
  const fallbacks = {
    person: '未知人物',
    kinship: '亲属称谓',
    place: '未知地点',
    location: '未知地点',
    overseas_place: '未知海外地点',
    hometown_place: '未知侨乡',
    amount: '未标注金额',
    date: '未知日期',
    theme: '其他主题',
    evidence: '暂无证据',
    record: '未知侨批',
    metadata_record: '目录元数据'
  }
  return fallbacks[type] || '未知节点'
}

export function truncateDisplayLabel(value, maxLength = 10) {
  const text = cleanText(value)
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}…`
}

function formatDateLabel(value) {
  const text = cleanText(value)
  const match = text.match(/^(\d{4})[.\-/](\d{1,2})(?:[.\-/](\d{1,2}))?$/)
  if (!match) return text
  return `${match[1]}年${Number(match[2])}月${
    match[3] ? `${Number(match[3])}日` : ''
  }`
}

function stripNodePrefix(value) {
  return cleanText(value).replace(/^[a-z_]+:/i, '')
}

function containsChinese(value) {
  return /[\u3400-\u9fff]/.test(String(value || ''))
}

function cleanText(value) {
  return String(value || '').trim()
}
