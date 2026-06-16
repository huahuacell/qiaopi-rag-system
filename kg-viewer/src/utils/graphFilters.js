const DEFAULT_PRIORITY = ['record', 'person', 'place', 'amount', 'date', 'theme', 'metadata_record', 'evidence']
const RECORD_GRAPH_TYPES = new Set(['record', 'metadata_record', 'person', 'place', 'amount', 'date', 'theme', 'evidence'])

export function buildOverviewDisplayGraph(payload, options = {}) {
  const includeEvidence = options.includeEvidence === true
  const maxNodes = options.maxNodes || 60
  const maxEdges = options.maxEdges || 100
  const nodes = Array.isArray(payload?.nodes) ? payload.nodes : []
  const edges = Array.isArray(payload?.edges) ? payload.edges : []

  const selectedNodes = nodes
    .filter((node) => includeEvidence || nodeType(node) !== 'evidence')
    .map((node, index) => ({ node, index }))
    .sort((left, right) => {
      const priorityDiff = nodePriority(left.node) - nodePriority(right.node)
      return priorityDiff || left.index - right.index
    })
    .slice(0, maxNodes)
    .map((item) => item.node)

  return withFilteredEdges(selectedNodes, edges, maxEdges)
}

export function buildRecordDisplayGraph(payload, options = {}) {
  const includeEvidence = options.includeEvidence === true
  const nodes = Array.isArray(payload?.nodes) ? payload.nodes : []
  const edges = Array.isArray(payload?.edges) ? payload.edges : []
  const selectedNodes = nodes.filter((node) => {
    const type = nodeType(node)
    if (!includeEvidence && type === 'evidence') return false
    return RECORD_GRAPH_TYPES.has(type)
  })

  return withFilteredEdges(selectedNodes, edges)
}

function withFilteredEdges(nodes, edges, maxEdges = Number.POSITIVE_INFINITY) {
  const nodeIds = new Set(nodes.map((node) => node.id))
  const selectedEdges = edges
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .slice(0, maxEdges)
  return { nodes, edges: selectedEdges }
}

function nodePriority(node) {
  const index = DEFAULT_PRIORITY.indexOf(nodeType(node))
  return index >= 0 ? index : DEFAULT_PRIORITY.length
}

function nodeType(node) {
  return node?.node_type || node?.type || node?.category || ''
}
