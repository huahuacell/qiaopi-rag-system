import assert from 'node:assert/strict'
import test from 'node:test'

import {
  evidenceTracesFromGraph,
  graphQualityState,
  metadataIdFromNode,
  recordIdsFromGraph
} from './graphPresentation.js'

test('graph trace helpers resolve records evidence and metadata', () => {
  const node = {
    id: 'metadata:CSQP-META-000001',
    type: 'metadata_record',
    record_id: 'CSQP-SFHC-TEXT-017',
    source_id: 'CSQP-META-000001'
  }
  const graph = {
    nodes: [{ id: 'record:CSQP-SFHC-TEXT-002', type: 'record' }],
    edges: [
      {
        type: 'SUPPORTED_BY',
        record_id: 'CSQP-SFHC-TEXT-017',
        evidence_text: '寄上洋银肆元',
        source_table: 'qiaopi_evidence_spans',
        source_id: 'EVID-1'
      }
    ]
  }

  assert.equal(metadataIdFromNode(node), 'CSQP-META-000001')
  assert.deepEqual(recordIdsFromGraph(node, graph), [
    'CSQP-SFHC-TEXT-002',
    'CSQP-SFHC-TEXT-017'
  ])
  assert.equal(evidenceTracesFromGraph(graph)[0].text, '寄上洋银肆元')
})

test('graph quality only passes with no structural failures', () => {
  assert.equal(
    graphQualityState({
      duplicate_logical_edge_count: 0,
      orphan_edge_count: 0,
      missing_node_provenance_count: 0,
      missing_edge_provenance_count: 0
    }).healthy,
    true
  )
  assert.equal(graphQualityState({ orphan_edge_count: 2 }).failureCount, 2)
})
