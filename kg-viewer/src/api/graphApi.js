import axios from 'axios'

function normalizeBaseUrl(baseUrl) {
  return (baseUrl || 'http://localhost:8000').trim().replace(/\/+$/, '')
}

async function requestGraph(baseUrl, path, options = {}) {
  try {
    const response = await axios.get(`${normalizeBaseUrl(baseUrl)}${path}`, {
      timeout: 15000,
      ...options
    })
    return response.data
  } catch (error) {
    const detail = error.response?.data?.detail
    const message = detail || error.message || '图谱 API 请求失败。'
    throw new Error(message)
  }
}

export function getGraphStats(baseUrl) {
  return requestGraph(baseUrl, '/api/graph/stats')
}

export function getRecordGraph(baseUrl, recordId) {
  return requestGraph(baseUrl, `/api/graph/record/${encodeURIComponent(recordId)}`)
}

export function getOverviewGraph(baseUrl) {
  return requestGraph(baseUrl, '/api/graph/overview')
}

export function getPlaceFlows(baseUrl, limit = 50) {
  return requestGraph(baseUrl, '/api/graph/flows/places', {
    params: { limit }
  })
}

export function getNodeNeighbors(baseUrl, nodeId, depth = 1, limit = 50) {
  return requestGraph(baseUrl, `/api/graph/node/${encodeURIComponent(nodeId)}/neighbors`, {
    params: { depth, limit }
  })
}
