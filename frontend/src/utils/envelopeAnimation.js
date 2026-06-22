export const ENVELOPE_STATES = Object.freeze({
  IDLE: 'idle',
  FOLDING: 'folding',
  INSERTING: 'inserting',
  SEALING: 'sealing',
  SEALED: 'sealed'
})

export const ENVELOPE_SEQUENCE = Object.freeze([
  { state: ENVELOPE_STATES.FOLDING, at: 0 },
  { state: ENVELOPE_STATES.INSERTING, at: 620 },
  { state: ENVELOPE_STATES.SEALING, at: 1380 },
  { state: ENVELOPE_STATES.SEALED, at: 2240 }
])

export function envelopeSequence(reducedMotion = false) {
  if (reducedMotion) {
    return [{ state: ENVELOPE_STATES.SEALED, at: 0 }]
  }
  return ENVELOPE_SEQUENCE.map((step) => ({ ...step }))
}

export function isEnvelopeAnimating(state) {
  return [
    ENVELOPE_STATES.FOLDING,
    ENVELOPE_STATES.INSERTING,
    ENVELOPE_STATES.SEALING
  ].includes(state)
}
