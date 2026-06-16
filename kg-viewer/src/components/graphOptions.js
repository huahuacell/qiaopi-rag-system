import {
  getEdgeDisplayLabel,
  getNodeCategoryLabel,
  getNodeDisplayLabel,
  getNodeTooltip,
  shortenText
} from '../utils/displayLabels.js'

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

export function buildGraphOption(payload, title, options = {}) {
  const nodes = payload.nodes || []
  const edges = payload.edges || []
  const categoryTypes = Array.from(new Set([...TYPE_ORDER, ...nodes.map((node) => nodeType(node))]))
  const showEvidenceLabels = options.showEvidenceLabels === true

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
          return formatTooltip([
            `关系类型：${getEdgeDisplayLabel(edge)}`,
            `原始关系：${edge.edge_type || edge.type || ''}`,
            `置信度：${edge.confidence !== undefined ? Number(edge.confidence).toFixed(2) : ''}`,
            `证据：${edge.evidence_text || firstListItem(edge.properties?.evidence_texts) || ''}`
          ])
        }
        const node = params.data.raw || {}
        return formatTooltip(getNodeTooltip(node).split('\n'))
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
      data: categoryTypes.map((type) => getNodeCategoryLabel({ type }))
    },
    series: [
      {
        name: title,
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        categories: categoryTypes.map((type) => ({ name: getNodeCategoryLabel({ type }) })),
        force: {
          repulsion: options.repulsion || 280,
          edgeLength: options.edgeLength || [116, 230],
          friction: 0.24,
          gravity: 0.055
        },
        label: {
          show: true,
          position: 'right',
          formatter(params) {
            return compactLabel(params.data.name, nodeType(params.data.raw))
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
          name: getNodeDisplayLabel(node),
          category: getNodeCategoryLabel(node),
          symbol: TYPE_SYMBOLS[nodeType(node)] || 'circle',
          symbolSize: symbolSize(nodeType(node)),
          value: node.id,
          raw: node,
          label: {
            show: nodeType(node) !== 'evidence' || showEvidenceLabels
          },
          itemStyle: {
            color: TYPE_COLORS[nodeType(node)] || '#707070',
            borderColor: '#000000',
            borderWidth: 1.15,
            shadowBlur: 0,
            opacity: 0.96
          }
        })),
        links: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
          name: getEdgeDisplayLabel(edge),
          raw: edge,
          label: {
            show: false,
            formatter: getEdgeDisplayLabel(edge)
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
  if (type === 'evidence') return 13
  if (type === 'amount') return 24
  return 28
}

function compactLabel(value, type) {
  const text = String(value || '')
  if (type === 'evidence') return shortenText(text, 8)
  if (type === 'record' || type === 'metadata_record') return shortenText(text, 12)
  return shortenText(text, 16)
}

function nodeType(node) {
  return node?.node_type || node?.type || node?.category || ''
}

function firstListItem(value) {
  if (Array.isArray(value)) return value[0] || ''
  return value || ''
}

function formatTooltip(lines) {
  return lines
    .filter((line) => !String(line).endsWith('：'))
    .map((line, index) => {
      const escaped = escapeHtml(line)
      return index === 0 ? `<strong>${escaped}</strong>` : escaped
    })
    .join('<br/>')
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
