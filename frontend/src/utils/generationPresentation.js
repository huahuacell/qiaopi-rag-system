export const GENERATION_BACKEND_LABELS = {
  qwen: 'Qwen 在线生成',
  deepseek: 'DeepSeek 在线生成',
  deterministic_local: '本地降级模式',
  prompt_preview: '仅预览 Prompt'
}

export const DEGRADED_REASON_LABELS = {
  dry_run_requested: '请求指定仅预览 Prompt',
  scaffold_phase_active: 'Scaffold 阶段尚未明确结束，真实 Qwen 调用被安全门阻止',
  qwen_disabled: 'Qwen 在线生成未启用',
  qwen_api_key_missing: '未配置 Qwen API Key',
  qwen_base_url_missing: '未配置 Qwen 服务地址',
  qwen_timeout: 'Qwen 请求超时，已改用本地降级',
  qwen_request_error: 'Qwen 网络请求失败，已改用本地降级',
  qwen_invalid_structured_output: 'Qwen 未返回合法结构化结果，已改用本地降级',
  deepseek_disabled: 'DeepSeek 在线生成未启用，当前使用本地降级解读',
  deepseek_api_key_missing: '未配置 DeepSeek API Key，当前使用本地降级解读',
  deepseek_base_url_missing: '未配置 DeepSeek API 地址，当前使用本地降级解读',
  deepseek_timeout: 'DeepSeek API 调用超时，已使用本地降级解读',
  deepseek_request_error: 'DeepSeek API 调用失败，已使用本地降级解读',
  deepseek_invalid_structured_output: 'DeepSeek 未返回有效结果，已使用本地降级解读'
}

export function generationState(result = {}) {
  const backend = result.generation_backend || ''
  const degradedReason = result.degraded_reason || ''
  return {
    backend,
    backendLabel: GENERATION_BACKEND_LABELS[backend] || backend || '尚未生成',
    degraded: Boolean(degradedReason) || backend === 'deterministic_local',
    degradedLabel: degradedReasonLabel(degradedReason, backend),
    cacheLabel: result.cache_hit ? '缓存命中' : '新生成',
    modelLabel: result.model || '—',
    promptVersion: result.prompt_version || '—',
    indexVersion: result.index_version || '—'
  }
}

function degradedReasonLabel(reason, backend) {
  if (DEGRADED_REASON_LABELS[reason]) return DEGRADED_REASON_LABELS[reason]
  if (reason.startsWith('deepseek_http_')) {
    return `DeepSeek API 返回 HTTP ${reason.slice('deepseek_http_'.length)}，已使用本地降级解读`
  }
  return reason || (backend === 'deterministic_local' ? '当前使用本地降级解读' : '')
}
