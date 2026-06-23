<template>
  <article class="archive-result-card">
    <div class="archive-result-marker" aria-hidden="true"></div>
    <div class="archive-result-rank" aria-hidden="true">{{ rank }}</div>

    <div class="archive-result-main">
      <header class="archive-result-head">
        <div class="archive-result-title-block">
          <div class="archive-result-id-row">
            <span>{{ result.metadata_id }}</span>
            <i></i>
            <em>目录元数据</em>
          </div>

          <strong class="archive-result-title">
            {{ result.title_clean || result.metadata_id }}
          </strong>

          <div class="archive-result-tags">
            <span>寄批人：{{ result.sender_raw || '-' }}</span>
            <span>收批人：{{ result.recipient_raw || '-' }}</span>
            <span>年代：{{ result.date_text || result.year_normalized || '-' }}</span>
          </div>
        </div>

        <div class="archive-score-badge">
          <strong>#{{ rank }}</strong>
          <span>CATALOG</span>
        </div>
      </header>

      <div class="archive-result-divider"></div>

      <section class="archive-result-reason">
        <h3>匹配原因</h3>
        <p>{{ result.matched_reason || '目录元数据检索命中' }}</p>
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
      </section>

      <section class="archive-result-evidence">
        <h3>目录摘要</h3>
        <div>
          <el-icon><Document /></el-icon>
          <p>
            {{ result.snippet || result.title_clean || '暂无目录摘要' }}
          </p>
        </div>
      </section>

      <footer class="archive-result-footer">
        <div class="archive-evidence-strip">
          <span>来源：{{ result.origin_place || result.country_or_region || '-' }}</span>
          <span>去向：{{ result.destination_place || '-' }}</span>
          <span v-if="result.remittance_raw">汇款：{{ result.remittance_raw }}</span>
        </div>

        <router-link
          v-if="result.linked_record_id"
          class="archive-detail-link"
          :to="`/records/${result.linked_record_id}`"
        >
          查看关联全文
          <span>›</span>
        </router-link>
        <span v-else class="metadata-unlinked-label">仅目录记录</span>
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
</script>
