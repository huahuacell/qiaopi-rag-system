import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const css = readFileSync(resolve('src/assets/styles/main.css'), 'utf8')

function ruleBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'm'))
  return match?.[1] || ''
}

test('plain interpretation evidence map constrains columns and wraps long tokens', () => {
  const gridRule = ruleBlock(`.archive-plain-evidence-head,
.archive-plain-evidence-card article`)
  const cardRule = ruleBlock('.archive-plain-evidence-card')
  const typeRule = ruleBlock('.archive-plain-evidence-type')
  const textRule = ruleBlock(`.archive-plain-evidence-card blockquote,
.archive-plain-evidence-card article > p,
.archive-plain-evidence-type strong,
.archive-plain-evidence-card article > em,
.archive-plain-evidence-head span`)
  const responsiveRule = css.match(/@media\s*\(max-width:\s*760px\)\s*\{[\s\S]*?\.archive-plain-evidence-head,[\s\S]*?\.archive-plain-evidence-card article[\s\S]*?grid-template-columns:\s*1fr/)

  assert.match(cardRule, /max-width:\s*100%/)
  assert.match(gridRule, /grid-template-columns:\s*minmax\(0,\s*132px\)\s+minmax\(0,\s*1fr\)\s+minmax\(0,\s*1fr\)\s+minmax\(0,\s*68px\)/)
  assert.match(gridRule, /min-width:\s*0/)
  assert.match(typeRule, /min-width:\s*0/)
  assert.match(typeRule, /max-width:\s*100%/)
  assert.match(textRule, /overflow-wrap:\s*anywhere/)
  assert.match(textRule, /word-break:\s*break-word/)
  assert.ok(responsiveRule, 'evidence map should stack to one column on narrow screens')
})
