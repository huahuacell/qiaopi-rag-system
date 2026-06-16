const TYPE_COLORS = {
  record: '#fa7864',
  metadata_record: '#dc8264',
  person: '#3b2a24',
  place: '#8e6454',
  amount: '#b98569',
  date: '#707070',
  theme: '#282828',
  evidence: '#e8e8e1'
}

const TYPE_ORDER = ['record', 'metadata_record', 'person', 'place', 'amount', 'date', 'theme', 'evidence']

const TYPE_LABELS = {
  record: '批信',
  metadata_record: '目录记录',
  person: '人物',
  place: '地点',
  amount: '款项',
  date: '日期',
  theme: '主题',
  evidence: '证据'
}

const TYPE_SYMBOLS = {
  record: 'roundRect',
  metadata_record: 'roundRect',
  person: 'circle',
  place: 'circle',
  amount: 'circle',
  date: 'circle',
  theme: 'roundRect',
  evidence: 'roundRect'
}

const EDGE_LABELS = {
  SENT_BY: '寄信人',
  RECEIVED_BY: '收信人',
  MENTIONS_PERSON: '提及人物',
  MENTIONS_PLACE: '提及地点',
  SENT_FROM: '寄出地',
  SENT_TO: '寄达地',
  HAS_AMOUNT: '款项',
  HAS_DATE: '日期',
  HAS_THEME: '主题',
  SUPPORTED_BY: '证据支持',
  LINKED_TO_METADATA: '目录链接'
}

export function buildGraphOption(payload, title) {
  const nodes = payload.nodes || []
  const edges = payload.edges || []
  const categoryTypes = Array.from(new Set([...TYPE_ORDER, ...nodes.map((node) => node.type)]))

  return {
    backgroundColor: 'rgba(255, 255, 255, 0)',
    color: categoryTypes.map((type) => TYPE_COLORS[type] || '#707070'),
    animation: true,
    animationDuration: 900,
    animationDurationUpdate: 760,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'quarticInOut',
    tooltip: {
      trigger: 'item',
      confine: true,
      backgroundColor: '#fff5e6',
      borderColor: '#000000',
      borderWidth: 1,
      textStyle: {
        color: '#000000',
        fontSize: 12
      },
      formatter(params) {
        if (params.dataType === 'edge') {
          const edge = params.data.raw || {}
          const edgeLabel = EDGE_LABELS[edge.type] || edge.type || ''
          const parts = [
            `<strong>${escapeHtml(edgeLabel)}</strong>`,
            `来源：${escapeHtml(edge.source || '')}`,
            `目标：${escapeHtml(edge.target || '')}`
          ]
          if (edge.evidence_text) parts.push(`证据：${escapeHtml(edge.evidence_text)}`)
          if (edge.confidence !== undefined) parts.push(`可信度：${Number(edge.confidence).toFixed(2)}`)
          return parts.join('<br/>')
        }
        const node = params.data.raw || {}
        return [
          `<strong>${escapeHtml(node.label || node.id || '')}</strong>`,
          `ID：${escapeHtml(node.id || '')}`,
          `类型：${escapeHtml(TYPE_LABELS[node.type] || node.type || '')}`
        ].join('<br/>')
      }
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 8,
      top: 12,
      bottom: 12,
      itemGap: 10,
      textStyle: {
        color: '#282828',
        fontSize: 12
      },
      data: categoryTypes.map((type) => TYPE_LABELS[type] || type)
    },
    series: [
      {
        name: title,
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        categories: categoryTypes.map((type) => ({ name: TYPE_LABELS[type] || type })),
        force: {
          repulsion: 165,
          edgeLength: [82, 170],
          friction: 0.32,
          gravity: 0.08
        },
        label: {
          show: true,
          position: 'right',
          formatter(params) {
            return compactLabel(params.data.name)
          },
          color: '#000000',
          fontSize: 11
        },
        edgeLabel: {
          show: false
        },
        lineStyle: {
          color: 'rgba(112, 112, 112, 0.62)',
          width: 1.35,
          opacity: 0.72,
          curveness: 0.18,
          cap: 'round',
          join: 'round'
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 2.4,
            color: '#dc8264',
            opacity: 0.9,
            cap: 'round'
          }
        },
        data: nodes.map((node) => ({
          id: node.id,
          name: node.label || node.id,
          category: TYPE_LABELS[node.type] || node.type,
          symbol: TYPE_SYMBOLS[node.type] || 'circle',
          symbolSize: symbolSize(node.type),
          value: node.id,
          raw: node,
          itemStyle: {
            color: TYPE_COLORS[node.type] || '#707070',
            borderColor: '#000000',
            borderWidth: 1.15,
            shadowBlur: 0,
            opacity: 0.96
          }
        })),
        links: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
          name: edge.type,
          raw: edge,
          label: {
            formatter: edge.type
          },
          lineStyle: {
            width: Math.max(1.1, Math.min(3.2, Number(edge.confidence || 0.6) * 2.2)),
            curveness: 0.18,
            cap: 'round',
            join: 'round'
          }
        }))
      }
    ]
  }
}

function symbolSize(type) {
  if (type === 'record') return 38
  if (type === 'metadata_record') return 32
  if (type === 'evidence') return 19
  if (type === 'amount') return 24
  return 28
}

function compactLabel(value) {
  const text = String(value || '')
  return text.length > 18 ? `${text.slice(0, 18)}...` : text
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
