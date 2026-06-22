import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildFallbackNeighborGraph,
  buildFallbackRecordGraph,
  buildFallbackSourceDetail
} from './graphFallback.js'

test('record graph fallback remains deterministic and rewrites the requested record id', () => {
  const graph = buildFallbackRecordGraph('CSQP-SFHC-TEXT-999')

  assert.equal(graph.record_id, 'CSQP-SFHC-TEXT-999')
  assert.ok(graph.nodes.some((node) => node.id === 'record:CSQP-SFHC-TEXT-999'))
  assert.ok(
    graph.edges.every((edge) => edge.record_id === 'CSQP-SFHC-TEXT-999')
  )
})

test('neighbor fallback returns only the selected node and its adjacent graph', () => {
  const graph = buildFallbackRecordGraph()
  const neighbors = buildFallbackNeighborGraph('person:母亲', graph)

  assert.equal(neighbors.center_node.id, 'person:母亲')
  assert.ok(neighbors.edges.length > 0)
  assert.ok(neighbors.nodes.some((node) => node.type === 'record'))
})

test('source fallback exposes traceable evidence details', () => {
  const graph = buildFallbackRecordGraph()
  const evidenceNode = graph.nodes.find((node) => node.type === 'evidence')
  const detail = buildFallbackSourceDetail(evidenceNode)

  assert.equal(detail.recordId, graph.record_id)
  assert.ok(detail.items.some((item) => item.label === '原文' && item.value))
})
