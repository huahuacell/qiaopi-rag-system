<template>
  <section class="archive-style-page">
    <div class="archive-style-bg" aria-hidden="true">
      <span class="archive-style-line line-a"></span>
      <span class="archive-style-line line-b"></span>
      <span class="archive-style-seal seal-a">批</span>
      <span class="archive-style-seal seal-b">文</span>
      <span class="archive-style-wash"></span>
    </div>

    <nav class="archive-style-breadcrumb" aria-label="侨批体生成路径">
      <span>侨批 RAG</span>
      <i>›</i>
      <span>释读生成</span>
      <i>›</i>
      <strong>侨批体生成</strong>
    </nav>

    <section class="archive-style-header">
      <div class="archive-style-redline" aria-hidden="true"></div>
      <div class="archive-style-header-copy">
        <span class="archive-style-label">风格转换 · STYLE TRANSFER</span>
        <h1>把现代白话转写为侨批书信体</h1>
        <p>
          基于侨批文本中的称谓、问安、汇款表达与结尾格式，将现代白话内容转写为具有侨批文体特征的书信文本，并展示可追溯的风格依据与一致性检查。
        </p>
      </div>
      <aside class="archive-style-header-mark">
        <div class="archive-style-round-seal" aria-hidden="true">批</div>
        <strong>QP-GEN-STYLE-001</strong>
        <span>档案索引号</span>
        <em>Qiaopi Style</em>
      </aside>
    </section>

    <div v-if="error || result.error_message" class="archive-style-demo-note warning" role="status">
      <span>i</span>
      <p>{{ error || result.error_message }}</p>
    </div>

    <section class="archive-writing-desk">
      <article class="archive-style-card archive-input-card">
        <header class="archive-style-card-head">
          <strong>白话内容输入</strong>
          <span>现代白话家书原文</span>
        </header>
        <div class="archive-style-card-body">
          <p class="archive-style-help">
            输入现代白话家书内容，系统将抽取人物、地点、汇款、问候等信息，并生成侨批风格文本。
          </p>
          <div class="archive-style-textarea-wrap">
            <i aria-hidden="true"></i>
            <textarea
              v-model="plainText"
              rows="7"
              placeholder="请输入现代白话家书内容……"
            ></textarea>
          </div>
          <div class="archive-style-chip-row" aria-label="生成约束">
            <span v-for="chip in inputChips" :key="chip.label">
              <small>{{ chip.label }}</small>
              <b>{{ chip.value }}</b>
            </span>
          </div>
          <div class="archive-style-actions">
            <button class="primary" type="button" :disabled="loading" @click="runTransfer">
              {{ loading ? '生成中…' : '生成侨批体' }}
            </button>
            <button type="button" @click="clearContent">清空内容</button>
          </div>
        </div>
      </article>

      <article class="archive-style-card archive-output-card">
        <header class="archive-style-card-head">
          <strong>侨批体生成结果</strong>
          <span v-if="generatedText" class="archive-draft-tag">Generated Draft</span>
        </header>
        <div class="archive-output-body">
          <div class="archive-output-paper" :class="{ empty: !generatedText }">
            <div class="archive-output-seal" aria-hidden="true">侨批</div>
            <i class="archive-output-redline one" aria-hidden="true"></i>
            <i class="archive-output-redline two" aria-hidden="true"></i>
            <template v-if="generatedText">
              <p
                v-for="(line, index) in generatedLines"
                :key="`${line}-${index}`"
                :class="{ head: index === 0, foot: index === generatedLines.length - 1 }"
              >
                {{ line || '\u00A0' }}
              </p>
            </template>
            <p v-else class="archive-output-empty">暂无生成结果。输入内容后点击生成侨批体。</p>
          </div>
          <div class="archive-output-tools">
            <button type="button" :disabled="!generatedText" @click="copyGeneratedText">复制文本</button>
          </div>
        </div>
      </article>
    </section>

    <section class="archive-style-card archive-slot-panel">
      <header class="archive-style-card-head">
        <strong>风格槽位</strong>
        <span>Style Slots</span>
      </header>
      <div class="archive-style-slot-grid">
        <article v-for="slot in styleSlotCards" :key="slot.num" class="archive-style-slot-card">
          <em>{{ slot.num }}</em>
          <span>{{ slot.name }}</span>
          <strong>{{ slot.value }}</strong>
        </article>
      </div>
    </section>

    <section class="archive-style-card archive-reference-panel">
      <header class="archive-style-card-head">
        <strong>证据依据</strong>
        <span>Evidence References</span>
        <em>RAG Grounded</em>
      </header>
      <div class="archive-reference-list" :class="{ empty: !evidenceRows.length }">
        <template v-if="evidenceRows.length">
          <article v-for="(row, index) in evidenceRows" :key="`${row.source_text}-${index}`">
            <div class="archive-reference-type">
              <i></i>
              <span>{{ row.reason || fieldLabel(row.source_field) }}</span>
            </div>
            <blockquote>{{ row.source_text || row.target_span || '暂无证据片段' }}</blockquote>
            <p>{{ fieldLabel(row.source_field) }}</p>
            <em>{{ row.target_span || `REF-${String(index + 1).padStart(3, '0')}` }}</em>
          </article>
        </template>
        <p v-else>暂无证据依据，后端返回 RAG 片段后将在此展示。</p>
      </div>
    </section>

    <section class="archive-style-card archive-consistency-panel">
      <header class="archive-style-card-head">
        <strong>一致性检查</strong>
        <span>Consistency Check</span>
        <em :class="{ failed: consistencyCheck.status === 'failed' }">
          {{ consistencyCheck.status === 'failed' ? 'Needs Review' : 'Consistent' }}
        </em>
      </header>
      <div class="archive-consistency-grid">
        <article v-for="item in validationCards" :key="item.label" :class="{ failed: !item.ok }">
          <div>
            <i></i>
            <strong>{{ item.label }}</strong>
          </div>
          <p>{{ item.detail }}</p>
        </article>
      </div>
    </section>

    <aside class="archive-style-demo-note">
      <span>i</span>
      <p>如果 Qwen 或后端生成服务尚未启用，系统将展示本地演示结果，并保留风格槽位、证据依据与一致性检查流程。</p>
    </aside>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { generateStyleTransfer } from '../api/generation'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackResult from '../mock/style_transfer.json'

const defaultPlainText = '母亲，我在新加坡平安，寄回八元给家里买米和药。请您放心。'

const plainText = ref(defaultPlainText)
const slots = reactive({
  recipient: '母亲',
  origin_place: '新加坡',
  money: '八元',
  purpose: '米粮和药费'
})
const result = ref(demoMode ? fallbackResult : {})
const loading = ref(false)
const error = ref('')

const slotLabels = {
  recipient: '收信人',
  origin_place: '来源地',
  money: '汇款',
  purpose: '用途',
  input_preview: '输入预览',
  opening: '称谓格式',
  safety: '问安表达',
  remittance: '汇款表达',
  family_care: '问候保重',
  instruction: '嘱托表达',
  closing: '结尾格式',
  style_reference: '综合风格'
}

const fieldLabels = {
  original_text: '侨批原文片段',
  normalized_text: '规范文本',
  style_pattern: '风格模式',
  source_column: '来源字段',
  body_core: '正文核心',
  prompt_context: 'Prompt 上下文'
}

const inputChips = computed(() => [
  { label: '风格', value: '家书' },
  { label: '语气', value: result.value?.slots?.recipient ? '恭敬' : '侨批体' },
  { label: '证据约束', value: evidenceRows.value.length ? '开启' : '待检索' },
  { label: '约束', value: '不补充原文外信息' }
])

const generatedText = computed(() => result.value.generated_text || '')
const generatedLines = computed(() => splitLetterLines(generatedText.value))

const slotRows = computed(() =>
  Object.entries(result.value.slots || {}).map(([key, value]) => [slotLabels[key] || key, formatValue(value)])
)

const styleSlotRows = computed(() =>
  Object.entries(result.value.style_slots || {}).map(([key, examples]) => [
    slotLabels[key] || key,
    examples?.[0]?.unit_text || `${examples?.length || 0} 条样例`
  ])
)

const evidenceRows = computed(() => {
  if (result.value.evidence_mapping?.length) return normalizeEvidence(result.value.evidence_mapping)
  if (result.value.evidence?.length) return normalizeEvidence(result.value.evidence)
  return normalizeEvidence(
    (result.value.evidence_references || []).map((item) => ({
      target_span: item.unit_type,
      source_field: item.source_column,
      source_text: item.unit_text,
      reason: item.evidence_type || item.unit_type,
      similarity_score: 1
    }))
  )
})

const consistencyCheck = computed(() => {
  if (result.value.consistency_check) return normalizeCheck(result.value.consistency_check)
  const report = result.value.validation_report
  if (!report) {
    return {
      status: generatedText.value ? 'passed' : 'pending',
      warnings: [],
      passed_rules: generatedText.value ? ['recipient_preserved'] : [],
      failed_rules: []
    }
  }
  return normalizeCheck({
    status: report.is_consistent ? 'passed' : 'failed',
    warnings: [
      ...(report.possible_hallucinations || []),
      ...(report.missing_required_facts || []),
      ...(report.unsupported_new_facts || [])
    ],
    passed_rules: (report.checks || []).filter((item) => item.status === 'pass').map((item) => item.message),
    failed_rules: (report.checks || []).filter((item) => item.status === 'fail').map((item) => item.message)
  })
})

const styleSlotCards = computed(() => {
  const sourceRows = new Map([...styleSlotRows.value, ...slotRows.value])
  return [
    {
      num: '01',
      name: '称谓格式',
      value: sourceRows.get('称谓格式') || inferOpening() || sourceRows.get('收信人') || '待生成'
    },
    {
      num: '02',
      name: '问安表达',
      value: sourceRows.get('问安表达') || inferSafety() || '待生成'
    },
    {
      num: '03',
      name: '汇款表达',
      value: sourceRows.get('汇款表达') || inferRemittance() || sourceRows.get('汇款') || '待生成'
    },
    {
      num: '04',
      name: '结尾格式',
      value: sourceRows.get('结尾格式') || inferClosing() || '待生成'
    }
  ]
})

const validationCards = computed(() => {
  const check = consistencyCheck.value
  const passed = check.passed_rules || []
  const failed = check.failed_rules || []
  const warnings = check.warnings || []
  const hasProblem = check.status === 'failed' || failed.length > 0
  return [
    {
      label: '人物一致',
      ok: !hasProblem || passed.some((rule) => /recipient|person|人物|收信人/.test(rule)),
      detail: findRuleText([...passed, ...warnings], /recipient|person|人物|收信人/) || `${slots.recipient || '人物'}信息已纳入生成检查`
    },
    {
      label: '金额一致',
      ok: !failed.some((rule) => /money|amount|金额|汇款/.test(rule)),
      detail: findRuleText([...passed, ...warnings], /money|amount|金额|汇款/) || `${slots.money || '汇款金额'}保持为生成约束`
    },
    {
      label: '地点一致',
      ok: !failed.some((rule) => /place|origin|地点|来源地/.test(rule)),
      detail: findRuleText([...passed, ...warnings], /place|origin|地点|来源地/) || `${slots.origin_place || '来源地'}作为语境线索保留`
    },
    {
      label: '生成边界',
      ok: !hasProblem,
      detail: failed[0] || warnings[0] || '未添加输入之外的新人物和事件'
    }
  ]
})

function normalizeEvidence(rows) {
  return rows.map((row) => ({
    target_span: row.target_span,
    source_field: row.source_field || row.source_column,
    source_text: row.source_text || row.evidence_text || row.unit_text,
    reason: row.reason || row.evidence_type || row.unit_type,
    similarity_score: row.similarity_score
  }))
}

function normalizeCheck(check) {
  return {
    status: check.status || 'pending',
    warnings: check.warnings || [],
    passed_rules: check.passed_rules || [],
    failed_rules: check.failed_rules || []
  }
}

function splitLetterLines(text) {
  if (!text) return []
  const trimmed = String(text).trim()
  if (trimmed.includes('\n')) return trimmed.split('\n')
  return trimmed
    .replace(/([。！？；：])/g, '$1\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function inferOpening() {
  return generatedLines.value[0] || ''
}

function inferSafety() {
  return generatedLines.value.find((line) => /平安|勿念|放心|安好/.test(line)) || ''
}

function inferRemittance() {
  return generatedLines.value.find((line) => /银|元|汇|寄|奉上|托/.test(line)) || ''
}

function inferClosing() {
  return generatedLines.value[generatedLines.value.length - 1] || ''
}

function findRuleText(rules, pattern) {
  return rules.find((rule) => pattern.test(String(rule))) || ''
}

function formatValue(value) {
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'object' && value !== null) return JSON.stringify(value)
  return String(value ?? '')
}

function fieldLabel(field) {
  return fieldLabels[field] || field || '侨批原文片段'
}

function clearContent() {
  plainText.value = ''
  result.value = {}
  error.value = ''
}

async function copyGeneratedText() {
  if (!generatedText.value || !navigator?.clipboard) return
  await navigator.clipboard.writeText(generatedText.value)
}

async function runTransfer() {
  loading.value = true
  error.value = ''
  try {
    result.value = await generateStyleTransfer({
      plain_text: plainText.value,
      top_k: 3,
      expansion_mode: 'balanced',
      dry_run: true
    })
  } catch (requestError) {
    if (demoMode) {
      result.value = fallbackResult
      error.value = demoFailureMessage('风格转换请求')
    } else {
      result.value = {}
      error.value = apiFailureMessage(requestError, '风格转换请求')
    }
  } finally {
    loading.value = false
  }
}

onMounted(runTransfer)
</script>
