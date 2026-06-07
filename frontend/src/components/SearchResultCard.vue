<template>
  <article class="result-card">
    <div class="result-main">
      <div class="result-title-row">
        <div>
          <router-link class="record-link" :to="`/records/${result.record_id}`">
            {{ result.title }}
          </router-link>
          <div class="record-id">{{ result.record_id }}</div>
        </div>
        <el-tag type="primary">{{ scoreLabel }}</el-tag>
      </div>

      <p class="result-snippet">{{ result.snippet }}</p>

      <div class="metadata-grid compact">
        <div><span>来源地</span>{{ result.origin_place }}</div>
        <div><span>目的地</span>{{ result.destination_place }}</div>
        <div><span>年代</span>{{ result.date }}</div>
        <div><span>亲属关系</span>{{ result.kinship }}</div>
        <div><span>汇款</span>{{ result.money }}</div>
      </div>

      <div class="evidence-strip">
        <el-tag
          v-for="item in result.evidence"
          :key="`${item.source_field}-${item.source_text}`"
          type="info"
          effect="plain"
        >
          {{ fieldLabel(item.source_field) }}：{{ item.reason }}
        </el-tag>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: { type: Object, required: true }
})

const scoreLabel = computed(() => `${Math.round((props.result.score || 0) * 100)}%`)

function fieldLabel(field) {
  const labels = {
    original_text: '原文',
    normalized_text: '规范文本',
    destination_place: '目的地',
    origin_place: '来源地',
    style_pattern: '风格模式'
  }
  return labels[field] || field
}
</script>
