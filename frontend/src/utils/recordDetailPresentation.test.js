import assert from 'node:assert/strict'
import test from 'node:test'

import { buildRelatedArchiveItems } from './recordDetailPresentation.js'

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
