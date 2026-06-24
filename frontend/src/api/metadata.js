import request from './request'

const METADATA_SEARCH_TIMEOUT_MS = 60_000

export async function searchMetadata(payload) {
  const response = await request.post('/api/metadata/search', payload, {
    timeout: METADATA_SEARCH_TIMEOUT_MS
  })
  return response.data
}

export async function fetchMetadataDetail(metadataId) {
  const response = await request.get(`/api/metadata/${encodeURIComponent(metadataId)}`)
  return response.data
}

export async function fetchMetadataLinkedText(metadataId) {
  const response = await request.get(
    `/api/metadata/${encodeURIComponent(metadataId)}/linked-text`
  )
  return response.data
}
