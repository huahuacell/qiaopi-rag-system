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
      <span>侨批档案</span>
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
        <span>馆藏记录</span>
        <i></i>
      </div>
      <div class="archive-record-headline">
        <div>
          <h1>{{ detailTitle }}</h1>
          <p>查看本条侨批的原文转写与档案元数据。</p>
        </div>
        <div class="archive-record-switcher">
          <label for="record-id-input">记录编号</label>
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
    </section>

    <div v-if="error" class="archive-detail-note warning" role="status">
      <span>i</span>
      <p>{{ error }}</p>
    </div>

    <div class="archive-detail-layout archive-detail-layout--record-only">
      <main class="archive-detail-main">
        <section class="archive-detail-card original-card">
          <header class="archive-card-title">
            <i></i>
            <strong>侨批原文</strong>
            <span>原文转写</span>
          </header>
          <div class="archive-letter-paper">
            <div class="letter-margin" aria-hidden="true"></div>
            <div class="letter-seal" aria-hidden="true">侨批</div>
            <p v-for="(line, index) in letterLines" :key="`${line}-${index}`">
              {{ line }}
            </p>
          </div>
        </section>
      </main>

      <aside class="archive-detail-sidebar record-only-sidebar">
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
            <p v-if="!sidebarMetadataRows.length" class="archive-empty-copy">暂无档案元数据。</p>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchRecordDetail } from '../api/records'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackRecord from '../mock/record_detail.json'
import { buildRecordMetadataRows } from '../utils/recordDetailPresentation'

const route = useRoute()
const router = useRouter()
const recordIdInput = ref(route.params.recordId || 'CSQP-SFHC-TEXT-001')
const detail = ref({})
const loading = ref(false)
const error = ref('')

const activeRecordId = computed(() => detail.value.record_id || route.params.recordId || 'CSQP-SFHC-TEXT-001')
const detailTitle = computed(() => detail.value.title || detail.value.title_reference || makeTitleFromMetadata() || '侨批档案记录')
const bodyText = computed(() => detail.value.original_text || detail.value.body_clean || detail.value.body_core || '')

const letterLines = computed(() => {
  const text = bodyText.value || '暂无原文转写。'
  const normalized = String(text).replace(/\r/g, '').trim()
  if (normalized.includes('\n')) return normalized.split('\n')
  return normalized
    .replace(/([。！？；])/g, '$1\n')
    .split('\n')
    .filter(Boolean)
})

const sidebarMetadataRows = computed(() =>
  buildRecordMetadataRows(detail.value, activeRecordId.value, detailTitle.value)
)

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

function openRecord() {
  router.push(`/records/${recordIdInput.value || 'CSQP-SFHC-TEXT-001'}`)
}

async function loadRecord(recordId) {
  loading.value = true
  error.value = ''
  recordIdInput.value = recordId
  try {
    const detailPayload = await fetchRecordDetail(recordId)
    detail.value = detailPayload || {}
  } catch (requestError) {
    if (demoMode) {
      detail.value = { ...fallbackRecord, record_id: recordId }
      error.value = demoFailureMessage('记录详情请求')
    } else {
      detail.value = { record_id: recordId }
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

<style scoped>
.archive-detail-layout--record-only {
  grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
  align-items: stretch;
}

.archive-detail-layout--record-only > .archive-detail-main,
.archive-detail-layout--record-only > .record-only-sidebar {
  display: flex;
  align-self: stretch;
}

.archive-detail-layout--record-only .original-card,
.archive-detail-layout--record-only .record-only-sidebar > .side-card {
  width: 100%;
  height: 100%;
  margin-bottom: 0;
}

.archive-detail-layout--record-only .record-only-sidebar {
  position: relative;
  top: auto;
}

@media (max-width: 1180px) {
  .archive-detail-layout--record-only {
    grid-template-columns: minmax(0, 1fr);
  }

  .archive-detail-layout--record-only > .archive-detail-main,
  .archive-detail-layout--record-only > .record-only-sidebar {
    display: block;
  }

  .archive-detail-layout--record-only .original-card,
  .archive-detail-layout--record-only .record-only-sidebar > .side-card {
    height: auto;
    margin-bottom: 16px;
  }
}
</style>
