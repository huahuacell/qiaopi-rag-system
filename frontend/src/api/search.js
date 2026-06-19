import request from './request'

const SEMANTIC_SEARCH_TIMEOUT_MS = 60_000

export async function keywordSearch(payload) {
  const response = await request.post('/api/search/keyword', payload)
  return response.data
}

export async function semanticSearch(payload) {
  const response = await request.post('/api/search/semantic', payload, {
    timeout: SEMANTIC_SEARCH_TIMEOUT_MS
  })
  return response.data
}

export async function hybridSearch(payload) {
  const response = await request.post('/api/search/hybrid', payload, {
    timeout: SEMANTIC_SEARCH_TIMEOUT_MS
  })
  return response.data
}
