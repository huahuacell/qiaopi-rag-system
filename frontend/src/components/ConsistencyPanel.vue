<template>
  <section class="consistency-panel">
    <div class="panel-heading-row">
      <h3>一致性检查</h3>
      <el-tag :type="tagType">{{ statusLabel }}</el-tag>
    </div>

    <div class="rule-grid">
      <div>
        <div class="rule-heading">通过规则</div>
        <el-tag
          v-for="rule in check.passed_rules"
          :key="rule"
          type="success"
          effect="plain"
        >
          {{ formatRule(rule) }}
        </el-tag>
      </div>
      <div>
        <div class="rule-heading">提醒</div>
        <el-tag
          v-for="warning in check.warnings"
          :key="warning"
          type="warning"
          effect="plain"
        >
          {{ formatRule(warning) }}
        </el-tag>
        <span v-if="!check.warnings?.length" class="muted-text">无</span>
      </div>
      <div>
        <div class="rule-heading">未通过规则</div>
        <el-tag
          v-for="rule in check.failed_rules"
          :key="rule"
          type="danger"
          effect="plain"
        >
          {{ formatRule(rule) }}
        </el-tag>
        <span v-if="!check.failed_rules?.length" class="muted-text">无</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  check: {
    type: Object,
    default: () => ({
      status: 'pending',
      warnings: [],
      passed_rules: [],
      failed_rules: []
    })
  }
})

const tagType = computed(() => {
  if (props.check.status === 'passed') return 'success'
  if (props.check.status === 'failed') return 'danger'
  return 'warning'
})

const statusLabel = computed(() => {
  const labels = {
    passed: '通过',
    failed: '未通过',
    pending: '待检查'
  }
  return labels[props.check.status] || props.check.status
})

function formatRule(rule) {
  const labels = {
    money_supported_by_evidence: '金额有证据支持',
    recipient_supported_by_evidence: '收信人有证据支持',
    purpose_supported_by_evidence: '用途有证据支持',
    money_preserved: '金额保持一致',
    recipient_preserved: '收信人保持一致',
    no_real_api_call: '未调用真实 API',
    placeholder_consistency_check: '占位一致性检查'
  }
  return labels[rule] || String(rule).replaceAll('_', ' ')
}
</script>
