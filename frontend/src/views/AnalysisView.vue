<template>
<<<<<<< Updated upstream
  <section v-loading="loading" class="page-stack">
    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="analysis-grid">
      <WordCloudPanel title="词云" :words="wordCloud" />
      <RelationGraph title="关系图谱" :nodes="relationNodes" :links="relationLinks" />
      <RelationGraph title="小型知识图谱" :nodes="knowledgeNodes" :links="knowledgeLinks" />
      <section class="analysis-panel storytelling">
        <div class="panel-heading-row">
          <h3>文化叙事</h3>
          <el-tag effect="plain">草稿</el-tag>
        </div>
        <p>
          一封从新加坡寄往潮州的侨批，把移民劳作、家庭生计、亲属责任和水客传递连接在一起。
          后续 RAG 层会把这些有证据支撑的记录转化为可解释的叙事摘要。
        </p>
        <div class="story-metrics">
          <StatCard title="来源地类型" :value="stats.origin_places?.length || 0" tone="blue" />
          <StatCard title="亲属关系类型" :value="stats.kinship_distribution?.length || 0" tone="green" />
        </div>
      </section>
=======
  <section v-loading="loading" class="archive-analysis-page">
    <div class="archive-analysis-bg" aria-hidden="true">
      <span class="analysis-seal-watermark">文本洞察</span>
      <span class="analysis-ink analysis-ink-a"></span>
      <span class="analysis-ink analysis-ink-b"></span>
    </div>

    <div class="archive-analysis-shell">
      <nav class="archive-analysis-breadcrumb" aria-label="分析工作台路径">
        <span>侨批 RAG</span>
        <i>›</i>
        <span>文本洞察</span>
        <i>›</i>
        <strong>分析工作台</strong>
      </nav>

      <header class="analysis-hero-card">
        <div class="analysis-hero-marker"></div>
        <div class="analysis-hero-seal" aria-hidden="true">洞察</div>
        <div class="analysis-hero-copy">
          <p class="analysis-kicker">文本洞察 · CONTENT INTELLIGENCE</p>
          <h1>从侨批文本中识别主题、关系与证据结构</h1>
          <p>
            数据看板关注馆藏规模、地点与年代分布；这里进一步分析正文表达，
            比较主题意图、亲属关系、汇款线索、检索单元和证据覆盖，回答“侨批在说什么”。
          </p>
        </div>
        <div class="analysis-hero-tags">
          <span class="analysis-badge analysis-badge-red">Text Insight</span>
          <span class="analysis-code">QP-ANALYSIS-002</span>
        </div>
      </header>

      <div class="analysis-status-note">
        <span></span>
        <p>{{ statusMessage }}</p>
      </div>

      <section class="analysis-signal-grid" aria-label="文本分析摘要">
        <article v-for="signal in contentSignals" :key="signal.label">
          <small>{{ signal.eyebrow }}</small>
          <strong>{{ signal.value }}</strong>
          <span>{{ signal.label }}</span>
          <p>{{ signal.note }}</p>
        </article>
      </section>

      <div class="analysis-visual-grid">
        <article class="analysis-card analysis-word-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-seal" aria-hidden="true">词</div>
          <div class="analysis-card-header">
            <h2>文本关键词云</h2>
            <span class="analysis-badge">Word Cloud</span>
          </div>
          <div class="analysis-word-field">
            <div class="analysis-word-cloud">
              <span
                v-for="word in wordCloud"
                :key="word.label"
                :style="{
                  fontSize: `${word.size}px`,
                  color: word.color,
                  fontWeight: word.weight
                }"
              >
                {{ word.label }}
              </span>
            </div>
          </div>
          <p class="analysis-card-note">
            组合高频亲属称谓、地点、金额和正文主题词；字号表示相对内容权重。
          </p>
        </article>

        <article class="analysis-card analysis-ranking-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-header">
            <h2>主题意图强度</h2>
            <span class="analysis-badge">Intent Profile</span>
          </div>
          <p class="analysis-card-intro">
            比较侨批记录的主要表达目的，识别汇款、问候、照料和事务托付等内容重心。
          </p>
          <div class="analysis-rank-list">
            <div v-for="(item, index) in intentItems" :key="item.label">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <strong>{{ displayLabel(item.label) }}</strong>
              <i><b :style="{ width: `${barPercent(item.value, maxIntentValue)}%` }"></b></i>
              <em>{{ formatNumber(item.value) }}</em>
            </div>
          </div>
          <p class="analysis-card-note">
            当前最突出的文本意图为“{{ displayLabel(intentItems[0]?.label || '暂无') }}”。
          </p>
        </article>

        <article class="analysis-card analysis-ranking-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-header">
            <h2>可检索内容结构</h2>
            <span class="analysis-badge">Retrieval Units</span>
          </div>
          <p class="analysis-card-intro">
            展示正文核心、汇款、家庭关怀、事务指示和摘要等检索单元的组成。
          </p>
          <div class="analysis-rank-list is-green">
            <div v-for="(item, index) in unitTypeItems" :key="item.label">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <strong>{{ unitTypeLabel(item.label) }}</strong>
              <i><b :style="{ width: `${barPercent(item.value, maxUnitValue)}%` }"></b></i>
              <em>{{ formatNumber(item.value) }}</em>
            </div>
          </div>
          <p class="analysis-card-note">
            平均每封全文记录形成 {{ retrievalUnitsPerRecord }} 个可检索内容单元。
          </p>
        </article>
      </div>

      <div class="analysis-narrative-grid">
        <article class="analysis-card analysis-relationship-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-header">
            <h2>亲属关系构成</h2>
            <span class="analysis-badge">Kinship Signals</span>
          </div>
          <div class="analysis-relationship-list">
            <div v-for="item in relationshipItems" :key="item.label">
              <header>
                <strong>{{ displayLabel(item.label) }}</strong>
                <span>{{ formatNumber(item.value) }} 条</span>
              </header>
              <i>
                <b :style="{ width: `${barPercent(item.value, maxRelationshipValue)}%` }"></b>
              </i>
            </div>
          </div>
          <aside class="analysis-focus-note">
            <span>主要关系</span>
            <strong>{{ primaryKinship }}</strong>
            <p>亲属称谓体现侨批作为家庭责任、情感维系与生活安排载体的文本属性。</p>
          </aside>
        </article>

        <article class="analysis-card analysis-evidence-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-header">
            <h2>证据与可解释性</h2>
            <span class="analysis-badge">Evidence Health</span>
          </div>
          <div class="analysis-evidence-summary">
            <div>
              <strong>{{ evidencePerRecord }}</strong>
              <span>平均证据片段 / 封</span>
            </div>
            <div>
              <strong>{{ entityPerRecord }}</strong>
              <span>平均实体提及 / 封</span>
            </div>
            <div>
              <strong>{{ formatNumber(stats.place_mention_count) }}</strong>
              <span>地点提及总数</span>
            </div>
          </div>
          <div class="analysis-evidence-grid">
            <div v-for="item in evidenceItems" :key="item.title" class="analysis-evidence-item">
              <h3>{{ item.title }}</h3>
              <p>{{ item.description }}</p>
            </div>
          </div>
        </article>
      </div>

      <article class="analysis-card analysis-narrative-card">
        <div class="analysis-card-marker"></div>
        <div class="analysis-card-seal analysis-card-seal-lg" aria-hidden="true">档案</div>
        <div class="analysis-card-header">
          <h2>综合内容结论</h2>
          <span class="analysis-badge">Evidence-based Narrative</span>
        </div>
        <div class="analysis-narrative-paper">
          <p>
            当前样本以“{{ primaryIntent }}”为主要表达意图，常见亲属关系为“{{ primaryKinship }}”，
            高频地点包括“{{ primaryOrigin }}”。{{ remittanceCoverage }} 的全文记录包含汇款线索；
            每封记录平均形成 {{ evidencePerRecord }} 条证据片段和 {{ retrievalUnitsPerRecord }} 个检索单元。
            这说明侨批既是跨洋家书，也是承载家庭生计、责任安排和来源追溯的重要档案。
          </p>
        </div>
      </article>

      <footer class="analysis-demo-note analysis-separation-note">
        <div></div>
        <h2>与知识图谱的边界</h2>
        <p>
          本页聚焦文本统计、主题和证据质量；知识图谱独立负责人物、地点、金额与记录之间的关系浏览和来源追溯。
          <router-link to="/knowledge-graph">打开知识图谱工作台 →</router-link>
        </p>
      </footer>
>>>>>>> Stashed changes
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchDashboardStats } from '../api/dashboard'
import RelationGraph from '../components/RelationGraph.vue'
import StatCard from '../components/StatCard.vue'
import WordCloudPanel from '../components/WordCloudPanel.vue'
import fallbackStats from '../mock/dashboard.json'

const stats = ref(fallbackStats)
const loading = ref(false)
const error = ref('')

<<<<<<< Updated upstream
const wordCloud = computed(() => [
  { label: '母亲', size: 34, color: '#2f7d7e' },
  { label: '八元', size: 30, color: '#d96c4a' },
  { label: '新加坡', size: 32, color: '#2f6fb0' },
  { label: '潮州', size: 28, color: '#6f5aa8' },
  { label: '米粮', size: 24, color: '#b77b28' },
  { label: '药费', size: 22, color: '#697386' },
  { label: '水客', size: 20, color: '#3d6d5c' },
  { label: '家用', size: 26, color: '#884a39' }
])

const relationNodes = computed(() => [
  { name: '陈生', symbolSize: 48 },
  { name: '母亲', symbolSize: 44 },
  { name: '新加坡', symbolSize: 42 },
  { name: '广东潮州', symbolSize: 42 },
  { name: '八元', symbolSize: 38 }
])

const relationLinks = computed(() => [
  { source: '陈生', target: '母亲', name: '汇款给' },
  { source: '陈生', target: '新加坡', name: '来源地' },
  { source: '母亲', target: '广东潮州', name: '目的地' },
  { source: '陈生', target: '八元', name: '寄出' }
])

const knowledgeNodes = computed(() => [
  { name: '侨批文本', symbolSize: 54 },
  { name: '亲属责任', symbolSize: 40 },
  { name: '汇款', symbolSize: 40 },
  { name: '迁移路线', symbolSize: 40 },
  { name: '家庭支持', symbolSize: 40 }
])

const knowledgeLinks = computed(() => [
  { source: '侨批文本', target: '亲属责任' },
  { source: '侨批文本', target: '汇款' },
  { source: '侨批文本', target: '迁移路线' },
  { source: '汇款', target: '家庭支持' }
])
=======
const palette = ['#0F4A43', '#A74432', '#6D765F', '#1A6B61', '#8A6A47', '#6F7C78']

const totalTextRecords = computed(() =>
  Number(stats.value.total_text_records ?? stats.value.text_records ?? 0)
)
const originPlaces = computed(() =>
  distributions.value.top_places || stats.value.origin_places || []
)
const destinationPlaces = computed(() => stats.value.destination_places || [])
const relationshipItems = computed(() =>
  distributions.value.relationship_distribution || stats.value.kinship_distribution || []
)
const moneyDistribution = computed(() => stats.value.money_distribution || [])

const intentItems = computed(() => {
  const items = distributions.value.main_intent_distribution || []
  if (items.length) return items.slice(0, 5)
  return [
    { label: 'remittance_and_family_support', value: Number(stats.value.remittance_record_count || 80) },
    { label: 'family_greeting', value: 54 },
    { label: 'family_care', value: 41 },
    { label: 'instruction', value: 36 }
  ]
})

const unitTypeItems = computed(() => {
  const items = distributions.value.unit_type_distribution || []
  if (items.length) return items.slice(0, 5)
  const total = Math.max(totalTextRecords.value, 1)
  return [
    { label: 'body_core', value: total },
    { label: 'rag_summary', value: total },
    { label: 'remittance', value: Math.round(total * 0.38) },
    { label: 'family_care', value: Math.round(total * 0.3) },
    { label: 'instruction', value: Math.round(total * 0.2) }
  ]
})

const primaryOrigin = computed(() => originPlaces.value[0]?.label || '新加坡')
const primaryDestination = computed(() => destinationPlaces.value[0]?.label || '广东潮州')
const primaryKinship = computed(() => displayLabel(relationshipItems.value[0]?.label || '母亲'))
const primaryMoney = computed(() => moneyDistribution.value[0]?.label || '八元')
const primaryIntent = computed(() => displayLabel(intentItems.value[0]?.label || '家庭问候'))

const maxIntentValue = computed(() => maxValue(intentItems.value))
const maxUnitValue = computed(() => maxValue(unitTypeItems.value))
const maxRelationshipValue = computed(() => maxValue(relationshipItems.value))

const remittanceCoverage = computed(() =>
  ratioLabel(stats.value.remittance_record_count, totalTextRecords.value)
)
const evidencePerRecord = computed(() =>
  averageLabel(stats.value.evidence_count, totalTextRecords.value)
)
const entityPerRecord = computed(() =>
  averageLabel(stats.value.entity_mention_count, totalTextRecords.value)
)
const retrievalUnitsPerRecord = computed(() =>
  averageLabel(stats.value.retrieval_unit_count, totalTextRecords.value)
)

const contentSignals = computed(() => [
  {
    eyebrow: 'REMITTANCE',
    value: remittanceCoverage.value,
    label: '汇款线索覆盖率',
    note: '含明确汇款或金额线索的全文记录占比'
  },
  {
    eyebrow: 'EVIDENCE',
    value: evidencePerRecord.value,
    label: '平均证据密度',
    note: '每封记录可回溯的证据片段数量'
  },
  {
    eyebrow: 'ENTITY',
    value: entityPerRecord.value,
    label: '平均实体密度',
    note: '人物、地点、金额等实体提及强度'
  },
  {
    eyebrow: 'RETRIEVAL',
    value: retrievalUnitsPerRecord.value,
    label: '平均检索单元',
    note: '每封记录被拆分出的可检索内容结构'
  }
])

const wordCloud = computed(() => {
  const requiredTerms = [
    { label: primaryKinship.value || '母亲', value: 80 },
    { label: primaryMoney.value || '八元', value: 72 },
    { label: primaryOrigin.value || '新加坡', value: 70 },
    { label: primaryDestination.value || '潮州', value: 64 },
    { label: primaryIntent.value || '汇款', value: 76 },
    { label: '家用', value: 52 },
    { label: '水客', value: 46 },
    { label: '托带', value: 42 },
    { label: '平安', value: 48 },
    { label: '侨批', value: 74 }
  ]

  return requiredTerms.map((word, index) => ({
    ...word,
    size: 13 + Math.round((word.value / 80) * 24),
    color: palette[index % palette.length],
    weight: word.value > 62 ? 600 : 500
  }))
})

const evidenceItems = computed(() => [
  {
    title: '正文证据',
    description: `当前共有 ${formatNumber(stats.value.evidence_count)} 条可追溯片段。`
  },
  {
    title: '结构化实体',
    description: `已识别 ${formatNumber(stats.value.entity_mention_count)} 次人物、地点或金额实体提及。`
  },
  {
    title: '检索结构',
    description: `共形成 ${formatNumber(stats.value.retrieval_unit_count)} 个带来源字段的检索单元。`
  },
  {
    title: '叙事边界',
    description: '综合结论只使用接口返回的统计和证据，不补充样本之外的事实。'
  }
])

const statusMessage = computed(() => {
  if (error.value) return error.value
  return '分析工作台使用正式统计接口计算文本主题、关系强度与证据密度；知识图谱保持为独立关系产品。'
})

const labelMap = {
  remittance_and_family_support: '汇款与家庭支持',
  family_greeting: '家庭问候',
  family_care: '家庭照料',
  instruction: '事务托付',
  unknown: '未分类',
  mother: '母亲',
  father: '父亲',
  parents: '父母',
  wife: '妻子',
  grandmother: '祖母'
}

const unitLabelMap = {
  body_core: '正文核心',
  record_full: '记录全文',
  remittance: '汇款线索',
  family_care: '家庭关怀',
  instruction: '事务指示',
  rag_summary: '检索摘要',
  style_reference: '风格参考',
  unknown: '未分类'
}

function displayLabel(label) {
  return labelMap[label] || String(label || '未分类').replaceAll('_', ' ')
}

function unitTypeLabel(label) {
  return unitLabelMap[label] || displayLabel(label)
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function maxValue(items) {
  return Math.max(...items.map((item) => Number(item.value || 0)), 1)
}

function barPercent(value, max) {
  return Math.max(5, Math.round((Number(value || 0) / Number(max || 1)) * 100))
}

function ratioLabel(value, total) {
  const denominator = Number(total || 0)
  if (!denominator) return '0%'
  return `${Math.round((Number(value || 0) / denominator) * 100)}%`
}

function averageLabel(value, total) {
  const denominator = Number(total || 0)
  if (!denominator) return '0.0'
  return (Number(value || 0) / denominator).toFixed(1)
}
>>>>>>> Stashed changes

async function loadStats() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await fetchDashboardStats()
  } catch {
    stats.value = fallbackStats
    error.value = '后端不可用，已加载分析页本地 mock 数据。'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>
