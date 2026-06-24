<template>
  <article class="archive-result-card">
    <div class="archive-result-marker" aria-hidden="true"></div>
    <div class="archive-result-rank" aria-hidden="true">{{ rank }}</div>

    <div class="archive-result-main">
      <header class="archive-result-head">
        <div class="archive-result-title-block">
          <div class="archive-result-id-row">
            <span>{{ result.record_id }}</span>
            <i></i>
            <em>{{ result.main_intent || result.unit_type || '侨批文本' }}</em>
          </div>

          <router-link class="archive-result-title" :to="`/records/${result.record_id}`">
            {{ result.title || result.title_reference || result.record_id }}
          </router-link>

          <div class="archive-result-tags">
            <span>来源地：{{ result.origin_place || '-' }}</span>
            <span>收信人：{{ result.recipient || result.kinship || '-' }}</span>
            <span>年代：{{ result.date || result.date_text || '-' }}</span>
          </div>
        </div>

        <div class="archive-score-badge">
          <strong>#{{ rank }}</strong>
          <span>RANK</span>
        </div>
      </header>

      <div class="archive-result-divider"></div>

      <section class="archive-result-reason">
        <h3>匹配原因</h3>
        <p>{{ matchReason }}</p>
      </section>

      <section v-if="graphPaths.length" class="archive-graph-paths">
        <h3>图谱关联路径</h3>
        <div>
          <span v-for="path in graphPaths" :key="`${path.seed_node_id}-${path.edge_type}`">
            {{ path.path_text }}
          </span>
        </div>
      </section>

      <section class="archive-score-contributions">
        <h3>排序贡献</h3>
        <div v-if="scoreContributions.length" class="score-contribution-list">
          <article v-for="item in scoreContributions" :key="item.key">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.meaning }}</p>
          </article>
        </div>
        <p v-else class="score-contribution-empty">该结果未返回可解释的排序分量。</p>
      </section>

      <section class="archive-result-evidence">
        <h3>证据片段</h3>
        <div>
          <el-icon><Document /></el-icon>
          <p>{{ evidenceText }}</p>
        </div>
      </section>

      <footer class="archive-result-footer">
        <div class="archive-evidence-strip">
          <span
            v-for="item in evidenceItems"
            :key="`${item.source_field}-${item.source_text}-${item.reason}`"
          >
            {{ fieldLabel(item.source_field) }}：{{ item.reason }}
          </span>
        </div>

        <router-link class="archive-detail-link" :to="`/records/${result.record_id}`">
          查看详情
          <span>›</span>
        </router-link>
      </footer>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { buildScoreContributions } from '../utils/searchPresentation'

const props = defineProps({
  result: { type: Object, required: true },
  rank: { type: Number, default: 1 },
  execution: { type: Object, default: () => ({}) }
})

const scoreContributions = computed(() =>
  buildScoreContributions(props.result, props.execution)
)
const graphPaths = computed(() => (props.result.graph_paths || []).slice(0, 3))

const evidenceItems = computed(() => {
  if (props.result.evidence?.length) return props.result.evidence
  if (props.result.matched_reason || props.result.source_column || props.result.source_field) {
    return [
      {
        source_field: props.result.source_column || props.result.source_field,
        source_text: props.result.matched_text || props.result.unit_text || props.result.snippet || '',
        reason: props.result.matched_reason || '后端检索命中'
      }
    ]
  }
  return [
    {
      source_field: props.result.source_column || 'retrieval_unit',
      source_text: props.result.snippet || props.result.unit_text || '',
      reason: props.result.matched_reason || '后端检索命中'
    }
  ]
})

const matchReason = computed(() => {
  const first = evidenceItems.value[0]
  if (props.result.matched_reason) return props.result.matched_reason
  if (first?.reason) return first.reason
  return '后端返回该检索单元，但未提供更具体的匹配说明。'
})

const evidenceText = computed(() => {
  const first = evidenceItems.value[0]
  return first?.source_text || props.result.snippet || props.result.unit_text || '暂无证据片段'
})

function fieldLabel(field) {
  const labels = {
    original_text: '原文',
    normalized_text: '规范文本',
    destination_place: '目的地',
    origin_place: '来源地',
    style_pattern: '风格模式',
    body_clean: '清洗正文',
    body_core: '核心正文',
    rag_summary_text: 'RAG 摘要',
    style_reference_text: '风格样本',
    evidence_remittance: '汇款证据',
    evidence_opening: '开头证据'
  }
  return labels[field] || field || '证据'
}
</script>
