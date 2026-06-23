function recordValue(record, key) {
  return record?.metadata?.[key] ?? record?.[key]
}

const metadataFieldDefinitions = [
  { key: 'record_id', label: '记录编号', mono: true },
  { key: 'archive_id', label: '档案编号', mono: true },
  { key: 'file_no', label: '档号', mono: true },
  { key: 'title', label: '题名' },
  { key: 'title_reference', label: '题名' },
  { key: 'sender_name_clean', label: '寄信人' },
  { key: 'sender', label: '寄信人' },
  { key: 'recipient_name_clean', label: '收信人' },
  { key: 'recipient', label: '收信人' },
  { key: 'date_text', label: '原始日期' },
  { key: 'date', label: '日期' },
  { key: 'date_standard', label: '规范日期', mono: true },
  { key: 'year_normalized', label: '年份', mono: true },
  { key: 'origin_place', label: '寄出地' },
  { key: 'destination_place', label: '收信地' },
  { key: 'country_or_region', label: '国家或地区' },
  { key: 'kinship', label: '亲属称谓' },
  { key: 'relationship_type', label: '人物关系' },
  { key: 'money', label: '汇款金额' },
  { key: 'amount_text', label: '汇款金额' },
  { key: 'currency', label: '币种' },
  { key: 'has_remittance', label: '是否涉及汇款' },
  { key: 'has_full_text', label: '是否有全文' },
  { key: 'main_intent', label: '主要内容' },
  { key: 'theme_tags', label: '主题标签' },
  { key: 'text_quality_level', label: '文本质量' },
  { key: 'place_mentions_normalized', label: '涉及地点' },
  { key: 'retrieval_keywords', label: '检索关键词' }
]

const metadataValueLabels = {
  remittance: '汇款',
  instruction: '嘱托',
  greeting: '问候',
  safety_report: '平安报讯',
  family_affection: '亲情关怀',
  business: '商务往来',
  other: '其他',
  unknown: '待考',
  high: '高',
  medium: '中',
  low: '低',
  son_to_parent: '儿子致父母',
  daughter_to_parent: '女儿致父母',
  child_to_parent: '子女致父母',
  parent_to_child: '父母致子女',
  husband_to_wife: '丈夫致妻子',
  wife_to_husband: '妻子致丈夫',
  sibling_to_sibling: '手足之间',
  relative_to_relative: '亲属之间',
  theme_remittance: '汇款',
  theme_family_affection: '亲情',
  theme_safety: '平安',
  theme_instruction: '嘱托',
  theme_greeting: '问候'
}

function localizeMetadataToken(token) {
  const normalized = String(token ?? '').trim()
  return metadataValueLabels[normalized] || normalized
}

export function formatRecordMetadataValue(key, value) {
  if (key === 'has_remittance' || key === 'has_full_text') {
    return Number(value) === 1 || value === true || value === 'true' ? '是' : '否'
  }
  if (Array.isArray(value)) {
    return value.filter(Boolean).map(localizeMetadataToken).join('、')
  }
  if (typeof value === 'object') return ''

  const text = String(value ?? '').trim()
  if (!text) return ''
  if (metadataValueLabels[text]) return metadataValueLabels[text]

  if (key === 'theme_tags' || key === 'main_intent' || key === 'relationship_type') {
    return text
      .split(/[；;,、|]+/)
      .map(localizeMetadataToken)
      .filter(Boolean)
      .join('、')
  }
  return text
}

export function buildRecordMetadataRows(record = {}, recordId = '', title = '') {
  const overrides = {
    record_id: recordId || recordValue(record, 'record_id'),
    title: title || recordValue(record, 'title') || recordValue(record, 'title_reference'),
    sender_name_clean: recordValue(record, 'sender_name_clean') || recordValue(record, 'sender'),
    recipient_name_clean: recordValue(record, 'recipient_name_clean') || recordValue(record, 'recipient')
  }
  const rows = []

  metadataFieldDefinitions.forEach(({ key, label, mono = false }) => {
    const rawValue = overrides[key] ?? recordValue(record, key)
    if (rawValue === undefined || rawValue === null || rawValue === '') return
    const value = formatRecordMetadataValue(key, rawValue)
    if (!value || rows.some((row) => row.label === label)) return
    rows.push({ key, label, value, mono })
  })

  return rows
}

function keywordValue(value) {
  if (Array.isArray(value)) return value.filter(Boolean).join(' ')
  return String(value ?? '').trim()
}

function searchTarget(keyword) {
  const query = keywordValue(keyword)
  return query ? { path: '/search', query: { query } } : null
}

export function buildRelatedArchiveItems(record = {}) {
  const origin = recordValue(record, 'origin_place')
  const relationship =
    recordValue(record, 'kinship') ||
    recordValue(record, 'relationship_type') ||
    recordValue(record, 'recipient') ||
    recordValue(record, 'recipient_name_clean') ||
    recordValue(record, 'sender') ||
    recordValue(record, 'sender_name_clean')
  const mainIntent = recordValue(record, 'main_intent')

  return [
    {
      label: '同来源地',
      title: `${keywordValue(origin) || '来源地'}相关侨批`,
      description: '沿同一侨居地继续查看跨地域书信线索。',
      to: searchTarget(origin)
    },
    {
      label: '同亲属关系',
      title: `${keywordValue(relationship) || '亲属'}相关家书`,
      description: '比较亲属称谓、问候对象与家庭责任表达。',
      to: searchTarget(relationship)
    },
    {
      label: '同主题',
      title: keywordValue(mainIntent) || '汇款',
      description: '追踪相近主题下的证据片段与释读方式。',
      to: searchTarget('汇款')
    }
  ]
}
