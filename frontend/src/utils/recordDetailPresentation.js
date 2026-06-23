function recordValue(record, key) {
  return record?.metadata?.[key] ?? record?.[key]
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
