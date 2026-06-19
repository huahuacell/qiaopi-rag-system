import request from './request'

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
