import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildRecordMetadataRows,
  buildRelatedArchiveItems,
  formatRecordMetadataValue
} from './recordDetailPresentation.js'

test('record metadata uses Chinese labels and localizes controlled values', () => {
  const rows = buildRecordMetadataRows(
    {
      title_reference: '新加坡寄往潮州的家书',
      sender: '陈生',
      recipient: '母亲',
      main_intent: 'remittance',
      relationship_type: 'son_to_parent',
      theme_tags: 'theme_remittance；theme_family_affection',
      text_quality_level: 'high',
      has_full_text: 1,
      raw_fields: { main_intent: 'remittance' }
    },
    'CSQP-SFHC-TEXT-017'
  )

  assert.deepEqual(
    rows.map(({ label, value }) => [label, value]),
    [
      ['记录编号', 'CSQP-SFHC-TEXT-017'],
      ['题名', '新加坡寄往潮州的家书'],
      ['寄信人', '陈生'],
      ['收信人', '母亲'],
      ['人物关系', '儿子致父母'],
      ['是否有全文', '是'],
      ['主要内容', '汇款'],
      ['主题标签', '汇款、亲情'],
      ['文本质量', '高']
    ]
  )
  assert.ok(rows.every((row) => !row.label.includes('_')))
})

test('metadata value formatter handles arrays and boolean fields', () => {
  assert.equal(formatRecordMetadataValue('theme_tags', ['theme_remittance', 'theme_greeting']), '汇款、问候')
  assert.equal(formatRecordMetadataValue('has_remittance', 0), '否')
})

test('related archive clues link to search with record-specific keywords', () => {
  const items = buildRelatedArchiveItems({
    metadata: {
      origin_place: '新加坡',
      relationship_type: '子女与父母'
    },
    main_intent: '汇款与平安问候'
  })

  assert.deepEqual(items.map((item) => item.to), [
    { path: '/search', query: { query: '新加坡' } },
    { path: '/search', query: { query: '子女与父母' } },
    { path: '/search', query: { query: '汇款' } }
  ])
})

test('kinship clue falls back to a related person and missing origin stays non-clickable', () => {
  const items = buildRelatedArchiveItems({ recipient_name_clean: '陈氏' })

  assert.equal(items[0].to, null)
  assert.deepEqual(items[1].to, {
    path: '/search',
    query: { query: '陈氏' }
  })
  assert.deepEqual(items[2].to, {
    path: '/search',
    query: { query: '汇款' }
  })
})
