import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildScoreContributions,
  resolveSearchExecution
} from './searchPresentation.js'

test('hybrid keyword fallback is labelled as degraded keyword retrieval', () => {
  const state = resolveSearchExecution('hybrid', {
    semantic_enabled: false,
    semantic_quality: 'disabled',
    fusion_method: 'keyword_fallback',
    error_message: 'Semantic index is unavailable.'
  })

  assert.equal(state.effectiveMode, 'keyword')
  assert.equal(state.effectiveLabel, '关键词检索（混合降级）')
  assert.equal(state.degraded, true)
  assert.deepEqual(state.sources, ['FTS5 / BM25'])
})

test('semantic failure is not represented as semantic results', () => {
  const state = resolveSearchExecution('semantic', {
    semantic_enabled: false,
    semantic_quality: 'disabled',
    results: []
  })

  assert.equal(state.effectiveMode, 'unavailable')
  assert.equal(state.effectiveLabel, '语义检索不可用')
  assert.equal(state.degraded, true)
})

test('validated RRF response is represented as production hybrid retrieval', () => {
  const state = resolveSearchExecution('hybrid', {
    semantic_enabled: true,
    semantic_quality: 'production',
    fusion_method: 'rrf'
  })

  assert.equal(state.effectiveMode, 'hybrid')
  assert.equal(state.effectiveLabel, '混合检索')
  assert.equal(state.degraded, false)
})

test('score contributions keep BM25 cosine and RRF on separate scales', () => {
  const state = resolveSearchExecution('hybrid', {
    semantic_enabled: true,
    semantic_quality: 'production',
    fusion_method: 'rrf'
  })
  const rows = buildScoreContributions(
    {
      bm25_score: -8.1234,
      semantic_score: 0.812345,
      final_score: 0.031746,
      retrieval_sources: ['keyword', 'semantic']
    },
    state
  )

  assert.deepEqual(
    rows.map((row) => row.label),
    ['BM25 原始值', '余弦相似度', 'RRF 融合值']
  )
  assert.ok(rows.every((row) => !row.value.includes('%')))
})
