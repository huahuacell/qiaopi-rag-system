import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildCorpusKeywordCloud,
  buildEmotionKeywordCloud,
  layoutCorpusKeywordCloud,
  normalizeEmotionDistribution,
  selectCooccurrenceEvidenceExamples,
  selectEmotionEvidenceExamples,
  selectKeywordEvidenceExamples,
  selectValenceEvidenceExamples,
  selectTypicalEmotionEvidence
} from './emotionClassification.js'

test('selectTypicalEmotionEvidence prefers reviewed-safe high-confidence evidence', () => {
  const selected = selectTypicalEmotionEvidence([
    {
      record_id: 'B',
      emotion_key: 'care',
      text: '较高但待复核',
      confidence: 0.95,
      needs_review: true
    },
    {
      record_id: 'A',
      emotion_key: 'care',
      text: '可靠证据',
      confidence: 0.82,
      needs_review: false
    }
  ], 'care')

  assert.equal(selected.record_id, 'A')
})

test('buildEmotionKeywordCloud uses only trigger terms found in source text', () => {
  const words = buildEmotionKeywordCloud([
    {
      record_id: 'R1',
      text: '两方平安，甚为喜乐。',
      trigger_terms: ['平安', '喜乐', '不存在'],
      confidence: 0.8
    },
    {
      record_id: 'R2',
      text: '家中平安。',
      trigger_terms: ['平安'],
      confidence: 0.6
    }
  ])

  assert.deepEqual(words.map((item) => item.label), ['平安', '喜乐'])
  assert.equal(words[0].termFrequency, 2)
  assert.equal(words[0].segmentFrequency, 2)
  assert.equal(words[0].score, 1.4)
})

test('buildCorpusKeywordCloud counts only Chinese keywords present in full text', () => {
  const words = buildCorpusKeywordCloud([
    {
      record_id: 'R1',
      has_full_text: 1,
      body_core: '家中平安，寄信后请查收。',
      retrieval_keywords: '家中；平安；寄信；查收；family_affection；新加坡'
    },
    {
      record_id: 'R2',
      has_full_text: 1,
      body_core: '遥祝家中平安，收到寄信后回音。',
      retrieval_keywords: '家中；平安；寄信；回音；海外'
    },
    {
      record_id: 'R3',
      has_full_text: 0,
      body_clean: '家中平安',
      retrieval_keywords: '家中；平安'
    }
  ])

  assert.deepEqual(words.map((item) => item.label), ['寄信', '家中', '平安'])
  assert.equal(words.find((item) => item.label === '家中').termFrequency, 2)
  assert.equal(words.find((item) => item.label === '家中').recordCount, 2)
  assert.equal(words.some((item) => item.label === '新加坡'), false)
})

test('selectEmotionEvidenceExamples waits for a selection and caps results at nine', () => {
  const examples = Array.from({ length: 12 }, (_, index) => ({
    record_id: `R${index + 1}`,
    emotion_key: 'care',
    text: `证据${index + 1}`,
    confidence: 0.9 - index * 0.01,
    needs_review: false
  }))

  assert.deepEqual(selectEmotionEvidenceExamples(examples, ''), [])
  assert.equal(selectEmotionEvidenceExamples(examples, 'care').length, 9)
  assert.equal(selectEmotionEvidenceExamples(examples, 'care')[0].record_id, 'R1')
})

test('layoutCorpusKeywordCloud is deterministic and scatters positions', () => {
  const words = Array.from({ length: 12 }, (_, index) => ({
    label: `词语${index}`,
    score: 20 - index,
    size: 34 - index,
    color: '#123456',
    weight: 600
  }))

  const first = layoutCorpusKeywordCloud(words)
  const second = layoutCorpusKeywordCloud(words)

  assert.deepEqual(first, second)
  assert.equal(new Set(first.map((item) => `${item.left}:${item.top}`)).size, 12)
  assert.ok(first.every((item) => item.left > 0 && item.left < 100))
  assert.ok(first.every((item) => item.top > 0 && item.top < 100))
})

test('valence and cooccurrence selections return matching evidence', () => {
  const examples = [
    { record_id: 'R1', emotion_key: 'a', valence: 'positive', text: '甲', confidence: 0.8 },
    { record_id: 'R1', emotion_key: 'b', valence: 'neutral', text: '乙', confidence: 0.7 },
    { record_id: 'R2', emotion_key: 'a', valence: 'positive', text: '丙', confidence: 0.9 }
  ]

  assert.deepEqual(
    selectValenceEvidenceExamples(examples, 'positive').map((item) => item.text),
    ['丙', '甲']
  )
  assert.deepEqual(
    selectCooccurrenceEvidenceExamples(examples, 'a', 'b').map((item) => item.record_id),
    ['R1', 'R1', 'R2']
  )
})

test('keyword selection creates traceable snippets from full text', () => {
  const examples = selectKeywordEvidenceExamples([
    {
      record_id: 'R1',
      year_normalized: '1936',
      body_core: '遥祝家中平安，收到寄信后请回音。'
    },
    {
      record_id: 'R2',
      body_core: '此处没有目标词。'
    }
  ], '平安')

  assert.equal(examples.length, 1)
  assert.equal(examples[0].record_id, 'R1')
  assert.equal(examples[0].year, '1936')
  assert.equal(examples[0].emotion_label, '关键词：平安')
  assert.match(examples[0].text, /平安/)
})

test('normalizeEmotionDistribution produces display percentages totaling 100', () => {
  const normalized = normalizeEmotionDistribution([
    { key: 'a', record_count: 202 },
    { key: 'b', record_count: 139 },
    { key: 'c', record_count: 111 }
  ])

  assert.equal(
    normalized.reduce((sum, item) => sum + item.display_percent, 0),
    100
  )
  assert.ok(
    Math.abs(normalized.reduce((sum, item) => sum + item.normalized_ratio, 0) - 1) <
      Number.EPSILON * 10
  )
})
