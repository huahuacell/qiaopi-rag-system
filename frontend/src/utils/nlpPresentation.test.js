import test from 'node:test'
import assert from 'node:assert/strict'

import {
  confidenceText,
  formatOffset,
  nlpValueText,
  normalizeNlpResult,
  validateSpanItem
} from './nlpPresentation.js'

test('NLP span presentation uses half-open offsets and validates source text', () => {
  const item = {
    source_text: '星洲',
    normalized_source_text: '星洲',
    original_start: 3,
    original_end: 5,
    normalized_start: 2,
    normalized_end: 4
  }

  assert.equal(formatOffset(item), '原文 [3, 5)')
  assert.equal(formatOffset(item, true), '规范 [2, 4)')
  assert.equal(validateSpanItem(item, '我在 星洲', '我在星洲'), true)
  assert.equal(validateSpanItem(item, '我在 暹罗', '在星洲'), false)
})

test('NLP span validation rejects invalid and out-of-range offsets', () => {
  const item = {
    source_text: '星洲',
    normalized_source_text: '星洲',
    original_start: -1,
    original_end: 2,
    normalized_start: 0,
    normalized_end: 2
  }

  assert.equal(validateSpanItem(item, '星洲', '星洲'), false)
  assert.equal(
    validateSpanItem(
      { ...item, original_start: 0, original_end: 3 },
      '星洲',
      '星洲'
    ),
    false
  )
})

test('NLP result normalization keeps lists and summary safe for presentation', () => {
  const result = normalizeNlpResult({
    task: 'general',
    entities: [{ needs_review: true }],
    relations: null,
    slots: undefined
  })

  assert.equal(result.task, 'general')
  assert.equal(result.summary.entity_count, 1)
  assert.equal(result.summary.relation_count, 0)
  assert.equal(result.summary.review_item_count, 1)
  assert.deepEqual(result.relations, [])
  assert.deepEqual(result.review_reasons, [])
  assert.equal(confidenceText(1.4), '100%')
  assert.equal(confidenceText(-0.2), '0%')
})

test('NLP coded values are translated for user-facing presentation', () => {
  assert.equal(nlpValueText('household_expenses'), '家庭生活开支')
  assert.equal(nlpValueText('writes_to'), '寄件人写给收件人')
  assert.equal(nlpValueText('recipient:unspecified'), '收件人（未明确）')
  assert.equal(nlpValueText('儿海泉'), '儿海泉')
})
