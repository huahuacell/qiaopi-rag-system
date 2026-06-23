<template>
  <section class="archive-nlp-page">
    <div class="archive-nlp-bg" aria-hidden="true">
      <span class="archive-nlp-line line-a"></span>
      <span class="archive-nlp-line line-b"></span>
      <span class="archive-nlp-seal seal-a">析</span>
      <span class="archive-nlp-seal seal-b">证</span>
      <span class="archive-nlp-wash"></span>
    </div>

    <nav class="archive-nlp-breadcrumb" aria-label="在线 NLP 页面路径">
      <span>侨批 RAG</span>
      <i>›</i>
      <span>文本处理</span>
      <i>›</i>
      <strong>在线 NLP</strong>
    </nav>

    <header class="archive-nlp-header">
      <div class="archive-nlp-redline" aria-hidden="true"></div>
      <div class="archive-nlp-header-copy">
        <div class="archive-nlp-label-row">
          <span>在线解析 · ONLINE NLP</span>
          <em>Traceable Rule Pipeline</em>
        </div>
        <h1>从侨批原文中抽取人物、地点与汇款线索</h1>
        <p>
          在线与离线建库共享同一套规范化规则。每个实体、关系和生成槽位均保留原文证据、
          双重半开区间偏移、规则版本、置信度与人工复核状态。
        </p>
      </div>
      <aside class="archive-nlp-header-mark">
        <div aria-hidden="true">析</div>
        <span>运行引擎</span>
        <strong>{{ engineLabel }}</strong>
        <em>{{ result.pipeline_version || 'QP-NLP-PENDING' }}</em>
      </aside>
    </header>

    <div v-if="error" class="archive-nlp-notice error" role="alert">
      <span>!</span>
      <p>{{ error }}</p>
    </div>

    <section class="archive-nlp-input-card">
      <header class="archive-nlp-card-head">
        <div>
          <small>01 · SOURCE INPUT</small>
          <h2>输入待解析文本</h2>
          <p>支持侨批原文和现代家书文本，最多 20,000 字；接口失败时不会静默加载 Mock。</p>
        </div>
        <div class="archive-nlp-task-tabs" role="tablist" aria-label="NLP 任务类型">
          <button
            v-for="option in taskOptions"
            :key="option.value"
            type="button"
            role="tab"
            :aria-selected="task === option.value"
            :class="{ active: task === option.value }"
            :disabled="loading"
            @click="task = option.value"
          >
            {{ option.label }}
          </button>
        </div>
      </header>

      <div class="archive-nlp-editor">
        <i aria-hidden="true"></i>
        <textarea
          v-model="text"
          rows="9"
          maxlength="20000"
          :disabled="loading"
          placeholder="输入侨批原文或现代家书文本……"
          @keydown.ctrl.enter.prevent="runAnalysis"
          @keydown.meta.enter.prevent="runAnalysis"
        ></textarea>
      </div>

      <div class="archive-nlp-input-meta">
        <div>
          <span>规范化</span>
          <span>实体识别</span>
          <span>关系抽取</span>
          <span>任务槽位</span>
        </div>
        <p><strong>{{ text.length.toLocaleString() }}</strong> / 20,000 字 · Ctrl / ⌘ + Enter 执行</p>
      </div>

      <footer class="archive-nlp-actions">
        <button type="button" :disabled="loading" @click="restoreSample">恢复示例</button>
        <button type="button" :disabled="loading || !text" @click="clearText">清空内容</button>
        <button
          class="primary"
          type="button"
          :disabled="!canAnalyze"
          @click="runAnalysis"
        >
          <span v-if="loading" class="archive-nlp-spinner" aria-hidden="true"></span>
          {{ loading ? '正在解析…' : '执行在线 NLP' }}
        </button>
      </footer>
    </section>

    <div v-if="isResultStale" class="archive-nlp-notice stale" role="status">
      <span>i</span>
      <p>输入文本或任务类型已改变。上一轮结果已收起，请重新执行分析以避免误读过期结果。</p>
    </div>

    <template v-if="hasCurrentResult">
      <section class="archive-nlp-runtime-strip" aria-label="本次解析运行信息">
        <article>
          <span>任务</span>
          <strong>{{ taskLabel(result.task) }}</strong>
        </article>
        <article>
          <span>规则引擎</span>
          <strong>{{ engineLabel }}</strong>
        </article>
        <article>
          <span>规范化版本</span>
          <strong>{{ result.normalization_version }}</strong>
        </article>
        <article>
          <span>结果状态</span>
          <strong :class="{ warning: result.review_required }">
            {{ result.review_required ? '需要人工复核' : '规则检查通过' }}
          </strong>
        </article>
      </section>

      <section class="archive-nlp-summary-grid" aria-label="抽取结果摘要">
        <article v-for="card in summaryCards" :key="card.index" :class="{ warning: card.warning }">
          <em>{{ card.index }}</em>
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.note }}</small>
          <b aria-hidden="true">{{ card.index }}</b>
        </article>
      </section>

      <div v-if="result.review_required" class="archive-nlp-review-banner" role="status">
        <div>
          <span>复</span>
          <strong>该结果需要人工复核</strong>
        </div>
        <ul>
          <li v-for="reason in result.review_reasons" :key="reason">{{ reason }}</li>
        </ul>
      </div>

      <div v-if="spanIntegrityFailures" class="archive-nlp-notice error" role="alert">
        <span>!</span>
        <p>{{ spanIntegrityFailures }} 个抽取项未通过前端偏移一致性检查，请核对接口返回。</p>
      </div>

      <section class="archive-nlp-card archive-nlp-normalization-card">
        <header class="archive-nlp-card-head compact">
          <div>
            <small>02 · NORMALIZATION</small>
            <h2>原文与规范文本</h2>
            <p>双栏对照用于验证在线分析与离线入库是否采用同一套文本规范。</p>
          </div>
          <span
            class="archive-nlp-state-tag"
            :class="{ changed: result.normalization_changed }"
          >
            {{ result.normalization_changed ? '文本已规范化' : '原文无需改写' }}
          </span>
        </header>

        <div class="archive-nlp-text-compare">
          <article>
            <header>
              <span>原始文本</span>
              <em>ORIGINAL</em>
            </header>
            <pre>{{ result.original_text }}</pre>
          </article>
          <article>
            <header>
              <span>规范文本</span>
              <em>NORMALIZED</em>
            </header>
            <pre>{{ result.normalized_text }}</pre>
          </article>
        </div>
      </section>

      <section class="archive-nlp-card">
        <header class="archive-nlp-card-head compact">
          <div>
            <small>03 · ENTITY EXTRACTION</small>
            <h2>实体与规范值</h2>
            <p>人物、亲属称谓、地点、日期、金额与书信套语均保留原文出处。</p>
          </div>
          <code>{{ result.entity_extractor_version }}</code>
        </header>

        <div v-if="result.entities.length" class="archive-nlp-entity-grid">
          <article
            v-for="entity in result.entities"
            :key="entity.entity_id"
            :class="{ review: entity.needs_review, invalid: !isSpanValid(entity) }"
          >
            <header>
              <span>{{ entityTypeLabel(entity.entity_type) }}</span>
              <em>{{ confidenceText(entity.confidence) }}</em>
            </header>
            <h3>{{ nlpValueText(entity.value) }}</h3>
            <blockquote>「{{ entity.source_text }}」</blockquote>
            <p
              v-if="entity.normalized_source_text && entity.normalized_source_text !== entity.source_text"
              class="archive-nlp-normalized-source"
            >
              规范片段：{{ entity.normalized_source_text }}
            </p>
            <dl>
              <div><dt>原文偏移</dt><dd>{{ formatOffset(entity) }}</dd></div>
              <div><dt>规范偏移</dt><dd>{{ formatOffset(entity, true) }}</dd></div>
              <div><dt>规则</dt><dd>{{ entity.rule_id || '—' }}</dd></div>
              <div><dt>抽取器</dt><dd>{{ entity.extractor_version }}</dd></div>
            </dl>
            <footer>
              <span :class="{ warning: entity.needs_review }">
                {{ entity.needs_review ? '需要人工复核' : '复核状态：通过' }}
              </span>
              <em :class="{ invalid: !isSpanValid(entity) }">
                {{ isSpanValid(entity) ? '偏移一致' : '偏移异常' }}
              </em>
            </footer>
          </article>
        </div>
        <div v-else class="archive-nlp-empty">
          <span aria-hidden="true">实</span>
          <p>当前文本未抽取到实体。</p>
        </div>
      </section>

      <section class="archive-nlp-card">
        <header class="archive-nlp-card-head compact">
          <div>
            <small>04 · RELATION EXTRACTION</small>
            <h2>关系与证据链</h2>
            <p>关系两端、证据文本、规则版本和双重偏移在同一卡片内完整呈现。</p>
          </div>
          <code>{{ result.relation_extractor_version }}</code>
        </header>

        <div v-if="result.relations.length" class="archive-nlp-relation-list">
          <article
            v-for="relation in result.relations"
            :key="relation.relation_id"
            :class="{ review: relation.needs_review, invalid: !isSpanValid(relation) }"
          >
            <div class="archive-nlp-relation-main">
              <span>{{ relationTypeLabel(relation.relation_type) }}</span>
              <div>
                <strong>{{ nlpValueText(relation.source_value) }}</strong>
                <i aria-hidden="true">→</i>
                <strong>{{ nlpValueText(relation.target_value) }}</strong>
              </div>
              <em>{{ confidenceText(relation.confidence) }}</em>
            </div>
            <blockquote>「{{ relation.evidence_text || relation.source_text }}」</blockquote>
            <div class="archive-nlp-trace-grid">
              <p><span>原文偏移</span><code>{{ formatOffset(relation) }}</code></p>
              <p><span>规范偏移</span><code>{{ formatOffset(relation, true) }}</code></p>
              <p><span>规则</span><code>{{ relation.rule_id || '—' }}</code></p>
              <p><span>抽取器</span><code>{{ relation.extractor_version }}</code></p>
            </div>
            <footer>
              <span :class="{ warning: relation.needs_review }">
                {{ relation.needs_review ? '需要人工复核' : '复核状态：通过' }}
              </span>
              <em :class="{ invalid: !isSpanValid(relation) }">
                {{ isSpanValid(relation) ? '偏移一致' : '偏移异常' }}
              </em>
            </footer>
          </article>
        </div>
        <div v-else class="archive-nlp-empty">
          <span aria-hidden="true">关</span>
          <p>当前文本未抽取到关系。</p>
        </div>
      </section>

      <section class="archive-nlp-card">
        <header class="archive-nlp-card-head compact">
          <div>
            <small>05 · TASK SLOTS</small>
            <h2>生成任务槽位</h2>
            <p>槽位可供白话释读、侨批体生成和后续一致性检查使用。</p>
          </div>
          <code>{{ result.slot_extractor_version }}</code>
        </header>

        <div v-if="result.slots.length" class="archive-nlp-slot-grid">
          <article
            v-for="slot in result.slots"
            :key="slot.slot_id"
            :class="{ review: slot.needs_review, invalid: !isSpanValid(slot) }"
          >
            <header>
              <span>{{ slotLabel(slot.slot_name) }}</span>
              <em>{{ confidenceText(slot.confidence) }}</em>
            </header>
            <strong>{{ nlpValueText(slot.value) }}</strong>
            <blockquote>「{{ slot.source_text }}」</blockquote>
            <dl>
              <div><dt>原文偏移</dt><dd>{{ formatOffset(slot) }}</dd></div>
              <div><dt>规范偏移</dt><dd>{{ formatOffset(slot, true) }}</dd></div>
              <div><dt>规则</dt><dd>{{ slot.rule_id || '—' }}</dd></div>
              <div><dt>抽取器</dt><dd>{{ slot.extractor_version }}</dd></div>
            </dl>
            <footer>
              <span :class="{ warning: slot.needs_review }">
                {{ slot.needs_review ? '需要人工复核' : '复核状态：通过' }}
              </span>
              <em :class="{ invalid: !isSpanValid(slot) }">
                {{ isSpanValid(slot) ? '偏移一致' : '偏移异常' }}
              </em>
            </footer>
          </article>
        </div>
        <div v-else class="archive-nlp-empty">
          <span aria-hidden="true">槽</span>
          <p>当前文本未抽取到任务槽位。</p>
        </div>
      </section>

    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { analyzeNlpText } from '../api/nlp'
import { apiFailureMessage } from '../config/runtime'
import {
  ENTITY_TYPE_LABELS,
  RELATION_TYPE_LABELS,
  SLOT_LABELS,
  confidenceText,
  formatOffset,
  nlpValueText,
  normalizeNlpResult,
  validateSpanItem
} from '../utils/nlpPresentation'

const sampleText =
  '寄批人：儿海泉\n收批人：母亲大人\n\n母亲大人尊前：我在星洲平安，今寄回中央法币陆元，给家中买米和药。戊七月初十日。'

const taskOptions = [
  { value: 'general', label: '通用抽取' },
  { value: 'interpretation', label: '白话释读槽位' },
  { value: 'style_transfer', label: '风格转换槽位' }
]

const text = ref(sampleText)
const task = ref('general')
const loading = ref(false)
const error = ref('')
const analyzedText = ref('')
const analyzedTask = ref('')
const result = reactive(normalizeNlpResult())

const hasResult = computed(() => Boolean(result.pipeline_version))
const isResultStale = computed(
  () =>
    hasResult.value &&
    (text.value !== analyzedText.value || task.value !== analyzedTask.value)
)
const hasCurrentResult = computed(() => hasResult.value && !isResultStale.value)
const canAnalyze = computed(() => Boolean(text.value.trim()) && !loading.value)
const engineLabel = computed(() =>
  result.engine === 'deterministic_rule' ? '确定性规则' : '等待分析'
)
const spanIntegrityFailures = computed(() =>
  [...result.entities, ...result.relations, ...result.slots].filter(
    (item) => !isSpanValid(item)
  ).length
)
const summaryCards = computed(() => [
  {
    index: '01',
    label: '实体',
    value: result.summary.entity_count,
    note: result.entity_extractor_version,
    warning: false
  },
  {
    index: '02',
    label: '关系',
    value: result.summary.relation_count,
    note: result.relation_extractor_version,
    warning: false
  },
  {
    index: '03',
    label: '任务槽位',
    value: result.summary.slot_count,
    note: result.slot_extractor_version,
    warning: false
  },
  {
    index: '04',
    label: '人工复核',
    value: result.review_required
      ? result.summary.review_item_count || '需要'
      : '无需',
    note: result.review_required
      ? result.summary.review_item_count
        ? '存在低置信抽取项'
        : '存在文本级复核原因'
      : '全部抽取项通过',
    warning: result.review_required
  }
])

function entityTypeLabel(value) {
  return ENTITY_TYPE_LABELS[value] || value || '未分类实体'
}

function relationTypeLabel(value) {
  return RELATION_TYPE_LABELS[value] || value || '未分类关系'
}

function slotLabel(value) {
  return SLOT_LABELS[value] || value || '未分类槽位'
}

function taskLabel(value) {
  return taskOptions.find((option) => option.value === value)?.label || value || '通用抽取'
}

function isSpanValid(item) {
  return validateSpanItem(item, result.original_text, result.normalized_text)
}

function clearResult() {
  Object.assign(result, normalizeNlpResult())
  analyzedText.value = ''
  analyzedTask.value = ''
}

async function runAnalysis() {
  if (!canAnalyze.value) return

  const requestedText = text.value
  const requestedTask = task.value
  loading.value = true
  error.value = ''
  clearResult()

  try {
    const payload = await analyzeNlpText(requestedText, requestedTask)
    Object.assign(result, normalizeNlpResult(payload))
    analyzedText.value = requestedText
    analyzedTask.value = requestedTask
  } catch (requestError) {
    clearResult()
    error.value = apiFailureMessage(requestError, '在线 NLP 请求')
  } finally {
    loading.value = false
  }
}

function restoreSample() {
  text.value = sampleText
  task.value = 'general'
  error.value = ''
  clearResult()
}

function clearText() {
  text.value = ''
  error.value = ''
  clearResult()
}

onMounted(runAnalysis)
</script>

<style src="../assets/styles/online-nlp.css"></style>
