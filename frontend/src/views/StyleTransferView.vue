<template>
  <section class="page-stack">
    <div class="style-grid">
      <section class="tool-surface">
        <div class="panel-heading-row">
          <h3>白话家书</h3>
        </div>
        <el-input v-model="plainText" type="textarea" :rows="10" />
        <div class="slot-grid editable">
          <el-input v-model="slots.recipient" placeholder="收信人" />
          <el-input v-model="slots.origin_place" placeholder="来源地" />
          <el-input v-model="slots.money" placeholder="汇款" />
          <el-input v-model="slots.purpose" placeholder="用途" />
        </div>
        <el-button type="primary" :loading="loading" @click="runTransfer">
          <el-icon><EditPen /></el-icon>
          转换
        </el-button>
      </section>

      <QiaopiTextPanel
        title="侨批风格文本"
        :text="result.generated_text || ''"
        badge="生成结果"
      />
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <section class="summary-panel">
      <div class="panel-heading-row">
        <h3>抽取槽位</h3>
        <el-tag effect="plain">{{ slotRows.length }}</el-tag>
      </div>
      <div class="slot-grid">
        <div v-for="[key, value] in slotRows" :key="key">
          <span>{{ key }}</span>{{ value }}
        </div>
      </div>
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
import { computed, onMounted, reactive, ref } from 'vue'

import { generateStyleTransfer } from '../api/generation'
import ConsistencyPanel from '../components/ConsistencyPanel.vue'
import EvidenceTable from '../components/EvidenceTable.vue'
import QiaopiTextPanel from '../components/QiaopiTextPanel.vue'
import fallbackResult from '../mock/style_transfer.json'

const plainText = ref('母亲，我在新加坡平安，寄回八元给家里买米和药。请您放心。')
const slots = reactive({
  recipient: '母亲',
  origin_place: '新加坡',
  money: '八元',
  purpose: '米粮和药费'
})
const result = ref(fallbackResult)
const loading = ref(false)
const error = ref('')

const slotLabels = {
  recipient: '收信人',
  origin_place: '来源地',
  money: '汇款',
  purpose: '用途',
  input_preview: '输入预览'
}

const slotRows = computed(() =>
  Object.entries(result.value.slots || {}).map(([key, value]) => [slotLabels[key] || key, value])
)

async function runTransfer() {
  loading.value = true
  error.value = ''
  try {
    result.value = await generateStyleTransfer({
      plain_text: plainText.value,
      slots: { ...slots }
    })
  } catch {
    result.value = fallbackResult
    error.value = '后端不可用，已加载风格转换本地 mock 数据。'
  } finally {
    loading.value = false
  }
}

onMounted(runTransfer)
</script>
