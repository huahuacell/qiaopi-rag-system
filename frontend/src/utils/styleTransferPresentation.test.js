import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildStyleTransferValidationCards,
  normalizeStyleTransferCheck
} from './styleTransferPresentation.js'

test('validation cards do not turn person red because another check failed', () => {
  const consistency = normalizeStyleTransferCheck({
    validation_report: {
      is_consistent: false,
      risk_level: 'medium',
      checks: [
        {
          name: 'recipient_consistency',
          status: 'pass',
          message: '夫妻关系保持一致。'
        },
        {
          name: 'remittance_expression',
          status: 'warn',
          message: '缺少寄款表达。'
        }
      ],
      possible_hallucinations: [],
      missing_required_facts: ['缺少寄款表达'],
      unsupported_new_facts: []
    }
  })

  const cards = buildStyleTransferValidationCards(consistency)
  assert.equal(cards.find((item) => item.label === '人物一致').status, 'pass')
  assert.equal(cards.find((item) => item.label === '生成边界').status, 'warn')
})

test('recipient failure is isolated to the person card', () => {
  const cards = buildStyleTransferValidationCards({
    checks: [
      {
        name: 'recipient_consistency',
        status: 'fail',
        message: '收信关系发生改变。'
      },
      {
        name: 'amount_consistency',
        status: 'pass',
        message: '金额一致。'
      }
    ]
  })

  assert.equal(cards.find((item) => item.label === '人物一致').status, 'fail')
  assert.equal(cards.find((item) => item.label === '金额一致').status, 'pass')
})
