import assert from 'node:assert/strict'
import test from 'node:test'

import {
  normalizeEmotionAnalysis,
  percentText
} from './emotionPresentation.js'

test('normalizeEmotionAnalysis supplies stable empty collections', () => {
  const normalized = normalizeEmotionAnalysis(null)

  assert.deepEqual(normalized.label_distribution, [])
  assert.equal(normalized.valence_distribution.length, 4)
  assert.equal(normalized.model.model_version, 'unavailable')
})

test('normalizeEmotionAnalysis clamps ratios and sorts emotion counts', () => {
  const normalized = normalizeEmotionAnalysis({
    label_distribution: [
      { key: 'low', record_count: 2, ratio: -1, average_confidence: 4 },
      { key: 'high', record_count: 8, ratio: 2, average_confidence: 0.8 }
    ],
    valence_distribution: [
      { key: 'mixed', label: '复合情感', record_count: 3, ratio: 0.3 }
    ]
  })

  assert.equal(normalized.label_distribution[0].key, 'high')
  assert.equal(normalized.label_distribution[0].ratio, 1)
  assert.equal(normalized.label_distribution[1].ratio, 0)
  assert.equal(normalized.label_distribution[1].average_confidence, 1)
  assert.equal(normalized.valence_distribution.find((item) => item.key === 'mixed').record_count, 3)
})

test('percentText formats a bounded percentage', () => {
  assert.equal(percentText(0.126, 1), '12.6%')
  assert.equal(percentText(4), '100%')
})

