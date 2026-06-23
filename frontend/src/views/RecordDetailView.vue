<template>
  <section v-loading="loading" class="archive-detail-page">
    <div class="archive-detail-bg" aria-hidden="true">
      <span class="archive-detail-line line-a"></span>
      <span class="archive-detail-line line-b"></span>
      <span class="archive-detail-seal seal-a">批</span>
      <span class="archive-detail-seal seal-b">证</span>
      <span class="archive-detail-wash"></span>
    </div>

    <nav class="archive-detail-breadcrumb" aria-label="记录详情路径">
      <span>侨批 RAG</span>
      <i>›</i>
      <span>档案检索</span>
      <i>›</i>
      <span>记录详情</span>
      <i>›</i>
      <strong>{{ activeRecordId }}</strong>
    </nav>

    <section class="archive-record-header">
      <div class="archive-record-watermark" aria-hidden="true">批</div>
      <div class="archive-record-label">
        <span>馆藏记录 · ARCHIVE RECORD</span>
        <i></i>
      </div>
      <div class="archive-record-headline">
        <div>
          <h1>{{ detailTitle }}</h1>
          <p>{{ recordDescription }}</p>
        </div>
        <div class="archive-record-switcher">
          <label for="record-id-input">RECORD LOOKUP</label>
          <div class="archive-record-input">
            <input
              id="record-id-input"
              v-model="recordIdInput"
              type="text"
              placeholder="CSQP-SFHC-TEXT-001"
              @keyup.enter="openRecord"
            />
            <button type="button" @click="openRecord">打开</button>
          </div>
        </div>
      </div>

      <div class="archive-record-tags">
        <span class="archive-id-tag primary">{{ activeRecordId }}</span>
        <span class="archive-id-tag">{{ archiveCode }}</span>
        <span class="archive-id-tag ready">Evidence Ready</span>
      </div>

      <div class="archive-record-chips" aria-label="记录元数据摘要">
        <span v-for="chip in headerChips" :key="chip.label" :class="{ red: chip.red }">
          {{ chip.label }}：{{ chip.value }}
        </span>
      </div>
    </section>

    <div v-if="error" class="archive-detail-note warning" role="status">
      <span>i</span>
      <p>{{ error }}</p>
    </div>

    <div class="archive-detail-layout">
      <main class="archive-detail-main">
        <section class="archive-detail-card original-card">
          <header class="archive-card-title">
            <i></i>
            <strong>侨批原文</strong>
            <span>原文转写 · Transcript</span>
          </header>
          <div class="archive-letter-paper">
            <div class="letter-margin" aria-hidden="true"></div>
            <div class="letter-seal" aria-hidden="true">侨批</div>
            <p v-for="(line, index) in letterLines" :key="`${line}-${index}`">
              {{ line }}
            </p>
          </div>
        </section>

        <section class="archive-detail-card">
          <header class="archive-card-title">
            <i></i>
            <strong>白话释读</strong>
            <span>RAG Summary</span>
          </header>
          <div class="archive-summary-paper">
            <p>{{ summaryText }}</p>
          </div>
        </section>

        <section class="archive-detail-card">
          <header class="archive-card-title">
            <i></i>
            <strong>证据映射</strong>
            <span>Evidence Map</span>
          </header>
          <div class="archive-evidence-grid" :class="{ empty: !evidenceRows.length }">
            <template v-if="evidenceRows.length">
              <div class="archive-evidence-head">证据类型</div>
              <div class="archive-evidence-head">原文片段</div>
              <div class="archive-evidence-head">解释含义</div>

              <template v-for="(row, index) in evidenceRows" :key="`${row.source_text}-${index}`">
                <div class="archive-evidence-type">
                  <span>{{ row.reason || fieldLabel(row.source_field) }}</span>
                  <em v-if="row.similarity_score !== undefined">{{ scoreLabel(row.similarity_score) }}</em>
                </div>
                <blockquote>{{ row.source_text || row.target_span || '暂无原文证据' }}</blockquote>
                <p>{{ evidenceMeaning(row) }}</p>
              </template>
            </template>
            <p v-else class="archive-empty-copy">暂无证据片段，后端返回后将在此展示句级依据。</p>
          </div>
        </section>

        <section class="archive-related-section">
          <div class="archive-related-title">
            <i></i>
            <strong>相关档案线索</strong>
            <span></span>
          </div>
          <div class="archive-related-grid">
            <article v-for="item in relatedArchives" :key="item.label" class="archive-related-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.description }}</p>
              <router-link v-if="item.to" :to="item.to" class="archive-related-link">
                前往检索 →
              </router-link>
              <small v-else class="archive-related-status">线索待检索确认</small>
            </article>
          </div>
        </section>

        <aside class="archive-detail-note">
          <span>i</span>
          <p>
            当前页面读取正式记录详情、实体与证据接口。仅在显式演示模式下，接口失败才会加载本地演示数据。
          </p>
        </aside>
      </main>

      <aside class="archive-detail-sidebar">
        <section class="archive-detail-card side-card">
          <header class="archive-card-title">
            <i></i>
            <strong>档案元数据</strong>
          </header>
          <div class="archive-meta-list">
            <div v-for="row in sidebarMetadataRows" :key="row.label">
              <span>{{ row.label }}</span>
              <strong :class="{ mono: row.mono }">{{ row.value }}</strong>
            </div>
          </div>
        </section>

        <section class="archive-detail-card side-card">
          <header class="archive-card-title">
            <i></i>
            <strong>实体识别</strong>
          </header>
          <div class="archive-entity-groups">
            <div v-for="group in entityGroups" :key="group.label" class="archive-entity-group">
              <span>{{ group.label }}</span>
              <div>
                <em v-for="item in group.items" :key="`${group.label}-${item.value}`">
                  {{ item.value }}
                </em>
              </div>
            </div>
          </div>
        </section>

        <section class="archive-detail-card side-card trace-card">
          <header class="archive-card-title trace-title">
            <i></i>
            <strong>可追溯说明</strong>
            <span>Consistent</span>
          </header>
          <div class="archive-trace-list">
            <div v-for="block in traceBlocks" :key="block.key">
              <span>{{ block.key }}</span>
              <p>{{ block.value }}</p>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchRecordDetail, fetchRecordEntities, fetchRecordEvidence } from '../api/records'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackRecord from '../mock/record_detail.json'
import { buildRelatedArchiveItems } from '../utils/recordDetailPresentation'

const route = useRoute()
const router = useRouter()
const recordIdInput = ref(route.params.recordId || 'CSQP-SFHC-TEXT-001')
const detail = ref({})
const entities = ref([])
const evidence = ref([])
const loading = ref(false)
const error = ref('')

const metadataLabels = {
  record_id: '记录编号',
  title: '标题',
  origin_place: '来源地',
  destination_place: '目的地',
  date: '年代',
  date_text: '日期',
  year_normalized: '年份',
  sender: '寄信人',
  recipient: '收信人',
  sender_name_clean: '寄信人',
  recipient_name_clean: '收信人',
  kinship: '亲属关系',
  relationship_type: '亲属关系',
  money: '汇款',
  main_intent: '主要意图',
  text_quality_level: '文本质量',
  place_mentions_normalized: '地点提及',
  theme_tags: '主题标签',
  retrieval_keywords: '检索关键词',
  has_remittance: '汇款状态'
}

const typeLabels = {
  person: '人物',
  place: '地点',
  kinship: '亲属',
  money: '金额',
  time: '时间',
  date: '时间',
  action: '行为',
  organization: '机构'
}

const activeRecordId = computed(() => detail.value.record_id || route.params.recordId || 'CSQP-SFHC-TEXT-001')
const detailTitle = computed(() => detail.value.title || detail.value.title_reference || makeTitleFromMetadata() || '侨批档案记录')
const archiveCode = computed(() => detail.value.archive_id || detail.value.file_no || `QP-REC-${String(activeRecordId.value).slice(-8)}`)
const bodyText = computed(() => detail.value.original_text || detail.value.body_clean || detail.value.body_core || '')
const summaryText = computed(() =>
  detail.value.rag_summary_text ||
  detail.value.normalized_text ||
  detail.value.body_core ||
  '暂无白话释读。后端返回摘要后将在此展示面向读者的解释文本。'
)

const recordDescription = computed(() => {
  const origin = getMeta('origin_place') || '侨居地'
  const dest = getMeta('destination_place') || '侨乡'
  const kinship = getMeta('kinship') || getMeta('relationship_type') || getMeta('recipient') || '亲属'
  return `一封关于${origin}与${dest}之间平安问候、汇款托带与${kinship}联系的侨批记录。`
})

const headerChips = computed(() => [
  { label: '来源地', value: getMeta('origin_place') || '待考' },
  { label: '收信人', value: getMeta('recipient') || getMeta('recipient_name_clean') || '待考' },
  { label: '年代', value: getMeta('date') || getMeta('date_text') || getMeta('year_normalized') || '待考' },
  { label: '类型', value: getMeta('main_intent') || '侨批文本' },
  { label: '证据状态', value: evidence.value.length ? '可追溯' : '待补充', red: true }
])

const letterLines = computed(() => {
  const text = bodyText.value || '暂无原文转写。'
  const normalized = String(text).replace(/\r/g, '').trim()
  if (normalized.includes('\n')) return normalized.split('\n')
  return normalized
    .replace(/([。！？；])/g, '$1\n')
    .split('\n')
    .filter(Boolean)
})

const rawMetadataRows = computed(() => {
  const metadata = detail.value.metadata || {}
  const merged = {
    record_id: activeRecordId.value,
    title: detailTitle.value,
    ...metadata,
    sender_name_clean: detail.value.sender_name_clean || detail.value.sender,
    recipient_name_clean: detail.value.recipient_name_clean || detail.value.recipient,
    date_text: detail.value.date_text,
    year_normalized: detail.value.year_normalized,
    relationship_type: detail.value.relationship_type,
    main_intent: detail.value.main_intent,
    place_mentions_normalized: detail.value.place_mentions_normalized,
    theme_tags: detail.value.theme_tags,
    retrieval_keywords: detail.value.retrieval_keywords
  }

  return Object.entries(merged)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => ({
      key,
      label: metadataLabels[key] || key,
      value: formatValue(value),
      mono: key === 'record_id' || key.includes('year') || key.includes('date')
    }))
})

const sidebarMetadataRows = computed(() => {
  const preferred = ['record_id', 'title', 'origin_place', 'destination_place', 'date', 'date_text', 'year_normalized', 'kinship', 'relationship_type', 'main_intent']
  const rows = []
  preferred.forEach((key) => {
    const row = rawMetadataRows.value.find((item) => item.key === key)
    if (row && !rows.some((item) => item.label === row.label)) rows.push(row)
  })
  rawMetadataRows.value.forEach((row) => {
    if (rows.length < 8 && !rows.some((item) => item.label === row.label)) rows.push(row)
  })
  return rows
})

const evidenceRows = computed(() =>
  evidence.value.map((row) => ({
    target_span: row.target_span,
    source_field: row.source_field || row.source_column,
    source_text: row.source_text || row.evidence_text,
    reason: row.reason || row.evidence_type || fieldLabel(row.source_field || row.source_column),
    similarity_score: row.similarity_score
  }))
)

const entityGroups = computed(() => {
  const groups = new Map()
  entities.value.forEach((entity) => {
    const type = entity.entity_type || 'other'
    const label = typeLabels[type] || type
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label).push({
      value: entity.value || entity.source_text || '未命名实体',
      confidence: entity.confidence
    })
  })

  if (!groups.size) {
    return [
      { label: '人物', items: [{ value: getMeta('recipient') || '待识别' }] },
      { label: '地点', items: [{ value: getMeta('origin_place') || '待识别' }] }
    ]
  }

  return Array.from(groups.entries()).map(([label, items]) => ({ label, items }))
})

const traceBlocks = computed(() => [
  {
    key: '原文依据',
    value: evidence.value.length ? `当前记录已返回 ${evidence.value.length} 条证据片段，释读内容可回看原文字段。` : '暂无后端证据片段，页面保留证据映射位置。'
  },
  {
    key: '证据粒度',
    value: evidence.value.some((row) => row.target_span) ? '支持生成片段到原文片段的映射。' : '以句级或字段级证据片段展示。'
  },
  {
    key: '生成边界',
    value: '白话释读优先依据原文、规范文本与检索证据，不补充原文之外的人物和事件。'
  },
  {
    key: '一致性检查',
    value: error.value
      ? demoMode
        ? '当前为显式演示数据，正式接口恢复后可重新校验。'
        : '正式接口请求失败，页面未加载 Mock 数据。'
      : '当前详情、实体与证据接口已完成同页展示。'
  }
])

const relatedArchives = computed(() => buildRelatedArchiveItems(detail.value))

function getMeta(key) {
  const metadata = detail.value.metadata || {}
  return metadata[key] ?? detail.value[key]
}

function makeTitleFromMetadata() {
  const origin = getMeta('origin_place')
  const dest = getMeta('destination_place')
  if (origin && dest) return `${origin}寄往${dest}的侨批`
  return ''
}

function formatValue(value) {
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'object') return JSON.stringify(value)
  if (value === 1) return '是'
  if (value === 0) return '否'
  return String(value)
}

function fieldLabel(field) {
  const labels = {
    original_text: '原文',
    normalized_text: '规范文本',
    destination_place: '目的地',
    origin_place: '来源地',
    style_pattern: '风格模式',
    body_core: '核心正文',
    rag_summary_text: 'RAG 摘要'
  }
  return labels[field] || field || '证据'
}

function evidenceMeaning(row) {
  if (row.target_span) return `支持生成片段：“${row.target_span}”`
  if (row.reason) return row.reason
  return `${fieldLabel(row.source_field)}字段中的可追溯依据`
}

function scoreLabel(score) {
  return `${Math.round((score || 0) * 100)}%`
}

function openRecord() {
  router.push(`/records/${recordIdInput.value || 'CSQP-SFHC-TEXT-001'}`)
}

async function loadRecord(recordId) {
  loading.value = true
  error.value = ''
  recordIdInput.value = recordId
  try {
    const [detailPayload, entitiesPayload, evidencePayload] = await Promise.all([
      fetchRecordDetail(recordId),
      fetchRecordEntities(recordId),
      fetchRecordEvidence(recordId)
    ])
    detail.value = detailPayload || {}
    entities.value = entitiesPayload?.entities || []
    evidence.value = evidencePayload?.evidence || []
  } catch (requestError) {
    if (demoMode) {
      detail.value = { ...fallbackRecord, record_id: recordId }
      entities.value = fallbackRecord.entities || []
      evidence.value = fallbackRecord.evidence || []
      error.value = demoFailureMessage('记录详情请求')
    } else {
      detail.value = { record_id: recordId }
      entities.value = []
      evidence.value = []
      error.value = apiFailureMessage(requestError, '记录详情请求')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => loadRecord(route.params.recordId || 'CSQP-SFHC-TEXT-001'))

watch(
  () => route.params.recordId,
  (recordId) => loadRecord(recordId || 'CSQP-SFHC-TEXT-001')
)
</script>
