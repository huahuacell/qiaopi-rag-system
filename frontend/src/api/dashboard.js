import request from './request'

export async function fetchDashboardStats() {
  const response = await request.get('/api/dashboard/stats')
  return response.data
}

