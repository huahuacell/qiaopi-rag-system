<template>
  <section class="stat-card" :class="`tone-${tone}`">
    <div class="stat-label">{{ title }}</div>
    <div class="stat-value">{{ formattedValue }}</div>
    <div v-if="caption" class="stat-caption">{{ caption }}</div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  caption: { type: String, default: '' },
  tone: { type: String, default: 'blue' }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})
</script>

