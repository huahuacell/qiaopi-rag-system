<template>
  <section class="page-stack">
    <div class="tool-surface">
      <div class="generation-controls">
        <el-input v-model="recordId" placeholder="记录 ID" />
        <el-button type="primary" :loading="loading" @click="runGeneration">
          <el-icon><Reading /></el-icon>
          生成解读
        </el-button>
      </div>
      <el-input
        v-model="originalText"
        type="textarea"
        :rows="4"
        placeholder="可选：粘贴侨批原文"
      />
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div v-loading="loading" class="two-column">
      <QiaopiTextPanel
        title="白话解读"
        :text="result.generated_text || ''"
        badge="生成结果"
      />

      <section class="summary-panel">
        <div class="panel-heading-row">
          <h3>结构化摘要</h3>
          <el-tag effect="plain">{{ result.record_id }}</el-tag>
        </div>
        <ul class="summary-list">
          <li v-for="item in result.summary" :key="item">{{ item }}</li>
        </ul>
        <div class="slot-grid">
          <div v-for="[key, value] in slotRows" :key="key">
            <span>{{ key }}</span>{{ value }}
          </div>
        </div>
      </section>
    </div>

    <section class="section-stack">
      <div class="panel-heading-row">
        <h3>证据</h3>
      </div>
      <EvidenceTable :rows="result.evidence || []" />
    </section>

    <section class="section-stack">
      <div class="panel-heading-row">
        <h3>证据映射</h3>
      </div>
      <EvidenceTable :rows="result.evidence_mapping || []" />
    </section>

    <ConsistencyPanel :check="result.consistency_check" />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { generatePlainInterpretation } from '../api/generation'
import ConsistencyPanel from '../components/ConsistencyPanel.vue'
import EvidenceTable from '../components/EvidenceTable.vue'
import QiaopiTextPanel from '../components/QiaopiTextPanel.vue'
import fallbackResult from '../mock/plain_interpretation.json'

const recordId = ref('CSQP-SFHC-TEXT-001')
const originalText = ref('')
const result = ref(fallbackResult)
const loading = ref(false)
const error = ref('')

const slotLabels = {
  sender: '寄信人',
  recipient: '收信人',
  origin_place: '来源地',
  destination_place: '目的地',
  money: '汇款',
  purpose: '用途',
  input_preview: '输入预览'
}

const slotRows = computed(() =>
  Object.entries(result.value.slots || {}).map(([key, value]) => [slotLabels[key] || key, value])
)

async function runGeneration() {
  loading.value = true
  error.value = ''
  try {
    result.value = await generatePlainInterpretation({
      record_id: recordId.value,
      original_text: originalText.value
    })
  } catch {
    result.value = fallbackResult
    error.value = '后端不可用，已加载白话解读本地 mock 数据。'
  } finally {
    loading.value = false
  }
}

onMounted(runGeneration)
</script>
