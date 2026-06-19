import assert from 'node:assert/strict'
import test from 'node:test'

import {
  recordBodyText,
  shouldReplaceOriginalText
} from './recordTextAutofill.js'

test('record body prefers full cleaned text before core text', () => {
  assert.equal(
    recordBodyText({
      body_clean: '完整正文',
      body_core: '核心正文'
    }),
    '完整正文'
  )
})

test('empty or previously auto-filled text can be replaced', () => {
  assert.equal(
    shouldReplaceOriginalText({
      currentText: '',
      manuallyEdited: true,
      lastAutoFilledText: ''
    }),
    true
  )
  assert.equal(
    shouldReplaceOriginalText({
      currentText: '旧档案正文',
      manuallyEdited: false,
      lastAutoFilledText: '旧档案正文'
    }),
    true
  )
})

test('pasted or manually edited text is preserved during record lookup', () => {
  assert.equal(
    shouldReplaceOriginalText({
      currentText: '用户粘贴的侨批原文',
      manuallyEdited: true,
      lastAutoFilledText: '旧档案正文'
    }),
    false
  )
})
