import request from './request'

export async function fetchRecordDetail(recordId) {
  const response = await request.get(`/api/records/${recordId}`)
  return response.data
}

export async function fetchRecordEntities(recordId) {
  const response = await request.get(`/api/records/${recordId}/entities`)
  return response.data
}

export async function fetchRecordEvidence(recordId) {
  const response = await request.get(`/api/records/${recordId}/evidence`)
  return response.data
}
