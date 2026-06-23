import assert from 'node:assert/strict'
import test from 'node:test'

import { buildInterpretationSummary } from './interpretationSummary.js'

test('builds people place amount and topic cards from record and source evidence', () => {
  const cards = buildInterpretationSummary({
    record: {
      sender: '陈甲',
      recipient: '母亲',
      relationship_type: '母子',
      place_mentions_normalized: '新加坡、潮州',
      main_intent: '寄款家书',
      has_remittance: 1
    },
    sourceText: '托带荷银八元，请母亲查收。'
  })

  assert.equal(cards[0].value, '寄批人：陈甲；收批人：母亲；关系：母子')
  assert.equal(cards[1].value, '新加坡、潮州')
  assert.match(cards[2].value, /荷银八元/)
  assert.match(cards[3].value, /汇款/)
  assert.match(cards[3].value, /家书/)
  assert.match(cards[3].value, /收款/)
  assert.match(cards[3].value, /侨批往来/)
})

test('reads nested metadata used by record detail responses', () => {
  const cards = buildInterpretationSummary({
    record: {
      metadata: {
        sender: '陈生',
        recipient: '母亲',
        kinship: '母子',
        origin_place: '新加坡',
        destination_place: '广东潮州',
        money: '八元'
      }
    },
    sourceText: '今托水客附上银八元，望收讫。'
  })

  assert.match(cards[0].value, /陈生/)
  assert.match(cards[1].value, /新加坡/)
  assert.match(cards[2].value, /八元/)
  assert.match(cards[3].value, /收款/)
})

test('uses evidence references when record detail has limited fields', () => {
  const cards = buildInterpretationSummary({
    result: {
      evidence_references: [
        {
          unit_text: '侨居新加坡，兹寄洋银十元回潮州，至祈查收。',
          unit_type: 'remittance'
        }
      ]
    }
  })

  assert.match(cards[1].value, /新加坡/)
  assert.match(cards[1].value, /潮州/)
  assert.match(cards[2].value, /洋银十元/)
  assert.match(cards[3].value, /汇款/)
})

test('uses explicit empty-state copy instead of pending placeholders', () => {
  const cards = buildInterpretationSummary({})

  assert.deepEqual(
    cards.map((card) => card.value),
    [
      '未发现明确人物关系',
      '未发现明确地点',
      '未发现明确金额',
      '未发现明确主题'
    ]
  )
  assert.equal(cards.some((card) => card.value === '待提取'), false)
})
