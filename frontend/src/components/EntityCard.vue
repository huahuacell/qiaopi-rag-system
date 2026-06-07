<template>
  <article class="entity-card">
    <div class="entity-type">{{ entityTypeLabel }}</div>
    <div class="entity-value">{{ entity.value }}</div>
    <div class="entity-source">{{ entity.source_text }}</div>
    <el-progress
      :percentage="percentage"
      :stroke-width="6"
      :show-text="false"
      status="success"
    />
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  entity: { type: Object, required: true }
})

const typeLabels = {
  person: '人物',
  place: '地点',
  kinship: '亲属关系',
  money: '金额',
  time: '时间'
}

const entityTypeLabel = computed(() => typeLabels[props.entity.entity_type] || props.entity.entity_type)
const percentage = computed(() => Math.round((props.entity.confidence || 0) * 100))
</script>
