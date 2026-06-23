import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getDisplayLabel,
  getRelationDisplay,
  getSearchableKeywords
} from './graphLabelMap.js'
import {
  transformGraphForFlow,
  transformGraphForKinshipCommunication
} from './graphTransforms.js'

test('graph labels prefer Chinese display text and preserve bilingual search', () => {
  const themeNode = {
    id: 'theme:theme_instruction',
    type: 'theme',
    label: 'instruction'
  }

  assert.equal(getDisplayLabel(themeNode), '嘱托')
  assert.equal(getRelationDisplay('HAS_THEME'), '表达主题')
  assert.ok(getSearchableKeywords(themeNode).includes('instruction'))
  assert.ok(getSearchableKeywords(themeNode).includes('嘱托'))
})

test('known archive theme codes are classified into specific Chinese categories', () => {
  assert.equal(
    getDisplayLabel({
      id: 'theme:home_building',
      type: 'theme',
      label: 'home_building'
    }),
    '家园营建'
  )
  assert.equal(
    getDisplayLabel({
      id: 'theme:safety_report',
      type: 'theme',
      label: 'safety_report'
    }),
    '平安近况'
  )
})

test('evidence nodes never expose structured technical labels as primary text', () => {
  const node = {
    id: 'evidence:1',
    type: 'evidence',
    label: 'sender=遥儿海泉;recipient=母亲',
    properties: { evidence_type: 'remittance' }
  }

  assert.equal(getDisplayLabel(node), '汇款证据')
})

test('kinship transform adds a person-to-person communication relation', () => {
  const graph = {
    nodes: [
      { id: 'record:R-1', type: 'record', record_id: 'R-1' },
      { id: 'person:甲', type: 'person', label: '甲' },
      {
        id: 'person:母亲',
        type: 'person',
        label: '母亲',
        properties: { kinship_type: 'mother', person_kind: 'kinship_term' }
      }
    ],
    edges: [
      { id: 'e1', source: 'record:R-1', target: 'person:甲', type: 'SENT_BY', record_id: 'R-1' },
      { id: 'e2', source: 'record:R-1', target: 'person:母亲', type: 'RECEIVED_BY', record_id: 'R-1' }
    ]
  }
  const result = transformGraphForKinshipCommunication(graph)

  assert.ok(result.nodes.some((node) => node.visualType === 'kinship'))
  assert.ok(result.edges.some((edge) => edge.rawType === 'COMMUNICATES_WITH'))
})

test('kinship transform normalizes recipient terms and removes isolated nodes', () => {
  const graph = {
    nodes: [
      {
        id: 'record:R-1',
        type: 'record',
        record_id: 'R-1',
        properties: {
          sender_name_clean: '陈生',
          recipient_name_clean: '澄海林宅岳母',
          main_intent: 'remittance'
        }
      },
      {
        id: 'record:R-2',
        type: 'record',
        record_id: 'R-2',
        properties: {
          sender_name_clean: '林文',
          recipient_name_clean: '鳌头黄氏荆妻',
          main_intent: 'instruction'
        }
      },
      { id: 'place:广东澄海', type: 'place', label: '广东澄海' }
    ],
    edges: [
      {
        id: 'p1',
        source: 'record:R-1',
        target: 'place:广东澄海',
        type: 'MENTIONS_PLACE',
        record_id: 'R-1'
      },
      {
        id: 'p2',
        source: 'record:R-2',
        target: 'place:广东澄海',
        type: 'MENTIONS_PLACE',
        record_id: 'R-2'
      }
    ]
  }
  const result = transformGraphForKinshipCommunication(graph, { maxNodes: 30 })
  const connectedIds = new Set(
    result.edges.flatMap((edge) => [edge.source, edge.target])
  )

  assert.ok(result.nodes.some((node) => node.displayLabel === '岳母'))
  assert.ok(result.nodes.some((node) => node.displayLabel === '妻子'))
  assert.ok(result.nodes.every((node) => connectedIds.has(node.id)))
})

test('flow transform creates overseas-record-hometown lanes', () => {
  const result = transformGraphForFlow(
    {},
    [
      {
        origin_place: '泰国',
        destination_place: '广东饶平',
        count: 2,
        record_ids_sample: ['R-1', 'R-2']
      }
    ]
  )

  assert.ok(result.nodes.some((node) => node.visualType === 'overseas_place'))
  assert.ok(result.nodes.some((node) => node.visualType === 'record_group'))
  assert.ok(result.nodes.some((node) => node.visualType === 'hometown_place'))
})

test('generic overseas origins are marked as locations with unknown precision', () => {
  const result = transformGraphForFlow(
    {},
    [
      {
        origin_place: '海外',
        destination_place: '广东侨乡',
        count: 2,
        record_ids_sample: ['R-1', 'R-2']
      }
    ]
  )

  assert.ok(
    result.nodes.some(
      (node) =>
        node.visualType === 'overseas_place' &&
        node.displayLabel === '海外（地点未详）'
    )
  )
})
