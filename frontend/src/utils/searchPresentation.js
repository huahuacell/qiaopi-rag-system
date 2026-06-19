const MODE_LABELS = {
  keyword: '关键词检索',
  semantic: '语义检索',
  hybrid: '混合检索'
}

function finiteNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function formatScore(value) {
  const number = finiteNumber(value)
  if (number === null) return '—'
  if (Math.abs(number) >= 100) return number.toFixed(2)
  if (Math.abs(number) >= 1) return number.toFixed(4)
  return number.toFixed(6)
}

export function resolveSearchExecution(requestedMode, response = {}, options = {}) {
  const semanticEnabled = response.semantic_enabled === true
  const semanticQuality = response.semantic_quality || 'disabled'
  const fusionMethod = response.fusion_method || null
  const isDemo = options.demoMode === true || response.demo_mode === true

  const common = {
    requestedMode,
    requestedLabel: MODE_LABELS[requestedMode] || requestedMode,
    semanticEnabled,
    semanticQuality,
    fusionMethod,
    isDemo,
    backendMessage: response.error_message || '',
    dataLabel: isDemo ? '显式演示数据' : '正式接口数据'
  }

  if (options.requestFailed === true) {
    return {
      ...common,
      effectiveMode: 'unavailable',
      effectiveLabel: '检索服务不可用',
      tone: 'danger',
      degraded: true,
      sources: [],
      explanation: options.failureMessage || '未收到后端检索响应。',
      dataLabel: '无数据（接口失败）'
    }
  }

  if (requestedMode === 'keyword') {
    return {
      ...common,
      effectiveMode: 'keyword',
      effectiveLabel: '关键词检索',
      tone: 'success',
      degraded: false,
      sources: ['FTS5 / BM25'],
      explanation: '本次排序由关键词召回与后端重排产生。'
    }
  }

  if (requestedMode === 'semantic') {
    if (!semanticEnabled) {
      return {
        ...common,
        effectiveMode: 'unavailable',
        effectiveLabel: '语义检索不可用',
        tone: 'danger',
        degraded: true,
        sources: [],
        explanation:
          response.error_message ||
          '后端未执行语义检索，也没有把关键词结果伪装成语义结果。'
      }
    }

    const testOnly = semanticQuality === 'test_hash'
    return {
      ...common,
      effectiveMode: 'semantic',
      effectiveLabel: testOnly ? '语义检索（测试向量）' : '语义检索',
      tone: testOnly ? 'warning' : 'success',
      degraded: testOnly,
      sources: ['向量余弦相似度'],
      explanation: testOnly
        ? '当前使用确定性 Hash 测试向量，仅用于流程验证，不代表生产语义质量。'
        : '本次排序由已通过清单校验的语义向量相似度产生。'
    }
  }

  if (requestedMode === 'hybrid') {
    if (semanticEnabled && fusionMethod === 'rrf') {
      const testOnly = semanticQuality === 'test_hash'
      return {
        ...common,
        effectiveMode: 'hybrid',
        effectiveLabel: testOnly ? '混合检索（测试向量）' : '混合检索',
        tone: testOnly ? 'warning' : 'success',
        degraded: testOnly,
        sources: ['FTS5 / BM25', '向量余弦相似度', 'RRF 排名融合'],
        explanation: testOnly
          ? '关键词与 Hash 测试向量通过 RRF 融合；仅用于演示和测试。'
          : '关键词排名与语义排名通过 RRF 融合，分数只表示本次排序贡献。'
      }
    }

    return {
      ...common,
      effectiveMode: 'keyword',
      effectiveLabel: '关键词检索（混合降级）',
      tone: 'warning',
      degraded: true,
      sources: ['FTS5 / BM25'],
      explanation:
        response.error_message ||
        '语义检索未参与，本次返回的是关键词结果，不是混合检索结果。'
    }
  }

  return {
    ...common,
    effectiveMode: requestedMode,
    effectiveLabel: MODE_LABELS[requestedMode] || requestedMode,
    tone: 'info',
    degraded: false,
    sources: [],
    explanation: '未识别的检索模式。'
  }
}

export function buildScoreContributions(result = {}, execution = {}) {
  const sources = new Set(result.retrieval_sources || [])
  const rows = []
  const bm25 = finiteNumber(result.bm25_score)
  const semantic = finiteNumber(result.semantic_score)
  const finalScore = finiteNumber(result.final_score)

  if ((sources.has('keyword') || execution.effectiveMode === 'keyword') && bm25 !== null) {
    rows.push({
      key: 'bm25',
      label: 'BM25 原始值',
      value: formatScore(bm25),
      meaning: 'SQLite FTS5 信号；同一查询内值越小，关键词排名通常越靠前。'
    })
  }

  if (
    (sources.has('semantic') || execution.effectiveMode === 'semantic') &&
    semantic !== null &&
    semantic !== 0
  ) {
    rows.push({
      key: 'semantic',
      label: '余弦相似度',
      value: formatScore(semantic),
      meaning: '向量方向相似度；同一模型和语料内值越大，语义越接近。'
    })
  }

  if (execution.fusionMethod === 'rrf' && finalScore !== null) {
    rows.push({
      key: 'rrf',
      label: 'RRF 融合值',
      value: formatScore(finalScore),
      meaning: '由关键词名次和语义名次共同贡献；不是概率，也不能与余弦值直接比较。'
    })
  } else if (execution.effectiveMode === 'keyword' && finalScore !== null) {
    rows.push({
      key: 'keyword-rerank',
      label: '关键词重排值',
      value: formatScore(finalScore),
      meaning: '后端综合 BM25、命中覆盖和单元类型后的本次查询排序值。'
    })
  } else if (execution.effectiveMode === 'semantic' && !rows.length && finalScore !== null) {
    rows.push({
      key: 'semantic',
      label: '余弦相似度',
      value: formatScore(finalScore),
      meaning: '向量方向相似度；同一模型和语料内值越大，语义越接近。'
    })
  }

  return rows
}

export function buildDemoSearchResponse(baseResponse, requestedMode, query) {
  const semanticEnabled = requestedMode !== 'keyword'
  const fusionMethod = requestedMode === 'hybrid' ? 'rrf' : null

  return {
    ...baseResponse,
    query,
    demo_mode: true,
    semantic_enabled: semanticEnabled,
    semantic_quality: semanticEnabled ? 'test_hash' : 'disabled',
    fusion_method: fusionMethod,
    error_message: null,
    results: (baseResponse.results || []).map((result, index) => {
      const demoScore = finiteNumber(result.score) ?? Math.max(0.1, 0.9 - index * 0.08)
      const sources =
        requestedMode === 'hybrid'
          ? ['keyword', 'semantic']
          : requestedMode === 'semantic'
            ? ['semantic']
            : ['keyword']

      return {
        ...result,
        unit_id: result.unit_id || `${result.record_id}-DEMO-${index + 1}`,
        unit_type: result.unit_type || 'body_core',
        title_reference: result.title_reference || result.title || result.record_id,
        date_text: result.date_text || result.date || '',
        main_intent: result.main_intent || 'demo',
        unit_text: result.unit_text || result.snippet || '',
        matched_text: result.matched_text || result.snippet || '',
        matched_reason: result.matched_reason || result.evidence?.[0]?.reason || '显式演示数据命中',
        source_column: result.source_column || result.evidence?.[0]?.source_field || 'demo',
        evidence_type: result.evidence_type || 'demo',
        bm25_score: sources.includes('keyword') ? -demoScore : 0,
        semantic_score: sources.includes('semantic') ? demoScore : 0,
        final_score:
          requestedMode === 'hybrid' ? 1 / (60 + index + 1) * 2 : demoScore,
        retrieval_sources: sources
      }
    })
  }
}
