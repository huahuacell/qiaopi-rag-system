import request from './request'

export async function fetchEmotionAnalysis() {
  const response = await request.get('/api/analysis/emotions')
  return response.data
}

