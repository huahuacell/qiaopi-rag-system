<template>
  <section v-loading="loading" class="page-stack">
    <div class="detail-toolbar">
      <el-input v-model="recordIdInput" class="record-input" placeholder="记录 ID" />
      <el-button type="primary" @click="openRecord">
        <el-icon><View /></el-icon>
        打开
      </el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <section class="record-hero">
      <div>
        <h2>{{ detail.title }}</h2>
        <div class="record-id">{{ detail.record_id }}</div>
      </div>
      <el-tag type="success">{{ detail.metadata?.money }}</el-tag>
    </section>

    <section class="metadata-grid">
      <div v-for="[key, value] in metadataRows" :key="key">
        <span>{{ key }}</span>{{ value }}
      </div>
    </section>

    <div class="two-column">
      <QiaopiTextPanel title="侨批原文" :text="detail.original_text || ''" badge="原文" />
      <QiaopiTextPanel title="规范文本" :text="detail.normalized_text || ''" badge="白话" />
    </div>

    <section class="section-stack">
      <div class="panel-heading-row">
        <h3>抽取实体</h3>
        <el-tag effect="plain">{{ entities.length }}</el-tag>
      </div>
      <div class="entity-grid">
        <EntityCard v-for="entity in entities" :key="`${entity.entity_type}-${entity.value}`" :entity="entity" />
      </div>
    </section>

    <section class="section-stack">
      <div class="panel-heading-row">
        <h3>证据</h3>
      </div>
      <EvidenceTable :rows="detail.evidence || []" />
    </section>

    <section class="section-stack">
      <div class="panel-heading-row">
        <h3>相似记录</h3>
        <el-tag effect="plain">{{ similar.total || 0 }}</el-tag>
      </div>
      <div class="result-list">
        <SearchResultCard
          v-for="result in similar.results"
          :key="result.record_id"
          :result="result"
        />
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchRecordDetail, fetchRecordEntities, fetchSimilarRecords } from '../api/records'
import EntityCard from '../components/EntityCard.vue'
import EvidenceTable from '../components/EvidenceTable.vue'
import QiaopiTextPanel from '../components/QiaopiTextPanel.vue'
import SearchResultCard from '../components/SearchResultCard.vue'
import fallbackRecord from '../mock/record_detail.json'
import fallbackSearch from '../mock/search_results.json'

const route = useRoute()
const router = useRouter()
const recordIdInput = ref(route.params.recordId || 'CSQP-SFHC-TEXT-001')
const detail = ref({})
const entities = ref([])
const similar = ref({ total: 0, results: [] })
const loading = ref(false)
const error = ref('')

const metadataLabels = {
  origin_place: '来源地',
  destination_place: '目的地',
  date: '年代',
  sender: '寄信人',
  recipient: '收信人',
  kinship: '亲属关系',
  money: '汇款'
}

const metadataRows = computed(() =>
  Object.entries(detail.value.metadata || {}).map(([key, value]) => [metadataLabels[key] || key, value])
)

function openRecord() {
  router.push(`/records/${recordIdInput.value || 'CSQP-SFHC-TEXT-001'}`)
}

async function loadRecord(recordId) {
  loading.value = true
  error.value = ''
  recordIdInput.value = recordId
  try {
    const [detailPayload, entitiesPayload, similarPayload] = await Promise.all([
      fetchRecordDetail(recordId),
      fetchRecordEntities(recordId),
      fetchSimilarRecords(recordId)
    ])
    detail.value = detailPayload
    entities.value = entitiesPayload.entities
    similar.value = similarPayload
  } catch {
    detail.value = { ...fallbackRecord, record_id: recordId }
    entities.value = fallbackRecord.entities
    similar.value = { ...fallbackSearch, mode: 'similar', query: recordId }
    error.value = '后端不可用，已加载记录详情本地 mock 数据。'
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
