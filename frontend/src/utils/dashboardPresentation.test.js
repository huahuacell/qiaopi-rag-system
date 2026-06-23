import assert from 'node:assert/strict'
import test from 'node:test'

import {
  formatRelationshipDistribution,
  formatRelationshipLabel,
  originAxisLabelOption,
  splitYearDistribution
} from './dashboardPresentation.js'

test('relationship labels use concise Chinese display names', () => {
  assert.equal(formatRelationshipLabel('child_to_parent'), '子女→父母')
  assert.equal(formatRelationshipLabel('parent_to_child'), '父母→子女')
  assert.equal(formatRelationshipLabel('sibling_other'), '兄弟姐妹')
  assert.equal(formatRelationshipLabel('spouse_to_spouse'), '夫妻')
  assert.equal(formatRelationshipLabel('grandchild_to_grandparent'), '孙辈→祖辈')
  assert.equal(formatRelationshipLabel('grandchild_to_grandparents'), '孙辈→祖辈')
  assert.equal(formatRelationshipLabel('social_or_other'), '社会/其他')
  assert.equal(formatRelationshipLabel('unknown'), '关系不详')
})

test('relationship labels cover enums returned by the live dashboard endpoint', () => {
  assert.equal(formatRelationshipLabel('sibling_or_same_generation_kin'), '兄弟姐妹/同辈')
  assert.equal(formatRelationshipLabel('social_or_business'), '社会/商业')
  assert.equal(formatRelationshipLabel('son_in_law_to_parent_in_law'), '女婿→岳父母')
  assert.equal(formatRelationshipLabel('uncle_nephew_or_nephew_kin'), '叔侄/舅甥')
  assert.equal(formatRelationshipLabel('younger_to_elder_kin'), '晚辈→长辈')
  assert.equal(formatRelationshipLabel('in_law_or_affinal_kin'), '姻亲')
  assert.equal(formatRelationshipLabel('parent_to_child_in_law'), '父母→子女配偶')
})

test('relationship formatter preserves the raw enum and shortens fallback text', () => {
  const [known, fallback] = formatRelationshipDistribution([
    { label: 'child_to_parent', value: 8 },
    { label: 'a_very_long_relationship_category_name', value: 3 }
  ])

  assert.deepEqual(known, {
    label: '子女→父母',
    rawLabel: 'child_to_parent',
    value: 8
  })
  assert.equal(fallback.rawLabel, 'a_very_long_relationship_category_name')
  assert.equal(fallback.label, 'a very long…')
})

test('year distribution contains only real years and reports unknown separately', () => {
  const result = splitYearDistribution([
    { label: '1972', value: 12 },
    { label: 'unknown', value: 77 },
    { label: 1911, value: 5 },
    { label: '1921', value: 9 },
    { label: '1938', value: 14 },
    { label: '1920s', value: 100 },
    { label: 'not_recorded', value: 4 }
  ])

  assert.deepEqual(result.years, [
    { label: '1911', value: 5 },
    { label: '1921', value: 9 },
    { label: '1938', value: 14 },
    { label: '1972', value: 12 }
  ])
  assert.equal(result.unknownCount, 77)
})

test('origin axis labels always render while keeping Guangdong Shantou readable', () => {
  const option = originAxisLabelOption()

  assert.equal(option.interval, 0)
  assert.equal(option.hideOverlap, false)
  assert.equal(option.rotate, 24)
  assert.equal(option.overflow, 'truncate')
  assert.equal(option.formatter('广东汕头'), '广东汕头')
  assert.equal(option.formatter('广东潮安支风长名称'), '广东潮安支风…')
})
