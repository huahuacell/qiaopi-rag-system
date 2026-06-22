const trueValues = new Set(['1', 'true', 'yes', 'on'])

export const demoMode = trueValues.has(
  String(import.meta.env.VITE_DEMO_MODE || '').trim().toLowerCase()
)

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function apiFailureMessage(error, action = '请求') {
  const backendDetail = error?.response?.data?.detail
  const isConnectionFailure =
    !error?.response &&
    (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK')
  const detail =
    typeof backendDetail === 'string'
      ? backendDetail
      : isConnectionFailure
        ? `无法连接后端 ${apiBaseUrl}，请在 backend 目录运行 uvicorn main:app --reload`
      : error?.code === 'ECONNABORTED'
        ? '请求超时'
        : error?.message

  return `${action}失败${detail ? `：${detail}` : ''}。未使用本地 Mock 回退。`
}

export function demoFailureMessage(action = '请求') {
  return `${action}未连接后端；当前由 VITE_DEMO_MODE=true 显式启用本地演示数据。`
}
