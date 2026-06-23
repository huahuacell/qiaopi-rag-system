export const ENTITY_TYPE_LABELS = {
  person: '人物',
  kinship: '亲属称谓',
  place: '地点',
  date: '日期',
  money: '金额',
  style_formula: '套语'
}

export const RELATION_TYPE_LABELS = {
  writes_to: '寄件人—收件人',
  child_to_parent: '子女—父母',
  remits_money_to: '汇款给',
  sent_from: '寄出地',
  sent_to: '寄达地'
}

export const SLOT_LABELS = {
  sender: '寄件人',
  recipient: '收件人',
  money: '金额',
  currency: '币种',
  date: '日期',
  origin_place: '来源地',
  destination_place: '目的地',
  purpose: '用途',
  relationship_type: '关系类型'
}

export const NLP_VALUE_LABELS = {
  household_expenses: '家庭生活开支',
  medical_expenses: '医疗与药费',
  education: '教育与学费',
  debt_repayment: '偿还债务',
  distribution: '分配款项',
  writes_to: '寄件人写给收件人',
  child_to_parent: '子女写给父母',
  remits_money_to: '向收件人汇款',
  sent_from: '从该地点寄出',
  sent_to: '寄往该地点',
  writer: '寄件人（姓名未识别）',
  'recipient:unspecified': '收件人（未明确）'
}

export function nlpValueText(value) {
  if (value === null || value === undefined || value === '') return '—'
  return NLP_VALUE_LABELS[String(value)] || String(value)
}

export function formatOffset(item, normalized = false) {
  const prefix = normalized ? '规范' : '原文'
  const start = normalized ? item?.normalized_start : item?.original_start
  const end = normalized ? item?.normalized_end : item?.original_end
  return `${prefix} [${Number(start || 0)}, ${Number(end || 0)})`
}

export function confidenceText(value) {
  const confidence = Math.min(1, Math.max(0, Number(value) || 0))
  return `${Math.round(confidence * 100)}%`
}

export function validateSpanItem(item, originalText, normalizedText) {
  if (!item) return false

  const offsets = [
    item.original_start,
    item.original_end,
    item.normalized_start,
    item.normalized_end
  ]
  if (!offsets.every(Number.isInteger)) return false
  if (
    item.original_start < 0 ||
    item.normalized_start < 0 ||
    item.original_end < item.original_start ||
    item.normalized_end < item.normalized_start ||
    item.original_end > originalText.length ||
    item.normalized_end > normalizedText.length
  ) {
    return false
  }

  return (
    originalText.slice(item.original_start, item.original_end) === item.source_text &&
    normalizedText.slice(item.normalized_start, item.normalized_end) ===
      item.normalized_source_text
  )
}

export function normalizeNlpResult(payload = {}) {
  const entities = Array.isArray(payload.entities) ? payload.entities : []
  const relations = Array.isArray(payload.relations) ? payload.relations : []
  const slots = Array.isArray(payload.slots) ? payload.slots : []
  const summary = payload.summary || {}

  return {
    task: payload.task || '',
    engine: payload.engine || '',
    pipeline_version: payload.pipeline_version || '',
    normalization_version: payload.normalization_version || '',
    entity_extractor_version: payload.entity_extractor_version || '',
    relation_extractor_version: payload.relation_extractor_version || '',
    slot_extractor_version: payload.slot_extractor_version || '',
    original_text: payload.original_text || '',
    normalized_text: payload.normalized_text || '',
    normalization_changed: Boolean(payload.normalization_changed),
    review_required: Boolean(payload.review_required),
    review_reasons: Array.isArray(payload.review_reasons) ? payload.review_reasons : [],
    entities,
    relations,
    slots,
    summary: {
      entity_count: Number.isInteger(summary.entity_count)
        ? summary.entity_count
        : entities.length,
      relation_count: Number.isInteger(summary.relation_count)
        ? summary.relation_count
        : relations.length,
      slot_count: Number.isInteger(summary.slot_count)
        ? summary.slot_count
        : slots.length,
      review_item_count: Number.isInteger(summary.review_item_count)
        ? summary.review_item_count
        : [...entities, ...relations, ...slots].filter((item) => item.needs_review).length
    }
  }
}
