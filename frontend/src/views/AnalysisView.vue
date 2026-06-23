<template>
  <section
    v-loading="loading"
    class="archive-analysis-page"
    :class="{ 'is-analysis-entered': analysisEntered }"
  >
    <div class="archive-analysis-bg" aria-hidden="true">
      <span class="analysis-seal-watermark">情感分类</span>
      <span class="analysis-ink analysis-ink-a"></span>
      <span class="analysis-ink analysis-ink-b"></span>
    </div>

    <div class="archive-analysis-shell">
      <nav class="archive-analysis-breadcrumb" aria-label="情感分类路径">
        <span>侨批 RAG</span>
        <i>›</i>
        <span>文本理解</span>
        <i>›</i>
        <strong>情感分类</strong>
      </nav>

      <header class="analysis-hero-card">
        <div class="analysis-hero-marker"></div>
        <div class="analysis-hero-seal" aria-hidden="true">分类</div>
        <div class="analysis-hero-copy">
          <p class="analysis-kicker">侨批正文 · 多标签情感分类</p>
          <h1>识别一封侨批中并存的情感表达</h1>
          <p>
            本页只呈现与情感分类直接相关的结果：情感标签、极性构成、共现组合、年代侧写和可追溯原文。
            一封信可同时包含平安、感激、牵挂、压力或嘱托，因此分类结果不强制互斥。
          </p>
        </div>
        <div class="analysis-hero-tags">
          <span class="analysis-badge analysis-badge-red">多标签分类</span>
        </div>
      </header>

      <section class="analysis-emotion-section" aria-labelledby="emotion-analysis-title">
        <div class="analysis-section-heading">
          <div>
            <p>句段判断 · 信件聚合 · 原文可追溯</p>
            <h2 id="emotion-analysis-title">侨批情感分类结果</h2>
            <span>
              以句段为最小判断单元，再聚合到信件层级；每项典型结果保留数据库原文证据。
            </span>
          </div>
        </div>

        <section class="analysis-emotion-signal-grid" aria-label="情感分类摘要">
          <article v-for="signal in emotionSignals" :key="signal.label">
            <small>{{ signal.eyebrow }}</small>
            <strong>{{ signal.value }}</strong>
            <span>{{ signal.label }}</span>
            <p>{{ signal.note }}</p>
          </article>
        </section>

        <div class="analysis-emotion-grid">
          <article class="analysis-card analysis-emotion-distribution-card">
            <div class="analysis-card-marker"></div>
            <div class="analysis-card-header">
              <h2>多标签情感分布</h2>
              <span class="analysis-badge">点击下方分类查看原文</span>
            </div>
            <p class="analysis-card-intro">
              占比按各情感标签的信件覆盖量归一化计算，全部标签合计为 100%。
              条形长度以当前最高项为满格，用于比较相对强弱，不代表 100%。
            </p>
            <div class="analysis-emotion-rank-list is-interactive">
              <button
                v-for="(item, index) in emotionItems"
                :key="item.key"
                type="button"
                :class="{ 'is-selected': selectionType === 'emotion' && selectedEmotionKey === item.key }"
                :aria-pressed="selectionType === 'emotion' && selectedEmotionKey === item.key"
                @click="selectEmotionEvidence(item)"
              >
                <span class="analysis-emotion-index">{{ String(index + 1).padStart(2, '0') }}</span>
                <span class="analysis-emotion-rank-content">
                  <span class="analysis-emotion-rank-header">
                    <strong>{{ item.label }}</strong>
                    <em>{{ formatNumber(item.record_count) }} 封 · {{ item.display_percent }}%</em>
                  </span>
                  <i>
                    <b
                      :class="`is-${item.valence}`"
                      :style="{
                        '--emotion-width': `${Math.max(3, item.relative_ratio * 100)}%`,
                        '--emotion-delay': `${index * 80}ms`
                      }"
                    ></b>
                  </i>
                  <small>
                    {{ formatNumber(item.segment_count) }} 个句段 · 平均置信度
                    {{ formatPercent(item.average_confidence, 1) }}
                  </small>
                </span>
              </button>
            </div>
          </article>

          <div class="analysis-emotion-side-stack">
            <article class="analysis-card analysis-valence-card">
              <div class="analysis-card-marker"></div>
              <div class="analysis-card-header">
                <h2>情感极性与复合度</h2>
                <span class="analysis-badge">极性构成</span>
              </div>
              <div class="analysis-valence-layout">
                <div class="analysis-valence-ring" :style="valenceRingStyle">
                  <div>
                    <strong>{{ formatNumber(emotionAnalysis.analyzed_records) }}</strong>
                    <span>全文信件</span>
                  </div>
                </div>
                <div class="analysis-valence-legend">
                  <button
                    v-for="item in valenceItems"
                    :key="item.key"
                    type="button"
                    :class="{ 'is-selected': selectionType === 'valence' && selectedValenceKey === item.key }"
                    :aria-pressed="selectionType === 'valence' && selectedValenceKey === item.key"
                    @click="selectValenceEvidence(item)"
                  >
                    <i :style="{ background: valenceColor(item.key) }"></i>
                    <span>{{ valenceLabel(item.key, item.label) }}</span>
                    <strong>{{ formatPercent(item.ratio) }}</strong>
                    <small>{{ formatNumber(item.record_count) }} 封</small>
                  </button>
                </div>
              </div>
            </article>

            <article class="analysis-card analysis-cooccurrence-card">
              <div class="analysis-card-marker"></div>
              <div class="analysis-card-header">
                <h2>情感共现关系</h2>
                <span class="analysis-badge">共现组合</span>
              </div>
              <p class="analysis-card-intro">
                同一封信中共同出现的情感组合，用于观察“事务—问安—牵挂”等表达结构。
              </p>
              <div class="analysis-cooccurrence-list">
                <button
                  v-for="item in cooccurrenceItems"
                  :key="`${item.left_key}-${item.right_key}`"
                  type="button"
                  :class="{
                    'is-selected':
                      selectionType === 'cooccurrence' &&
                      selectedCooccurrenceKey === `${item.left_key}-${item.right_key}`
                  }"
                  @click="selectCooccurrenceEvidence(item)"
                >
                  <span>{{ item.left_label }}</span>
                  <i aria-hidden="true">＋</i>
                  <span>{{ item.right_label }}</span>
                  <b>{{ formatNumber(item.record_count) }} 封</b>
                </button>
                <p v-if="!cooccurrenceItems.length">暂无达到展示条件的共现组合。</p>
              </div>
            </article>
          </div>
        </div>

        <div class="analysis-emotion-detail-grid">
          <article ref="evidenceSectionRef" class="analysis-card analysis-emotion-evidence-card">
            <div class="analysis-card-marker"></div>
            <div class="analysis-card-header">
              <h2>典型原文例证</h2>
              <span class="analysis-badge">
                {{ evidenceSelectionLabel }}
              </span>
            </div>
            <div
              v-if="selectedEvidenceExamples.length"
              class="analysis-emotion-evidence-list is-selected-only"
              aria-live="polite"
            >
              <article
                v-for="item in selectedEvidenceExamples"
                :key="`${item.record_id}-${item.emotion_key}-${item.text}`"
              >
                <header>
                  <strong>{{ item.emotion_label }}</strong>
                  <span>{{ item.record_id }}<template v-if="item.year"> · {{ item.year }}</template></span>
                </header>
                <blockquote>{{ item.text }}</blockquote>
                <footer>
                  <span>
                    触发：
                    {{ item.trigger_terms?.length ? item.trigger_terms.join('、') : '上下文特征' }}
                  </span>
                  <em v-if="item.confidence != null">{{ formatPercent(item.confidence, 1) }}</em>
                </footer>
              </article>
            </div>
            <div v-else class="analysis-evidence-awaiting" aria-live="polite">
              <strong>{{ selectionType ? '当前选择暂无可展示原文' : '请选择一个分析项目' }}</strong>
              <p>{{ selectionType ? '当前数据中没有更多可追溯片段。' : '可点击情感分布、极性、共现组合或正文关键词。' }}</p>
            </div>
          </article>
        </div>
      </section>

      <article v-loading="keywordLoading" class="analysis-card analysis-emotion-word-card">
        <div class="analysis-card-marker"></div>
        <div class="analysis-card-seal" aria-hidden="true">词</div>
        <div class="analysis-card-header">
          <h2>全库侨批正文关键词云</h2>
          <span class="analysis-badge">{{ formatNumber(corpusRecords.length) }} 封全文</span>
        </div>
        <p class="analysis-card-intro">
          覆盖数据库中全部可用侨批正文，不局限于情感词。候选词必须真实出现在正文中，
          英文技术标签和只存在于元数据中的地点、关系或金额不会参与计算。
        </p>
        <div class="analysis-word-field is-emotion-cloud">
          <div class="analysis-envelope-art" aria-hidden="true">
            <img class="analysis-envelope-postmark-image" :src="postmarkImage" alt="" />
            <svg viewBox="0 0 1000 620" preserveAspectRatio="none">
              <path class="analysis-envelope-flap" d="M55 55 L500 355 L945 55" />
              <path class="analysis-envelope-fold" d="M55 565 L355 332" />
              <path class="analysis-envelope-fold" d="M945 565 L645 332" />
              <path class="analysis-envelope-route" d="M88 505 C220 420 280 535 410 450 S650 365 760 445 S890 475 930 390" />
            </svg>
          </div>
          <div
            v-if="wordCloudLayout.length"
            class="analysis-word-cloud"
            :class="{ 'is-word-cloud-entered': wordCloudEntered }"
          >
            <button
              v-for="(word, index) in wordCloudLayout"
              :key="word.label"
              type="button"
              class="analysis-word-token"
              :class="{ 'is-selected': selectionType === 'keyword' && selectedKeyword === word.label }"
              :style="{
                '--word-size': `${word.size}px`,
                '--word-color': word.color,
                '--word-weight': word.weight,
                '--word-left': `${word.left}%`,
                '--word-top': `${word.top}%`,
                '--word-rotate': `${word.rotation}deg`,
                '--word-delay': `${index * 18}ms`
              }"
              :aria-label="wordTooltip(word)"
              :title="wordTooltip(word)"
              @click="selectKeywordEvidence(word.label)"
            >
              <span>{{ word.label }}</span>
              <small class="analysis-word-tooltip" role="tooltip">{{ wordTooltip(word) }}</small>
            </button>
          </div>
          <p v-else class="analysis-empty-copy">
            {{ keywordLoading ? '正在汇总全部侨批正文关键词…' : '暂无可用于生成词云的正文关键词。' }}
          </p>
        </div>
        <div class="analysis-cloud-method">
          <strong>权重如何计算</strong>
          <p>
            每个词的确定性权重为“全库正文出现总次数 ×（1 + ln（1 + 出现记录数））”；
            既保留高频词，也提高跨多封侨批反复出现词语的权重。分数越高，字号越大。
          </p>
          <span>
            当前读取 {{ formatNumber(corpusRecords.length) }} 封可用全文，
            展示 {{ formatNumber(corpusKeywordCloud.length) }} 个正文关键词。
          </span>
        </div>
      </article>

      <section
        class="analysis-qiaopi-feature-grid"
        :class="{ 'has-national-board': nationalThemeRecords.length }"
        aria-label="银信合一与家国相连专题"
      >
        <article class="analysis-card analysis-remittance-distribution-card">
          <div class="analysis-card-marker"></div>
          <div class="analysis-card-seal" aria-hidden="true">银</div>
          <div class="analysis-card-header">
            <h2>银信合一 · 汇款数额分布</h2>
            <span class="analysis-badge">
              {{ formatNumber(remittanceSummary.amountRecordCount) }} 封有明确金额
            </span>
          </div>
          <p class="analysis-card-intro">
            每封侨批仅取结构化主汇款金额，按原文名义数额分组；不同历史币种不作汇率或购买力换算。
          </p>

          <div v-if="remittanceSummary.amountRecordCount" class="analysis-remittance-layout">
            <div
              class="analysis-remittance-overview"
              :style="{
                '--amount-coverage': `${remittanceSummary.coverageRatio * 100}%`
              }"
            >
              <small>金额覆盖率</small>
              <strong>{{ formatPercent(remittanceSummary.coverageRatio, 1) }}</strong>
              <span>
                {{ formatNumber(remittanceSummary.amountRecordCount) }} /
                {{ formatNumber(remittanceSummary.totalRecords) }} 封
              </span>
            </div>

            <div class="analysis-remittance-bars">
              <div v-for="item in remittanceSummary.buckets" :key="item.key">
                <header>
                  <strong>{{ item.label }}</strong>
                  <span>{{ formatNumber(item.count) }} 封 · {{ formatPercent(item.ratio, 1) }}</span>
                </header>
                <i>
                  <b :style="{ '--remittance-width': `${item.relativeRatio * 100}%` }"></b>
                </i>
              </div>
            </div>
          </div>
          <p v-else class="analysis-empty-copy">暂无可用于统计的结构化汇款金额。</p>

          <div v-if="remittanceSummary.currencies.length" class="analysis-currency-strip">
            <strong>原文币种</strong>
            <span
              v-for="item in remittanceSummary.currencies.slice(0, 6)"
              :key="item.label"
            >
              {{ item.label }} {{ item.count }}
            </span>
          </div>
        </article>

        <article
          v-if="nationalThemeRecords.length"
          class="analysis-card analysis-national-theme-card"
        >
          <div class="analysis-card-marker"></div>
          <div class="analysis-national-seal" aria-hidden="true">家国</div>
          <div class="analysis-card-header">
            <h2>家国相连 · 国家主题侨批</h2>
            <span class="analysis-badge analysis-badge-red">
              {{ formatNumber(nationalThemeRecords.length) }} 封正文命中
            </span>
          </div>
          <p class="analysis-card-intro">
            仅展示正文明确出现乡国归思、国难民生或侨汇政策表达的侨批，点击可查看完整记录。
          </p>

          <div class="analysis-national-records">
            <RouterLink
              v-for="item in nationalThemeRecords"
              :key="item.recordId"
              :to="`/records/${item.recordId}`"
            >
              <header>
                <span>{{ item.year || '年代未详' }}</span>
                <strong>{{ item.themeLabel }}</strong>
                <em>{{ item.matchedTerms.join('、') }}</em>
              </header>
              <blockquote>{{ item.snippet }}</blockquote>
              <footer>
                <span>{{ item.recordId }}</span>
                <b>查看原批 ›</b>
              </footer>
            </RouterLink>
          </div>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

import { fetchEmotionAnalysis } from '../api/analysis'
import { fetchRecordCorpus } from '../api/records'
import postmarkImage from '../assets/nav/2.png'
import { demoMode } from '../config/runtime'
import fallbackEmotionAnalysis from '../mock/emotion_analysis.json'
import {
  buildRemittanceAmountSummary,
  buildCorpusKeywordCloud,
  layoutCorpusKeywordCloud,
  normalizeEmotionDistribution,
  selectCooccurrenceEvidenceExamples,
  selectEmotionEvidenceExamples,
  selectKeywordEvidenceExamples,
  selectNationalThemeRecords,
  selectValenceEvidenceExamples
} from '../utils/emotionClassification'
import {
  emptyEmotionAnalysis,
  normalizeEmotionAnalysis,
  percentText
} from '../utils/emotionPresentation'

const emotionAnalysis = ref(
  normalizeEmotionAnalysis(demoMode ? fallbackEmotionAnalysis : emptyEmotionAnalysis)
)
const selectedEmotionKey = ref('')
const selectedValenceKey = ref('')
const selectedCooccurrence = ref(null)
const selectedKeyword = ref('')
const selectionType = ref('')
const loading = ref(false)
const allRecords = ref([])
const corpusRecords = ref([])
const keywordLoading = ref(false)
const analysisEntered = ref(false)
const wordCloudEntered = ref(false)
const evidenceSectionRef = ref(null)

const valencePalette = {
  positive: '#2F6F63',
  neutral: '#9A8D76',
  negative: '#A74432',
  mixed: '#C2884B'
}

const valenceLabels = {
  positive: '积极安慰',
  neutral: '中性事务',
  negative: '忧虑哀伤',
  mixed: '复合情感'
}

const emotionItems = computed(() =>
  normalizeEmotionDistribution(emotionAnalysis.value.label_distribution)
)
const valenceItems = computed(() => emotionAnalysis.value.valence_distribution || [])
const cooccurrenceItems = computed(() => (emotionAnalysis.value.cooccurrence || []).slice(0, 8))
const allEvidenceExamples = computed(() => emotionAnalysis.value.evidence_examples || [])
const selectedEmotion = computed(() =>
  emotionItems.value.find((item) => item.key === selectedEmotionKey.value) || null
)
const selectedCooccurrenceKey = computed(() =>
  selectedCooccurrence.value
    ? `${selectedCooccurrence.value.left_key}-${selectedCooccurrence.value.right_key}`
    : ''
)
const selectedEvidenceExamples = computed(() => {
  if (selectionType.value === 'emotion') {
    return selectEmotionEvidenceExamples(
      allEvidenceExamples.value,
      selectedEmotionKey.value,
      9
    )
  }
  if (selectionType.value === 'valence') {
    return selectValenceEvidenceExamples(
      allEvidenceExamples.value,
      selectedValenceKey.value,
      9
    )
  }
  if (selectionType.value === 'cooccurrence' && selectedCooccurrence.value) {
    return selectCooccurrenceEvidenceExamples(
      allEvidenceExamples.value,
      selectedCooccurrence.value.left_key,
      selectedCooccurrence.value.right_key,
      9
    )
  }
  if (selectionType.value === 'keyword') {
    return selectKeywordEvidenceExamples(corpusRecords.value, selectedKeyword.value, 9)
  }
  return []
})
const evidenceSelectionLabel = computed(() => {
  if (selectionType.value === 'emotion' && selectedEmotion.value) {
    return `${selectedEmotion.value.label} · ${selectedEvidenceExamples.value.length} 例`
  }
  if (selectionType.value === 'valence') {
    return `${valenceLabel(selectedValenceKey.value)} · ${selectedEvidenceExamples.value.length} 例`
  }
  if (selectionType.value === 'cooccurrence' && selectedCooccurrence.value) {
    return `${selectedCooccurrence.value.left_label} × ${selectedCooccurrence.value.right_label} · ${selectedEvidenceExamples.value.length} 例`
  }
  if (selectionType.value === 'keyword') {
    return `关键词“${selectedKeyword.value}” · ${selectedEvidenceExamples.value.length} 例`
  }
  return '等待选择'
})
const corpusKeywordCloud = computed(() =>
  buildCorpusKeywordCloud(corpusRecords.value)
)
const wordCloudLayout = computed(() =>
  layoutCorpusKeywordCloud(corpusKeywordCloud.value)
)
const remittanceSummary = computed(() =>
  buildRemittanceAmountSummary(allRecords.value)
)
const nationalThemeRecords = computed(() =>
  selectNationalThemeRecords(allRecords.value, 4)
)

const emotionSignals = computed(() => [
  {
    eyebrow: '主要分类',
    value: emotionAnalysis.value.dominant_emotion_label || '暂无',
    label: '主要情感表达',
    note: '排除纯事务背景后，全文馆藏中覆盖最多的情感类型'
  },
  {
    eyebrow: '多标签',
    value: ratioLabel(
      emotionAnalysis.value.multi_label_records,
      emotionAnalysis.value.analyzed_records
    ),
    label: '多情感共存',
    note: `${formatNumber(emotionAnalysis.value.multi_label_records)} 封信同时包含两类及以上表达`
  },
  {
    eyebrow: '复合极性',
    value: ratioLabel(
      emotionAnalysis.value.mixed_valence_records,
      emotionAnalysis.value.analyzed_records
    ),
    label: '复合情感信件',
    note: '积极安慰与忧虑、牵挂等表达在同一封信中共存'
  },
  {
    eyebrow: '原文句段',
    value: formatNumber(emotionAnalysis.value.analyzed_segments),
    label: '已分析句段',
    note: `${formatNumber(emotionAnalysis.value.analyzed_records)} / ${formatNumber(emotionAnalysis.value.total_records)} 条记录具有可用全文`
  }
])

const valenceRingStyle = computed(() => {
  let cursor = 0
  const segments = valenceItems.value.map((item) => {
    const start = cursor
    cursor += Number(item.ratio || 0) * 100
    return `${valenceColor(item.key)} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`
  })
  if (!segments.length || cursor <= 0) {
    return { background: 'conic-gradient(#ddd6c8 0 100%)' }
  }
  if (cursor < 100) {
    segments.push(`#ebe4d8 ${cursor.toFixed(2)}% 100%`)
  }
  return { background: `conic-gradient(${segments.join(', ')})` }
})

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatPercent(value, digits = 0) {
  return percentText(value, digits)
}

function ratioLabel(value, total) {
  const denominator = Number(total || 0)
  if (!denominator) return '0%'
  return `${Math.round((Number(value || 0) / denominator) * 100)}%`
}

function valenceColor(key) {
  return valencePalette[key] || '#9A8D76'
}

function valenceLabel(key, fallback) {
  return valenceLabels[key] || fallback || '未分类'
}

function wordTooltip(word) {
  return `确定性权重 ${word.score.toFixed(4)}；全库正文出现 ${word.termFrequency} 次；覆盖 ${word.recordCount} 封侨批`
}

function resetSelection(type) {
  selectionType.value = type
  if (type !== 'emotion') selectedEmotionKey.value = ''
  if (type !== 'valence') selectedValenceKey.value = ''
  if (type !== 'cooccurrence') selectedCooccurrence.value = null
  if (type !== 'keyword') selectedKeyword.value = ''
}

async function scrollToEvidence() {
  await nextTick()
  evidenceSectionRef.value?.scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  })
}

function selectEmotionEvidence(item) {
  resetSelection('emotion')
  selectedEmotionKey.value = item.key
  scrollToEvidence()
}

function selectValenceEvidence(item) {
  resetSelection('valence')
  selectedValenceKey.value = item.key
  scrollToEvidence()
}

function selectCooccurrenceEvidence(item) {
  resetSelection('cooccurrence')
  selectedCooccurrence.value = item
  scrollToEvidence()
}

function selectKeywordEvidence(keyword) {
  resetSelection('keyword')
  selectedKeyword.value = keyword
  scrollToEvidence()
}

async function loadEmotionAnalysis() {
  loading.value = true
  analysisEntered.value = false

  try {
    emotionAnalysis.value = normalizeEmotionAnalysis(await fetchEmotionAnalysis())
  } catch {
    if (demoMode) {
      emotionAnalysis.value = normalizeEmotionAnalysis(fallbackEmotionAnalysis)
    } else {
      emotionAnalysis.value = normalizeEmotionAnalysis(emptyEmotionAnalysis)
    }
  } finally {
    loading.value = false
    await nextTick()
    requestAnimationFrame(() => {
      analysisEntered.value = true
    })
  }
}

function fallbackCorpusFromEvidence() {
  return allEvidenceExamples.value.map((item, index) => ({
    record_id: item.record_id || `DEMO-${index + 1}`,
    has_full_text: 1,
    body_core: item.text,
    retrieval_keywords: (item.trigger_terms || []).join('；')
  }))
}

async function loadCorpusKeywords() {
  keywordLoading.value = true
  wordCloudEntered.value = false

  try {
    const records = await fetchRecordCorpus(emotionAnalysis.value.total_records)
    const fullTextRecords = records.filter(
      (record) =>
        Number(record?.has_full_text) === 1 &&
        Boolean(record?.body_core || record?.body_clean)
    )
    if (!fullTextRecords.length) {
      throw new Error('未读取到可用全文')
    }
    allRecords.value = records
    corpusRecords.value = fullTextRecords
  } catch {
    allRecords.value = []
    corpusRecords.value = demoMode ? fallbackCorpusFromEvidence() : []
  } finally {
    keywordLoading.value = false
    await nextTick()
    requestAnimationFrame(() => {
      wordCloudEntered.value = true
    })
  }
}

onMounted(async () => {
  await loadEmotionAnalysis()
  await loadCorpusKeywords()
})
</script>
