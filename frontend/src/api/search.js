import request from './request'

export async function keywordSearch(payload) {
  const response = await request.post('/api/search/keyword', payload)
  return response.data
}

export async function semanticSearch(payload) {
  const response = await request.post('/api/search/semantic', payload)
  return response.data
}

export async function hybridSearch(payload) {
  const response = await request.post('/api/search/hybrid', payload)
  return response.data
}

