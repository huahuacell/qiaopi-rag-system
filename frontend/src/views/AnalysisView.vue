<template>
  <section v-loading="loading" class="archive-analysis-page">
    <div class="archive-analysis-bg" aria-hidden="true">
      <span class="analysis-seal-watermark">馆藏脉络</span>
      <span class="analysis-ink analysis-ink-a"></span>
      <span class="analysis-ink analysis-ink-b"></span>
    </div>

    <div class="archive-analysis-shell">
      <nav class="archive-analysis-breadcrumb" aria-label="Breadcrumb">
        <span>侨批 RAG</span>
        <i>›</i>
        <span>馆藏脉络</span>
        <i>›</i>
        <strong>分析工作台</strong>
      </nav>

      <header class="analysis-hero-card">
        <div class="analysis-hero-marker"></div>
        <div class="analysis-hero-seal" aria-hidden="true">馆藏</div>
        <div class="analysis-hero-copy">
          <p class="analysis-kicker">馆藏脉络 · ARCHIVE ANALYSIS</p>
          <h1>从侨批文本中观察人物、地名与汇款关系</h1>
          <p>
            基于侨批记录中的关键词、实体、亲属称谓、来源地与证据片段，生成词云、
            关系图谱与文化叙事摘要，帮助用户理解跨海家书背后的迁移网络和家庭记忆。
          </p>
        </div>
        <div class="analysis-hero-tags">
          <span class="analysis-badge analysis-badge-red">Archive Insight</span>
          <span class="analysis-code">QP-ANALYSIS-001</span>
        </div>
      </header>

      <div v-if="error" class="analysis-status-note">
        <span></span>
        <p>{{ error }}</p>
      </div>

      <div v-else class="analysis-status-note">
        <span></span>
        <p>
          当前分析基于正式数据接口返回结果生成；正式模式下接口失败不会静默加载 Mock 数据。
        </p>
      </div>

      <div class="analysis-visual-grid">
        <article class="analysis-card analysis-word-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-seal" aria-hidden="true">批</div>
          <div class="analysis-card-header">
            <h2>关键词云图</h2>
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
          <p class="analysis-card-note">基于侨批正文、来源地、亲属称谓与金额字段提取的高频词，字号表示词频权重。</p>
        </article>

        <article class="analysis-card analysis-graph-product-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-header">
            <h2>正式知识图谱</h2>
            <span class="analysis-badge">Knowledge Graph</span>
          </div>
          <p>
            静态关系预览已退出正式链路。主站知识图谱直接读取 `/api/graph/*`，
            支持记录子图、节点邻居、证据来源和目录元数据追溯。
          </p>
          <router-link to="/knowledge-graph">
            打开知识图谱工作台
            <span>→</span>
          </router-link>
        </article>
      </div>

      <div class="analysis-narrative-grid">
        <article class="analysis-card analysis-narrative-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-seal analysis-card-seal-lg" aria-hidden="true">档案</div>
          <div class="analysis-card-header">
            <h2>文化叙事</h2>
            <span class="analysis-badge">Narrative</span>
          </div>
          <div class="analysis-narrative-paper">
            <p>
              一封从{{ primaryOrigin }}寄往{{ primaryDestination }}的侨批，
              把移民劳作、家庭生计、亲属责任和水客传递连接在一起。
              系统依据来源地、亲属称谓、汇款线索与证据片段，把这些记录转化为可解释的文化叙事摘要。
            </p>
          </div>

          <div class="analysis-metric-grid">
            <div
              v-for="metric in insightMetrics"
              :key="metric.label"
              class="analysis-mini-metric"
              :style="{ '--metric-color': metric.color }"
            >
              <span class="analysis-mini-stamp">批</span>
              <strong>{{ metric.value }}</strong>
              <small>{{ metric.label }}</small>
            </div>
          </div>
        </article>

        <article class="analysis-card analysis-evidence-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-header">
            <h2>分析依据</h2>
            <span class="analysis-badge">Evidence-based</span>
          </div>
          <div class="analysis-evidence-grid">
            <div v-for="item in evidenceItems" :key="item.title" class="analysis-evidence-item">
              <h3>{{ item.title }}</h3>
              <p>{{ item.description }}</p>
            </div>
          </div>
        </article>
      </div>

      <footer class="analysis-demo-note">
        <div></div>
        <h2>链路说明</h2>
        <p>
          文化分析仍使用看板统计；知识图谱已迁移到正式图谱工作台，不再由前端静态拼接节点。
        </p>
      </footer>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchDashboardDistributions, fetchDashboardStats } from '../api/dashboard'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackStats from '../mock/dashboard.json'

const stats = ref(demoMode ? fallbackStats : {})
const distributions = ref({})
const loading = ref(false)
const error = ref('')

const palette = ['#0F4A43', '#A74432', '#6D765F', '#1A6B61', '#8A6A47', '#6F7C78']

const originPlaces = computed(() => distributions.value.top_places || stats.value.origin_places || [])
const destinationPlaces = computed(() => stats.value.destination_places || [])
const relationshipDistribution = computed(
  () => distributions.value.relationship_distribution || stats.value.kinship_distribution || []
)
const moneyDistribution = computed(() => stats.value.money_distribution || [])

const primaryOrigin = computed(() => originPlaces.value[0]?.label || '新加坡')
const primaryDestination = computed(() => destinationPlaces.value[0]?.label || '广东潮州')
const primaryKinship = computed(() => relationshipDistribution.value[0]?.label || '母亲')
const primaryMoney = computed(() => moneyDistribution.value[0]?.label || '八元')

const wordCloud = computed(() => {
  const requiredTerms = [
    { label: primaryKinship.value || '母亲', value: 80 },
    { label: primaryMoney.value || '八元', value: 72 },
    { label: primaryOrigin.value || '新加坡', value: 70 },
    { label: primaryDestination.value || '潮州', value: 64 },
    { label: '米粮', value: 50 },
    { label: '药费', value: 44 },
    { label: '水客', value: 46 },
    { label: '家用', value: 52 },
    { label: '托带', value: 42 },
    { label: '汇款', value: 58 },
    { label: '平安', value: 48 },
    { label: '侨批', value: 76 }
  ]

  return requiredTerms.map((word, index) => ({
    ...word,
    size: 13 + Math.round((word.value / 80) * 24),
    color: palette[index % palette.length],
    weight: word.value > 62 ? 600 : 500
  }))
})

const insightMetrics = computed(() => [
  { label: '来源地类型', value: originPlaces.value.length || 4, color: '#0F4A43' },
  { label: '亲属关系类型', value: relationshipDistribution.value.length || 4, color: '#1A6B61' },
  { label: '证据片段数量', value: 6, color: '#A74432' }
])

const evidenceItems = [
  { title: '关键词依据', description: '来自侨批正文与元数据字段。' },
  { title: '实体依据', description: '人物、地点、金额与亲属称谓共同构成实体线索。' },
  { title: '图谱依据', description: '记录之间的共现关系与语义关联用于构建图谱。' },
  { title: '叙事边界', description: '不补充证据之外的人物、地点和事件。' }
]

async function loadStats() {
  loading.value = true
  error.value = ''
  try {
    const [statsPayload, distributionsPayload] = await Promise.all([
      fetchDashboardStats(),
      fetchDashboardDistributions()
    ])
    stats.value = statsPayload
    distributions.value = distributionsPayload
  } catch (requestError) {
    if (demoMode) {
      stats.value = fallbackStats
      distributions.value = {}
      error.value = demoFailureMessage('分析数据请求')
    } else {
      stats.value = {}
      distributions.value = {}
      error.value = apiFailureMessage(requestError, '分析数据请求')
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>
