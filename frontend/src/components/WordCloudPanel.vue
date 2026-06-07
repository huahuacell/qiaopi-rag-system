<template>
  <section class="analysis-panel">
    <div class="panel-heading-row">
      <h3>{{ title }}</h3>
      <el-tag effect="plain">占位</el-tag>
    </div>
    <div class="word-cloud">
      <span
        v-for="word in words"
        :key="word.label"
        :style="{ fontSize: `${word.size}px`, color: word.color }"
      >
        {{ word.label }}
      </span>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: '词云' },
  words: { type: Array, default: () => [] }
})
</script>
