import request from './request'

export async function generateInterpretation(payload) {
  const response = await request.post('/api/generation/interpret', payload)
  return response.data
}

export async function generateStyleTransfer(payload) {
  const response = await request.post('/api/generation/style-transfer', payload)
  return response.data
}
