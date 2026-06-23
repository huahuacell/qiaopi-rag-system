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
          <div
            v-if="result.generation_backend"
            class="archive-runtime-tags"
            aria-label="本次生成使用的模型与提示词版本"
          >
            <span class="archive-draft-tag" :title="generationRuntime.backendLabel">
              {{ generationRuntime.modelLabel }}
            </span>
            <span class="archive-draft-tag" :title="generationRuntime.promptVersion">
              {{ promptBadgeLabel }}
            </span>
          </div>
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
        <QiaopiEnvelopePanel
          v-model="generatedText"
          :loading="loading"
          :generation-key="generationKey"
          @copy="copyGeneratedText"
        />
      </article>
    </section>

    <section class="archive-style-card archive-slot-panel">
      <header class="archive-style-card-head">
        <strong>风格槽位</strong>
        <span>按本次输入意图检索，仅最佳样例注入提示词</span>
        <em>{{ result.retrieval_mode === 'hybrid' ? '混合检索' : '槽位检索' }}</em>
      </header>
      <div class="archive-style-slot-grid">
        <article v-for="slot in styleSlotCards" :key="slot.num" class="archive-style-slot-card">
          <em>{{ slot.num }}</em>
          <span>{{ slot.name }}</span>
          <strong>{{ slot.value }}</strong>
          <small>{{ slot.meta }}</small>
        </article>
      </div>
    </section>

    <section class="archive-style-card archive-reference-panel">
      <header class="archive-style-card-head">
        <strong>证据依据</strong>
        <span>仅展示已注入提示词的侨批原文，以及它与生成表达的对应关系</span>
        <em>RAG 文体溯源</em>
      </header>
      <div class="archive-reference-list" :class="{ empty: !evidenceRows.length }">
        <template v-if="evidenceRows.length">
          <article v-for="(row, index) in evidenceRows" :key="`${row.unit_id}-${row.target_span}-${index}`">
            <div class="archive-reference-type">
              <i></i>
              <div>
                <span>{{ reasonLabel(row.reason) }}</span>
                <small>{{ evidenceTraceLabel(row) }}</small>
              </div>
            </div>
            <div class="archive-reference-target">
              <small>{{ row.target_label || '生成表达' }}</small>
              <em>{{ row.target_span || `REF-${String(index + 1).padStart(3, '0')}` }}</em>
            </div>
            <div class="archive-reference-source">
              <small>知识库侨批原文</small>
              <blockquote>{{ evidenceSourceText(row) }}</blockquote>
            </div>
            <p>
              <b>{{ fieldLabel(row.source_field) }}</b>
              <small>{{ row.record_id || row.unit_id }}</small>
            </p>
          </article>
        </template>
        <p v-else>暂无达到映射阈值的知识库文体依据；事实一致性仍会在下方独立检查。</p>
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
        <article
          v-for="item in validationCards"
          :key="item.label"
          :class="{ failed: item.status === 'fail', warning: item.status === 'warn' }"
        >
          <div>
            <i></i>
            <strong>{{ item.label }}</strong>
          </div>
          <p>{{ item.detail }}</p>
        </article>
      </div>
    </section>

  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

import { generateStyleTransfer } from '../api/generation'
import QiaopiEnvelopePanel from '../components/QiaopiEnvelopePanel.vue'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackResult from '../mock/style_transfer.json'
import { generationState } from '../utils/generationPresentation'
import {
  buildStyleTransferValidationCards,
  normalizeStyleTransferCheck
} from '../utils/styleTransferPresentation'

const defaultPlainText = '母亲，我在新加坡平安，寄回八元给家里买米和药。请您放心。'

const plainText = ref(defaultPlainText)
const result = ref(demoMode ? fallbackResult : {})
const generatedText = ref(demoMode ? fallbackResult.generated_text || '' : '')
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
  prompt_context: '提示词上下文',
  style_reference_text: '综合文体参考',
  evidence_instruction: '嘱托表达证据',
  evidence_closing: '结尾署名证据',
  evidence_safety: '平安问候证据',
  evidence_remittance: '寄款表达证据',
  evidence_family_care: '亲属关怀证据',
  evidence_opening: '称谓开头证据',
  opening: '称谓开头',
  safety: '平安问候',
  remittance: '寄款表达',
  family_care: '亲属关怀',
  instruction: '嘱托表达',
  closing: '结尾署名',
  style_reference: '综合文体参考',
  user_input: '用户输入'
}

const reasonLabels = {
  lexical_overlap: '词句重合匹配',
  no_supported_evidence_match: '未找到足够匹配的知识库证据',
  hybrid_style_support: '混合检索文体依据',
  semantic_style_support: '语义相似文体依据',
  lexical_style_support: '关键词文体依据',
  hybrid_slot_style_support: '混合检索 · 功能槽位依据',
  semantic_slot_style_support: '语义检索 · 功能槽位依据',
  lexical_slot_style_support: '关键词检索 · 功能槽位依据',
  semantic_similarity: '语义相似匹配',
  hybrid_match: '综合检索匹配',
  exact_match: '原文精确匹配',
  style_reference_text: '综合文体参考',
  evidence_instruction: '嘱托表达证据',
  evidence_closing: '结尾署名证据',
  evidence_safety: '平安问候证据',
  evidence_remittance: '寄款表达证据',
  evidence_family_care: '亲属关怀证据',
  evidence_opening: '称谓开头证据',
  opening: '称谓开头参考',
  safety: '平安问候参考',
  remittance: '寄款表达参考',
  family_care: '亲属关怀参考',
  instruction: '嘱托表达参考',
  closing: '结尾署名参考',
  style_reference: '综合文体参考'
}

const inputChips = computed(() => [
  { label: '风格', value: '家书' },
  { label: '语气', value: result.value?.slots?.recipient ? '恭敬' : '侨批体' },
  { label: '证据约束', value: evidenceRows.value.length ? '开启' : '待检索' },
  { label: '约束', value: '不补充原文外信息' }
])

const generationRuntime = computed(() => generationState(result.value))
const generationKey = computed(() =>
  String(result.value.request_id || result.value.cache_key || '')
)
const promptBadgeLabel = computed(() => {
  const version = generationRuntime.value.promptVersion
  const match = String(version).match(/v(\d+)$/i)
  return match ? `prompt-v${match[1]}` : version
})
const activeStyleSlots = computed(() => new Set(result.value.active_style_slots || []))

const evidenceRows = computed(() => {
  const mapped = normalizeEvidence(result.value.evidence_mapping || [])
    .filter((item) => item.evidence_role === 'style' && item.source_text)
  if (mapped.length) return mergeEvidenceByKnowledgeUnit(mapped)

  return normalizeEvidence(
    (result.value.evidence_references || [])
      .filter((item) => item.prompt_included)
      .map((item) => ({
        target_span: `已注入“${slotLabels[item.unit_type] || item.unit_type}”槽位`,
        target_label: '注入槽位',
        record_id: item.record_id,
        unit_id: item.unit_id,
        source_field: item.source_column,
        source_text: item.unit_text,
        reason: retrievalReason(item.retrieval_sources),
        evidence_role: 'style',
        retrieval_sources: item.retrieval_sources,
        prompt_included: true,
        similarity_score: item.slot_score || item.final_score || 0
      }))
  )
})

const consistencyCheck = computed(() =>
  normalizeStyleTransferCheck(result.value, Boolean(generatedText.value))
)

const styleSlotCards = computed(() => {
  const styleSlots = result.value.style_slots || {}
  const card = (num, key, name) => {
    const active = activeStyleSlots.value.has(key)
    const example = styleSlots[key]?.[0]
    if (!active) {
      return {
        num,
        name,
        value: '本次输入未涉及该表达',
        meta: '未启用，不注入提示词'
      }
    }
    if (!example) {
      return {
        num,
        name,
        value: '未检索到合格样例',
        meta: '建议人工检查知识库槽位数据'
      }
    }
    const sources = new Set(example.retrieval_sources || [])
    const sourceLabel =
      sources.has('keyword') && sources.has('semantic')
        ? '关键词＋语义'
        : sources.has('semantic')
          ? '语义检索'
          : '关键词检索'
    const score = Math.round((example.slot_score || example.final_score || 0) * 100)
    const relationshipMeta =
      example.relationship_match === 'matched' && example.relationship_label
        ? `关系匹配：${example.relationship_label}`
        : example.relationship_match === 'mismatched'
          ? '关系不匹配，仅作备选'
          : '关系中性'
    return {
      num,
      name,
      value: example.unit_text,
      meta: `${sourceLabel} · ${relationshipMeta} · 槽位评分 ${score}% · ${example.prompt_included ? '已注入提示词' : '仅作备选'}`
    }
  }
  return [
    card('01', 'opening', '称谓格式'),
    card('02', 'safety', '问安表达'),
    card('03', 'remittance', '汇款表达'),
    card('04', 'closing', '结尾格式')
  ]
})

const validationCards = computed(() =>
  buildStyleTransferValidationCards(consistencyCheck.value)
)

function normalizeEvidence(rows) {
  const referenceMap = new Map(
    (result.value.evidence_references || []).map((item) => [item.unit_id, item])
  )
  const seen = new Set()
  return rows
    .map((row) => {
      const reference = referenceMap.get(row.unit_id) || {}
      return {
        target_span: row.target_span,
        target_label: row.target_label,
        record_id: row.record_id || reference.record_id,
        unit_id: row.unit_id || reference.unit_id,
        source_unit_type: row.source_unit_type || reference.unit_type,
        source_field: row.source_field || row.source_column || reference.source_column,
        source_text: row.source_text || row.evidence_text || row.unit_text || reference.unit_text,
        reason: row.reason || row.evidence_type || row.unit_type,
        evidence_role: row.evidence_role || 'style',
        retrieval_sources: row.retrieval_sources || reference.retrieval_sources || [],
        prompt_included: row.prompt_included ?? reference.prompt_included ?? false,
        slot_match: row.slot_match ?? false,
        similarity_score: row.similarity_score ?? reference.slot_score ?? 0
      }
    })
    .filter((row) => {
      const key = `${row.unit_id}|${row.target_span}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

function mergeEvidenceByKnowledgeUnit(rows) {
  const grouped = new Map()
  rows.forEach((row) => {
    const key = row.unit_id || `${row.record_id}|${row.source_text}`
    const current = grouped.get(key)
    if (!current) {
      grouped.set(key, {
        ...row,
        target_span: row.target_span,
        target_spans: [row.target_span].filter(Boolean)
      })
      return
    }
    if (row.target_span && !current.target_spans.includes(row.target_span)) {
      current.target_spans.push(row.target_span)
      current.target_span = current.target_spans.join(' / ')
    }
    current.similarity_score = Math.max(
      Number(current.similarity_score) || 0,
      Number(row.similarity_score) || 0
    )
    current.slot_match = current.slot_match || row.slot_match
  })
  return [...grouped.values()]
}

function evidenceSourceText(row) {
  if (row.source_text) return row.source_text
  return row.target_span || '暂无证据片段'
}

function retrievalReason(sources = []) {
  if (sources.includes('keyword') && sources.includes('semantic')) return 'hybrid_style_support'
  if (sources.includes('semantic')) return 'semantic_style_support'
  return 'lexical_style_support'
}

function evidenceTraceLabel(row) {
  const score = Math.round((Number(row.similarity_score) || 0) * 100)
  const injection = row.prompt_included ? '已注入 Prompt' : '检索候选'
  const slot = row.source_unit_type
    ? `${slotLabels[row.source_unit_type] || row.source_unit_type} · `
    : ''
  const method = row.slot_match ? '功能匹配' : '词句映射'
  return `${slot}${injection} · ${method} ${score}%`
}

function fieldLabel(field) {
  return fieldLabels[field] || '知识库来源字段'
}

function reasonLabel(reason) {
  return reasonLabels[reason] || fieldLabels[reason] || '知识库证据'
}

function clearContent() {
  plainText.value = ''
  result.value = {}
  generatedText.value = ''
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
      dry_run: false
    })
    generatedText.value = result.value.generated_text || ''
  } catch (requestError) {
    if (demoMode) {
      result.value = fallbackResult
      generatedText.value = fallbackResult.generated_text || ''
      error.value = demoFailureMessage('风格转换请求')
    } else {
      result.value = {}
      generatedText.value = ''
      error.value = apiFailureMessage(requestError, '风格转换请求')
    }
  } finally {
    loading.value = false
  }
}

</script>
