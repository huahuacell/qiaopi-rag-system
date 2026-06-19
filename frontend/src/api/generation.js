import request from './request'

// Qwen allows up to 120 seconds per attempt and the backend may retry twice.
// Keep the browser request alive across all attempts plus retry backoff.
const GENERATION_TIMEOUT_MS = 370_000

export async function generateInterpretation(payload) {
  const response = await request.post('/api/generation/interpret', payload, {
    timeout: GENERATION_TIMEOUT_MS
  })
  return response.data
}

export async function generateStyleTransfer(payload) {
  const response = await request.post('/api/generation/style-transfer', payload, {
    timeout: GENERATION_TIMEOUT_MS
  })
  return response.data
}
