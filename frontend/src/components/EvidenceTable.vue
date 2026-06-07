<template>
  <el-table :data="rows" class="evidence-table" size="small" border>
    <el-table-column
      v-if="hasTargetSpan"
      prop="target_span"
      label="生成片段"
      min-width="160"
    />
    <el-table-column label="来源字段" width="150">
      <template #default="{ row }">
        {{ fieldLabel(row.source_field) }}
      </template>
    </el-table-column>
    <el-table-column prop="source_text" label="原文证据" min-width="220" />
    <el-table-column prop="reason" label="依据说明" min-width="220" />
    <el-table-column label="分数" width="110">
      <template #default="{ row }">
        {{ Math.round((row.similarity_score || 0) * 100) }}%
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  rows: { type: Array, default: () => [] }
})

const hasTargetSpan = computed(() => props.rows.some((row) => row.target_span))

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
