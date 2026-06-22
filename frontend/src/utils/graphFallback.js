import fallbackRecordGraph from '../mock/graph_record.json' with { type: 'json' }

const SAMPLE_RECORD_ID = fallbackRecordGraph.record_id

export function buildFallbackRecordGraph(recordId = SAMPLE_RECORD_ID) {
  const normalizedRecordId = String(recordId || '').trim() || SAMPLE_RECORD_ID
  const serialized = JSON.stringify(fallbackRecordGraph).replaceAll(
    SAMPLE_RECORD_ID,
    normalizedRecordId
  )
  return JSON.parse(serialized)
}

export function buildFallbackNeighborGraph(nodeId, graph = {}) {
  const centerNode = (graph.nodes || []).find((node) => node.id === nodeId)
  if (!centerNode) return null

  const edges = (graph.edges || []).filter(
    (edge) => edge.source === nodeId || edge.target === nodeId
  )
  const nodeIds = new Set([nodeId])
  for (const edge of edges) {
    nodeIds.add(edge.source)
    nodeIds.add(edge.target)
  }

  return {
    node_id: nodeId,
    center_node: centerNode,
    nodes: (graph.nodes || []).filter((node) => nodeIds.has(node.id)),
    edges,
    depth: 1,
    limit: 100
  }
}

export function buildFallbackSourceDetail(node = {}) {
  const properties = node.properties || {}

  if (node.type === 'record') {
    const activeRecordId = node.record_id || String(node.id || '').replace(/^record:/, '')
    return {
      title: '记录源数据（演示）',
      recordId: activeRecordId,
      items: [
        { label: '题名', value: properties.title_reference || node.label },
        { label: '寄批人', value: properties.sender },
        { label: '收批人', value: properties.recipient },
        { label: '日期', value: properties.date_text || properties.date_standard }
      ]
    }
  }

  if (node.type === 'evidence') {
    return {
      title: '原始证据片段（演示）',
      recordId: node.record_id || '',
      items: [
        { label: '证据 ID', value: node.source_id },
        { label: '证据类型', value: properties.evidence_type },
        { label: '来源字段', value: properties.source_column },
        { label: '原文', value: properties.evidence_text || node.label }
      ]
    }
  }

  if (node.type === 'metadata_record') {
    return {
      title: '目录元数据（演示）',
      recordId: properties.linked_record_id || node.record_id || '',
      items: [
        { label: '元数据 ID', value: node.source_id },
        { label: '题名', value: properties.title_clean || node.label },
        { label: '寄件人', value: properties.sender_raw },
        { label: '收件人', value: properties.recipient_raw },
        { label: '日期', value: properties.date_text || properties.date_standard },
        {
          label: '全文关联',
          value: properties.linked_record_id || node.record_id || '未关联全文'
        }
      ]
    }
  }

  return null
}
