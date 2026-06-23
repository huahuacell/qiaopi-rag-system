const EMPTY_VALUES = {
  people: '未发现明确人物关系',
  places: '未发现明确地点',
  amounts: '未发现明确金额',
  topics: '未发现明确主题'
}

const KNOWN_PLACES = [
  '新加坡',
  '潮州',
  '汕头',
  '香港',
  '澳门',
  '泰国',
  '暹罗',
  '越南',
  '马来亚',
  '马来西亚',
  '槟城',
  '印尼',
  '印度尼西亚',
  '菲律宾',
  '缅甸'
]

const AMOUNT_PATTERN = /(?:荷银|洋银|大洋|银元|银)?[零〇一二两三四五六七八九十百千万\d]+(?:元|毫|角|钱|银元|荷银|洋银|大洋)/g

export function buildInterpretationSummary({ result = {}, record = {}, sourceText = '' } = {}) {
  const evidenceText = (result.evidence_references || [])
    .map((item) => item?.unit_text || '')
    .filter(Boolean)
    .join('；')
  const evidenceTypes = (result.evidence_references || [])
    .map((item) => item?.unit_type || item?.evidence_type || '')
    .filter(Boolean)
    .join(' ')
  const factualText = [sourceText, evidenceText].filter(Boolean).join('；')

  return [
    {
      num: '01',
      label: '人物关系',
      value: peopleSummary(record, result, factualText)
    },
    {
      num: '02',
      label: '地点信息',
      value: placeSummary(record, result, factualText)
    },
    {
      num: '03',
      label: '金额信息',
      value: amountSummary(record, result, factualText)
    },
    {
      num: '04',
      label: '主题信息',
      value: topicSummary(record, factualText, evidenceTypes)
    }
  ]
}

function recordValue(record, key) {
  return record?.metadata?.[key] ?? record?.raw_fields?.[key] ?? record?.[key]
}

function peopleSummary(record, result, factualText) {
  const slots = result.slots || {}
  const sender = firstText(
    recordValue(record, 'sender_name_clean'),
    recordValue(record, 'sender'),
    slots.sender,
    slots.sender_name
  )
  const recipient = firstText(
    recordValue(record, 'recipient_name_clean'),
    recordValue(record, 'recipient'),
    slots.recipient,
    slots.recipient_name
  )
  const relationship = firstText(
    recordValue(record, 'kinship'),
    recordValue(record, 'relationship_type'),
    slots.relationship,
    slots.relationship_type
  )
  const callTerm = firstMatch(
    factualText,
    /(?:母亲|父亲|双亲|祖父|祖母|兄长|兄弟|弟弟|姐姐|妹妹|妻子|丈夫|儿子|女儿)/g
  )
  const parts = []
  if (sender) parts.push(`寄批人：${sender}`)
  if (recipient) parts.push(`收批人：${recipient}`)
  if (relationship) parts.push(`关系：${relationship}`)
  else if (callTerm) parts.push(`称谓：${callTerm}`)
  return parts.join('；') || EMPTY_VALUES.people
}

function placeSummary(record, result, factualText) {
  const slots = result.slots || {}
  const values = [
    recordValue(record, 'origin_place'),
    recordValue(record, 'destination_place'),
    recordValue(record, 'place_mentions_normalized'),
    recordValue(record, 'countries_or_regions'),
    slots.origin_place,
    slots.residence_place,
    slots.destination_place
  ]
  const places = unique(
    values.flatMap(splitValues).concat(
      KNOWN_PLACES.filter((place) => factualText.includes(place))
    )
  )
  return places.join('、') || EMPTY_VALUES.places
}

function amountSummary(record, result, factualText) {
  const slots = result.slots || {}
  const values = [
    slots.money,
    slots.amount,
    recordValue(record, 'money'),
    recordValue(record, 'remittance_raw'),
    ...(factualText.match(AMOUNT_PATTERN) || [])
  ]
  const amounts = unique(values.flatMap(splitValues))
  return amounts.join('、') || EMPTY_VALUES.amounts
}

function topicSummary(record, factualText, evidenceTypes) {
  const corpus = [
    recordValue(record, 'main_intent'),
    recordValue(record, 'theme_tags'),
    recordValue(record, 'retrieval_keywords'),
    recordValue(record, 'rag_summary_text'),
    factualText,
    evidenceTypes
  ]
    .filter(Boolean)
    .join(' ')
  if (!corpus) return EMPTY_VALUES.topics

  const topics = []
  const hasRemittance = recordValue(record, 'has_remittance')
  if (
    hasRemittance === true ||
    Number(hasRemittance) === 1 ||
    /寄款|汇款|款项|银元|荷银|洋银|大洋|remittance/i.test(corpus)
  ) {
    topics.push('汇款')
  }
  if (/家书|家人|母亲|父亲|亲人|平安|问候|思念/.test(corpus)) {
    topics.push('家书')
  }
  if (/收款|查收|收讫|收到|领收/.test(corpus)) {
    topics.push('收款')
  }
  topics.push('侨批往来')
  return unique(topics).join('、')
}

function firstText(...values) {
  return values.map(cleanText).find(Boolean) || ''
}

function cleanText(value) {
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean).join('、')
  return String(value ?? '').trim()
}

function splitValues(value) {
  return cleanText(value)
    .split(/[、，,;；|/\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function unique(values) {
  return [...new Set(values.map(cleanText).filter(Boolean))]
}

function firstMatch(text, pattern) {
  return String(text || '').match(pattern)?.[0] || ''
}
