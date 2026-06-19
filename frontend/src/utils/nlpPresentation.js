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

export function formatOffset(item, normalized = false) {
  const prefix = normalized ? '规范' : '原文'
  const start = normalized ? item?.normalized_start : item?.original_start
  const end = normalized ? item?.normalized_end : item?.original_end
  return `${prefix} [${Number(start || 0)}, ${Number(end || 0)})`
}

export function confidenceText(value) {
  return `${Math.round(Number(value || 0) * 100)}%`
}

export function validateSpanItem(item, originalText, normalizedText) {
  if (!item) return false
  return (
    originalText.slice(item.original_start, item.original_end) === item.source_text &&
    normalizedText.slice(item.normalized_start, item.normalized_end) ===
      item.normalized_source_text
  )
}
