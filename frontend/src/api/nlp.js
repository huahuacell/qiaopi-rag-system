import request from './request'

export async function analyzeNlpText(text, task = 'general') {
  const response = await request.post('/api/nlp/analyze', { text, task })
  return response.data
}
