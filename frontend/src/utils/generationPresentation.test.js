import test from 'node:test'
import assert from 'node:assert/strict'

import { generationState } from './generationPresentation.js'

test('generation state explicitly identifies scaffold degradation', () => {
  const state = generationState({
    generation_backend: 'deterministic_local',
    model: 'deterministic-local-v1',
    prompt_version: 'interpret-json-v2',
    index_version: 'rel:abc',
    cache_hit: true,
    degraded_reason: 'scaffold_phase_active'
  })

  assert.equal(state.backendLabel, '确定性本地降级')
  assert.equal(state.degraded, true)
  assert.match(state.degradedLabel, /Scaffold/)
  assert.equal(state.cacheLabel, '缓存命中')
})

test('generation state distinguishes a successful Qwen response', () => {
  const state = generationState({
    generation_backend: 'qwen',
    model: 'qwen-plus',
    cache_hit: false
  })

  assert.equal(state.backendLabel, 'Qwen 在线生成')
  assert.equal(state.degraded, false)
  assert.equal(state.cacheLabel, '新生成')
})
