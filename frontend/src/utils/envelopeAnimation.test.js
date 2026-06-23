import assert from 'node:assert/strict'
import test from 'node:test'

import {
  ENVELOPE_STATES,
  envelopeSequence,
  isEnvelopeAnimating
} from './envelopeAnimation.js'

test('full envelope sequence is ordered and ends sealed', () => {
  const sequence = envelopeSequence(false)

  assert.deepEqual(
    sequence.map((step) => step.state),
    ['folding', 'inserting', 'sealing', 'sealed']
  )
  assert.equal(sequence.at(-1).at, 2240)
  assert.ok(sequence.every((step, index) => index === 0 || step.at > sequence[index - 1].at))
})

test('reduced motion skips directly to sealed state', () => {
  assert.deepEqual(envelopeSequence(true), [{ state: ENVELOPE_STATES.SEALED, at: 0 }])
})

test('only transitional states are marked as animating', () => {
  assert.equal(isEnvelopeAnimating(ENVELOPE_STATES.FOLDING), true)
  assert.equal(isEnvelopeAnimating(ENVELOPE_STATES.INSERTING), true)
  assert.equal(isEnvelopeAnimating(ENVELOPE_STATES.SEALING), true)
  assert.equal(isEnvelopeAnimating(ENVELOPE_STATES.SEALED), false)
  assert.equal(isEnvelopeAnimating(ENVELOPE_STATES.IDLE), false)
})
