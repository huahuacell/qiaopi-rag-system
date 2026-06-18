import request from './request'

export async function generatePlainInterpretation(payload) {
  const response = await request.post('/api/generation/plain-interpretation', payload)
  return response.data
}

export async function generateStyleTransfer(payload) {
  const response = await request.post('/api/generation/style-transfer', payload)
  return response.data
}
