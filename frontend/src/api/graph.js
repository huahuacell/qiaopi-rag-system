import request from './request'

export async function fetchGraphStats() {
  const response = await request.get('/api/graph/stats')
  return response.data
}

export async function fetchRecordGraph(recordId) {
  const response = await request.get(`/api/graph/record/${encodeURIComponent(recordId)}`)
  return response.data
}

export async function fetchNodeNeighbors(nodeId, options = {}) {
  const response = await request.get(
    `/api/graph/node/${encodeURIComponent(nodeId)}/neighbors`,
    {
      params: {
        depth: options.depth || 1,
        limit: options.limit || 80
      }
    }
  )
  return response.data
}

export async function fetchGraphOverview(options = {}) {
  const response = await request.get('/api/graph/overview', {
    params: {
      limit_nodes: options.limitNodes || 80,
      limit_edges: options.limitEdges || 140
    }
  })
  return response.data
}

export async function fetchPlaceFlows(limit = 30) {
  const response = await request.get('/api/graph/flows/places', {
    params: { limit }
  })
  return response.data
}
