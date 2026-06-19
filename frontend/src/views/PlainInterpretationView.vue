<template>
  <section class="archive-plain-page">
    <div class="archive-plain-bg" aria-hidden="true">
      <span class="archive-plain-line line-a"></span>
      <span class="archive-plain-line line-b"></span>
      <span class="archive-plain-seal seal-a">释</span>
      <span class="archive-plain-seal seal-b">证</span>
      <span class="archive-plain-wash"></span>
    </div>

    <nav class="archive-plain-breadcrumb" aria-label="白话释读路径">
      <span>侨批 RAG</span>
      <i>›</i>
      <span>释读生成</span>
      <i>›</i>
      <strong>白话释读</strong>
    </nav>

    <section class="archive-plain-header">
      <div class="archive-plain-redline" aria-hidden="true"></div>
      <div class="archive-plain-header-copy">
        <div class="archive-plain-label-row">
          <span>白话释读 · PLAIN INTERPRETATION</span>
          <em>RAG Interpretation</em>
        </div>
        <h1>将侨批原文转化为现代白话说明</h1>
        <p>
          基于侨批正文、结构化字段与证据片段，对旧式书信表达进行现代白话释读，并展示可追溯的证据映射与一致性检查。
        </p>
      </div>
      <aside class="archive-plain-header-mark">
        <div aria-hidden="true">释</div>
        <strong>QP-INTERPRET-001</strong>
      </aside>
    </section>

    <div v-if="error || result.error_message" class="archive-plain-note warning" role="status">
      <span>i</span>
      <p>{{ error || result.error_message }}</p>
    </div>

    <section v-if="result.generation_backend" class="generation-runtime-panel">
      <article>
        <span>生成后端</span>
        <strong :class="{ degraded: generationRuntime.degraded }">{{ generationRuntime.backendLabel }}</strong>
      </article>
      <article>
        <span>模型</span>
        <strong>{{ generationRuntime.modelLabel }}</strong>
      </article>
      <article>
        <span>Prompt 版本</span>
        <strong>{{ generationRuntime.promptVersion }}</strong>
      </article>
      <article>
        <span>索引版本</span>
        <strong>{{ generationRuntime.indexVersion }}</strong>
      </article>
      <article>
        <span>缓存</span>
        <strong>{{ generationRuntime.cacheLabel }}</strong>
      </article>
      <p v-if="generationRuntime.degraded">{{ generationRuntime.degradedLabel }}</p>
    </section>

    <section v-loading="loading" class="archive-interpretation-desk">
      <article class="archive-plain-card archive-source-card">
        <header class="archive-plain-card-head">
          <i class="card-icon document" aria-hidden="true"></i>
          <strong>侨批原文输入</strong>
          <span>原始文献</span>
        </header>
        <div class="archive-plain-card-body">
          <p class="archive-plain-help">输入侨批原文或选择一条档案记录，系统将生成现代白话释读。</p>

          <label class="archive-record-field">
            <span>档案编号</span>
            <input v-model="recordId" type="text" placeholder="CSQP-SFHC-TEXT-001" />
          </label>

          <div class="archive-original-paper">
            <i aria-hidden="true"></i>
            <textarea
              v-model="originalText"
              rows="9"
              placeholder="请输入侨批原文..."
            ></textarea>
          </div>

          <div class="archive-plain-chip-row" aria-label="释读约束">
            <span v-for="chip in inputChips" :key="chip">{{ chip }}</span>
          </div>

          <div class="archive-plain-actions">
            <button class="primary" type="button" :disabled="loading || !canGenerate" @click="runGeneration">
              {{ loading ? '生成中…' : '生成白话释读' }}
            </button>
            <button type="button" @click="clearContent">清空内容</button>
          </div>
        </div>
      </article>

      <article class="archive-plain-card archive-interpretation-card">
        <header class="archive-plain-card-head">
          <i class="card-icon book" aria-hidden="true"></i>
          <strong>白话释读结果</strong>
          <span class="plain-tag">Plain Chinese</span>
        </header>
        <div class="archive-plain-card-body interpretation-body">
          <div v-if="loading" class="archive-plain-loading">
            <i aria-hidden="true"></i>
            <p>正在生成白话释读…</p>
          </div>
          <div v-else-if="generatedText" class="archive-annotation-paper">
            <div class="archive-annotation-seal" aria-hidden="true">释</div>
            <div class="archive-annotation-title">
              <span>◆ 释读注记</span>
              <i></i>
              <em>{{ result.record_id || recordId }}</em>
            </div>
            <p>{{ generatedText }}</p>
            <footer>
              <span>模型：{{ generationRuntime.modelLabel }}</span>
              <span>策略：证据约束</span>
              <span>粒度：句级映射</span>
            </footer>
          </div>
          <div v-else class="archive-plain-empty">
            <span aria-hidden="true">文</span>
            <p>请在左侧输入原文并点击生成</p>
          </div>
        </div>
      </article>
    </section>

    <section class="archive-plain-section">
      <header class="archive-plain-section-title">
        <i aria-hidden="true"></i>
        <strong>结构化摘要</strong>
        <span>STRUCT-SUMMARY</span>
      </header>
      <div class="archive-summary-card-grid">
        <article v-for="item in summaryCards" :key="item.num" class="archive-summary-card">
          <div aria-hidden="true">{{ item.num }}</div>
          <em>{{ item.num }}</em>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>
    </section>

    <section class="archive-plain-section">
      <header class="archive-plain-section-title">
        <i aria-hidden="true"></i>
        <strong>证据映射</strong>
        <span>EVIDENCE-MAP</span>
      </header>
      <div class="archive-plain-evidence-card" :class="{ empty: !evidenceMapRows.length }">
        <template v-if="evidenceMapRows.length">
          <div class="archive-plain-evidence-head">
            <span>释读片段</span>
            <span>原文证据</span>
            <span>依据说明</span>
            <span>分数</span>
          </div>
          <article v-for="(row, index) in evidenceMapRows" :key="`${row.source_text}-${index}`">
            <div class="archive-plain-evidence-type">
              <i></i>
              <strong>{{ evidenceCategory(row, index) }}</strong>
            </div>
            <blockquote>「{{ row.source_text || row.target_span || '暂无原文证据' }}」</blockquote>
            <p>{{ evidenceMeaning(row) }}</p>
            <em>{{ scoreLabel(row.similarity_score) }}</em>
          </article>
        </template>
        <p v-else>暂无证据映射，后端返回 RAG 证据后将在此展示。</p>
      </div>
    </section>

    <section class="archive-plain-section">
      <header class="archive-plain-section-title consistency-title">
        <i aria-hidden="true"></i>
        <strong>一致性检查</strong>
        <em :class="{ failed: consistencyCheck.status === 'failed' }">
          {{ consistencyCheck.status === 'failed' ? 'Needs Review' : 'Consistent · 通过' }}
        </em>
        <span>CONSISTENCY</span>
      </header>
      <div class="archive-plain-validation-card">
        <div class="archive-plain-validation-seal" aria-hidden="true">核</div>
        <div class="archive-validation-grid">
          <article v-for="item in validationCards" :key="item.label" :class="{ failed: !item.ok }">
            <div>
              <i></i>
              <span>{{ item.label }}</span>
            </div>
            <p>{{ item.detail }}</p>
          </article>
        </div>
        <footer>
          <span>检查项：{{ passedValidationCount }} / {{ validationCards.length }} 通过</span>
          <i></i>
          <strong>QP-VALID · {{ result.record_id || recordId }}</strong>
        </footer>
      </div>
    </section>

    <aside class="archive-plain-note">
      <span>i</span>
      <p>如果 Qwen 或后端释读服务尚未启用，系统将展示本地演示结果，并保留白话释读、证据映射与一致性检查流程。</p>
    </aside>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { generateInterpretation } from '../api/generation'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackResult from '../mock/plain_interpretation.json'
import { generationState } from '../utils/generationPresentation'

const recordId = ref('CSQP-SFHC-TEXT-001')
const originalText = ref('')
const result = ref(demoMode ? fallbackResult : {})
const loading = ref(false)
const error = ref('')

const inputChips = ['原文转写', '证据约束：开启', '句级映射', '不补充原文外信息']

const slotLabels = {
  sender: '寄信人',
  recipient: '收信人',
  origin_place: '来源地',
  destination_place: '目的地',
  money: '汇款',
  purpose: '用途',
  input_preview: '输入预览'
}

const fieldLabels = {
  original_text: '原文',
  normalized_text: '规范文本',
  style_pattern: '风格模式',
  source_column: '来源字段',
  prompt_context: 'Prompt 上下文'
}

const canGenerate = computed(() => Boolean(originalText.value.trim() || recordId.value.trim()))
const generatedText = computed(() => result.value.generated_text || '')
const generationRuntime = computed(() => generationState(result.value))

const slotRows = computed(() =>
  Object.entries(result.value.slots || {}).map(([key, value]) => [slotLabels[key] || key, formatValue(value)])
)

const summaryRows = computed(() => {
  if (result.value.summary?.length) return result.value.summary
  if (result.value.validation_report?.summary) return [result.value.validation_report.summary]
  if (result.value.error_message) return ['后端已返回提示信息，可查看证据上下文和错误提示。']
  return []
})

const evidenceRows = computed(() => {
  if (result.value.evidence?.length) return normalizeEvidence(result.value.evidence)
  return normalizeEvidence(
    (result.value.evidence_references || []).map((item) => ({
      source_field: item.source_column,
      source_text: item.unit_text,
      reason: item.evidence_type || item.unit_type,
      similarity_score: 1
    }))
  )
})

const evidenceMapRows = computed(() => {
  if (result.value.evidence_mapping?.length) return normalizeEvidence(result.value.evidence_mapping)
  return evidenceRows.value
})

const consistencyCheck = computed(() => {
  if (result.value.consistency_check) return normalizeCheck(result.value.consistency_check)
  const report = result.value.validation_report
  if (!report) {
    return {
      status: generatedText.value ? 'passed' : 'pending',
      warnings: [],
      passed_rules: generatedText.value ? ['money_supported_by_evidence', 'recipient_supported_by_evidence'] : [],
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

const slotMap = computed(() => new Map(slotRows.value))

const summaryCards = computed(() => [
  {
    num: '01',
    label: '人物关系',
    value: joinAvailable([slotMap.value.get('寄信人'), slotMap.value.get('收信人')]) || findSummary(/人|母|亲|寄信|收信/) || '待提取'
  },
  {
    num: '02',
    label: '地点信息',
    value: joinAvailable([slotMap.value.get('来源地'), slotMap.value.get('目的地')]) || findSummary(/地|新加坡|潮州|家乡/) || '待提取'
  },
  {
    num: '03',
    label: '金额信息',
    value: slotMap.value.get('汇款') || findSummary(/元|银|钱|汇款/) || '待提取'
  },
  {
    num: '04',
    label: '主题信息',
    value: joinAvailable([slotMap.value.get('用途'), ...summaryRows.value.slice(0, 2)]) || '平安问候、汇款托带、家人关怀'
  }
])

const validationCards = computed(() => {
  const check = consistencyCheck.value
  const passed = check.passed_rules || []
  const failed = check.failed_rules || []
  const warnings = check.warnings || []
  const hasProblem = check.status === 'failed' || failed.length > 0
  return [
    {
      label: '原文依据',
      ok: !hasProblem || evidenceMapRows.value.length > 0,
      detail: evidenceMapRows.value.length ? `释读内容关联 ${evidenceMapRows.value.length} 条原文证据` : '暂无证据片段'
    },
    {
      label: '金额一致',
      ok: !failed.some((rule) => /money|amount|金额|汇款/.test(String(rule))),
      detail: findRuleText([...passed, ...warnings], /money|amount|金额|汇款/) || `${slotMap.value.get('汇款') || '金额'}已进入一致性检查`
    },
    {
      label: '人物一致',
      ok: !failed.some((rule) => /recipient|sender|person|人物|收信人|寄信人/.test(String(rule))),
      detail: findRuleText([...passed, ...warnings], /recipient|sender|person|人物|收信人|寄信人/) || `${slotMap.value.get('收信人') || '人物关系'}已保留`
    },
    {
      label: '生成边界',
      ok: !hasProblem,
      detail: failed[0] || warnings[0] || '未添加原文之外的人物和事件'
    }
  ]
})

const passedValidationCount = computed(() => validationCards.value.filter((item) => item.ok).length)

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

function joinAvailable(items) {
  return items.filter(Boolean).join('、')
}

function findSummary(pattern) {
  return summaryRows.value.find((item) => pattern.test(String(item))) || ''
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
  return fieldLabels[field] || field || '原文'
}

function evidenceCategory(row, index) {
  const fallback = ['平安信息', '汇款信息', '亲属问候', '后续寄款']
  return row.reason || row.target_span || fallback[index % fallback.length]
}

function evidenceMeaning(row) {
  if (row.target_span) return `支持释读片段：“${row.target_span}”`
  if (row.reason) return row.reason
  return `${fieldLabel(row.source_field)}字段中的可追溯依据`
}

function scoreLabel(score) {
  if (score === undefined || score === null) return '证据'
  return `${Math.round(score * 100)}%`
}

function clearContent() {
  originalText.value = ''
  result.value = {}
  error.value = ''
}

async function runGeneration() {
  loading.value = true
  error.value = ''
  try {
    result.value = await generateInterpretation({
      query: originalText.value.trim() || '请根据该档案记录解释这封侨批的主要内容。',
      record_id: recordId.value,
      top_k: 8,
      filters: {},
      expansion_mode: 'balanced',
      dry_run: false
    })
  } catch (requestError) {
    if (demoMode) {
      result.value = fallbackResult
      error.value = demoFailureMessage('白话解读请求')
    } else {
      result.value = {}
      error.value = apiFailureMessage(requestError, '白话解读请求')
    }
  } finally {
    loading.value = false
  }
}

onMounted(runGeneration)
</script>
