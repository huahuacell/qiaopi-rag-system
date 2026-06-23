const RELATIONSHIP_LABELS = {
  child_to_parent: '子女→父母',
  parent_to_child: '父母→子女',
  sibling_other: '兄弟姐妹',
  spouse_to_spouse: '夫妻',
  grandchild_to_grandparent: '孙辈→祖辈',
  grandchild_to_grandparents: '孙辈→祖辈',
  social_or_other: '社会/其他',
  sibling_or_same_generation_kin: '兄弟姐妹/同辈',
  social_or_business: '社会/商业',
  son_in_law_to_parent_in_law: '女婿→岳父母',
  uncle_nephew_or_nephew_kin: '叔侄/舅甥',
  younger_to_elder_kin: '晚辈→长辈',
  in_law_or_affinal_kin: '姻亲',
  parent_to_child_in_law: '父母→子女配偶',
  unknown: '关系不详'
}

const FALLBACK_LABEL_LENGTH = 11
const ORIGIN_AXIS_LABEL_LENGTH = 6

export function originAxisLabelOption() {
  return {
    interval: 0,
    rotate: 24,
    hideOverlap: false,
    width: 72,
    overflow: 'truncate',
    formatter(value) {
      const label = String(value ?? '')
      return label.length > ORIGIN_AXIS_LABEL_LENGTH
        ? `${label.slice(0, ORIGIN_AXIS_LABEL_LENGTH)}…`
        : label
    }
  }
}

export function formatRelationshipLabel(rawLabel) {
  const normalized = String(rawLabel ?? '').trim()
  if (!normalized) return '关系不详'

  const mapped = RELATIONSHIP_LABELS[normalized]
  if (mapped) return mapped

  if (/^grandchild_to_grandparents?$/.test(normalized)) return '孙辈→祖辈'

  const fallback = normalized.replace(/_+/g, ' ')
  return fallback.length > FALLBACK_LABEL_LENGTH
    ? `${fallback.slice(0, FALLBACK_LABEL_LENGTH)}…`
    : fallback
}

export function formatRelationshipDistribution(items = []) {
  return items.map((item) => {
    const rawLabel = String(item?.label ?? '')
    return {
      ...item,
      label: formatRelationshipLabel(rawLabel),
      rawLabel
    }
  })
}

export function splitYearDistribution(items = []) {
  let unknownCount = 0
  const years = []

  for (const item of items) {
    const rawLabel = String(item?.label ?? '').trim()
    const value = Number(item?.value || 0)

    if (rawLabel.toLowerCase() === 'unknown') {
      unknownCount += value
      continue
    }

    if (!/^\d{4}$/.test(rawLabel)) continue
    years.push({ label: rawLabel, value })
  }

  years.sort((left, right) => Number(left.label) - Number(right.label))
  return { years, unknownCount }
}
