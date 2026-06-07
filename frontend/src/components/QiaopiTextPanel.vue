<template>
  <section class="text-panel">
    <div class="panel-heading-row">
      <h3>{{ title }}</h3>
      <el-tag v-if="badge" effect="plain">{{ badge }}</el-tag>
    </div>
    <p>{{ text }}</p>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  text: { type: String, required: true },
  badge: { type: String, default: '' }
})
</script>

