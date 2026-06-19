import test from 'node:test'
import assert from 'node:assert/strict'

import { formatOffset, validateSpanItem } from './nlpPresentation.js'

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
