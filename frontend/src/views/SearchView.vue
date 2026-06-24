<template>
  <section class="archive-search-page">
    <div class="archive-search-bg" aria-hidden="true">
      <span class="search-bg-seal search-seal-a">侨批</span>
      <span class="search-bg-seal search-seal-b">检</span>
      <span class="search-bg-wash"></span>
      <span class="search-bg-line"></span>
    </div>

    <nav class="archive-search-breadcrumb" aria-label="检索页面路径">
      <span>侨批 RAG</span>
      <i>›</i>
      <span>档案检索</span>
      <i>›</i>
      <strong>证据检索</strong>
    </nav>

    <section class="archive-search-header">
      <div class="search-header-grid" aria-hidden="true"></div>
      <div class="search-header-seal" aria-hidden="true">
        <span>侨批</span>
        <small>数字档案馆</small>
      </div>
      <div class="search-header-wash" aria-hidden="true"></div>

      <div class="search-header-content">
        <div class="search-header-label">
          <span>档案检索 · ARCHIVE SEARCH</span>
          <i></i>
          <em>QP-SEARCH-001</em>
        </div>

        <h1>检索跨海家书中的人、地与汇款线索</h1>
        <p>
          支持关键词、语义、混合与 GraphRAG 检索，从侨批文本和知识图谱中定位相关记录、证据片段与关系路径，帮助用户追溯书信中的人物关系、来源地与文化记忆。
        </p>

        <div class="search-header-badges">
          <strong>Evidence Retrieval</strong>
          <span>v2.4.1 · RAG</span>
        </div>
      </div>
    </section>

    <div class="archive-search-layout">
      <main class="archive-search-main">
        <section class="archive-search-panel">
          <div class="search-corpus-tabs" aria-label="检索数据范围">
            <button
              type="button"
              :class="{ active: corpusScope === 'fulltext' }"
              @click="setCorpusScope('fulltext')"
            >
              全文证据 · 213
            </button>
            <button
              type="button"
              :class="{ active: corpusScope === 'metadata' }"
              @click="setCorpusScope('metadata')"
            >
              目录元数据 · 50,064
            </button>
          </div>
          <div class="search-mode-tabs" role="tablist" aria-label="检索模式">
            <button
              v-for="item in availableSearchModes"
              :key="item.value"
              type="button"
              :class="{ active: mode === item.value }"
              @click="mode = item.value"
            >
              {{ item.label }}
              <span v-if="mode === item.value"></span>
            </button>
          </div>

          <div class="search-panel-body">
            <div class="archive-search-input">
              <el-icon><Search /></el-icon>
              <input
                v-model="query"
                type="search"
                :placeholder="searchPlaceholder"
                @keyup.enter="runSearch"
              />
              <button v-if="query" type="button" aria-label="清空关键词" @click="query = ''">×</button>
            </div>

            <div class="archive-search-actions">
              <button class="search-primary" type="button" :disabled="loading" @click="runSearch">
                <el-icon><Search /></el-icon>
                {{ loading ? '检索中' : '开始检索' }}
              </button>
              <button class="search-secondary" type="button" @click="clearConditions">清空条件</button>
            </div>

            <div class="archive-search-examples" aria-label="可选检索词">
              <span>可选词示例</span>
              <button
                v-for="example in searchExamples"
                :key="example.query"
                type="button"
                :class="{ active: isActiveExample(example) }"
                :title="example.desc"
                @click="applySearchExample(example)"
              >
                {{ example.query }}
              </button>
            </div>

            <div class="archive-filter-chips" aria-label="检索筛选条件">
              <button
                v-for="chip in filterChips"
                :key="chip.key"
                type="button"
                :class="{ active: chip.active }"
                @click="toggleChip(chip)"
              >
                <span>{{ chip.mark }}</span>
                {{ chip.label }}
                <i v-if="chip.active">×</i>
              </button>
            </div>
          </div>
        </section>

        <el-alert
          v-if="error || response.error_message"
          :title="error || response.error_message"
          :type="requestFailed ? 'error' : 'warning'"
          show-icon
          :closable="false"
          class="archive-search-alert"
        />

        <section
          v-if="hasSearched"
          class="search-execution-status"
          :class="`is-${execution.tone}`"
          aria-live="polite"
        >
          <div>
            <span>实际执行模式</span>
            <strong>{{ execution.effectiveLabel }}</strong>
          </div>
          <p>{{ execution.explanation }}</p>
          <em>{{ execution.dataLabel }}</em>
        </section>

        <section
          v-if="hasSearched && lastRequestedMode === 'graphrag'"
          class="graph-search-summary"
          :class="{ 'is-fallback': response.graph_fallback }"
        >
          <header>
            <div>
              <span>GraphRAG 图谱召回</span>
              <strong>
                {{ response.graph_enabled ? '图谱已参与排序' : '已自动降级' }}
              </strong>
            </div>
            <em>{{ response.graph_candidate_count || 0 }} 条候选记录</em>
          </header>
          <div v-if="response.graph_seed_nodes?.length" class="graph-seed-list">
            <span
              v-for="seed in response.graph_seed_nodes"
              :key="seed.id"
            >
              {{ seed.matched_term }} → {{ seed.label }}
            </span>
          </div>
          <p>
            {{ response.graph_fallback_reason || response.graph_message || '图谱结果已与原检索链路融合。' }}
          </p>
        </section>

        <section class="archive-result-summary">
          <div>
            <span>{{ corpusScope === 'metadata' ? '命中目录：' : '命中单元：' }}</span>
            <strong>{{ resultCount }}</strong>
            <span>条</span>
          </div>
          <div>
            <span>{{ corpusScope === 'metadata' ? '目录条目：' : '涉及记录：' }}</span>
            <strong>{{ recordCount }}</strong>
            <span>{{ corpusScope === 'metadata' ? '条' : '封' }}</span>
          </div>
          <i></i>
          <div>
            <span>请求模式：</span>
            <em>{{ execution.requestedLabel }}</em>
          </div>
          <div>
            <span>实际模式：</span>
            <em :class="{ degraded: execution.degraded }">{{ execution.effectiveLabel }}</em>
          </div>
          <i></i>
          <div class="summary-evidence">
            <span>排序来源：</span>
            <b v-for="source in execution.sources" :key="source">{{ source }}</b>
            <b v-if="!execution.sources.length">未执行</b>
          </div>
          <i></i>
          <p>数据状态：{{ execution.dataLabel }}</p>
        </section>

        <section v-loading="loading" class="archive-result-list">
          <SearchResultCard
            v-for="(result, index) in corpusScope === 'fulltext' ? response.results : []"
            :key="result.unit_id || `${result.record_id}-${index}`"
            :result="result"
            :rank="index + 1"
            :execution="execution"
          />
          <MetadataSearchResultCard
            v-for="(result, index) in corpusScope === 'metadata' ? response.results : []"
            :key="result.metadata_id || index"
            :result="result"
            :rank="index + 1"
            :execution="execution"
          />
          <el-empty
            v-if="!response.results?.length && !loading"
            :description="requestFailed ? '检索服务不可用，未加载 Mock 数据' : '暂无检索结果'"
          />
        </section>

        <aside class="archive-search-hint">
          <span>i</span>
          <p v-if="demoMode">
            当前显式启用了演示模式；接口失败时才会加载本地演示结果，并清楚标记为测试数据。
          </p>
          <p v-else>
            <template v-if="corpusScope === 'metadata'">
              目录元数据用于发现档案线索，不会作为 RAG 生成的全文证据；仅已关联记录可以跳转查看全文。
            </template>
            <template v-else>
              正式接口模式不会静默回退到 Mock。GraphRAG 无法识别有效节点时，会明确降级到现有混合检索。
            </template>
          </p>
        </aside>
      </main>

      <aside class="archive-evidence-panel">
        <div class="evidence-panel-grid" aria-hidden="true"></div>
        <div class="evidence-panel-seal" aria-hidden="true">
          <span>侨批</span>
          <small>数字档案馆</small>
        </div>

        <div class="evidence-panel-content">
          <header>
            <el-icon><Reading /></el-icon>
            <h2>证据链说明</h2>
            <i></i>
          </header>

          <div class="evidence-guide-list">
            <article v-for="item in evidenceGuide" :key="item.title">
              <strong :class="item.tone">{{ item.title }}</strong>
              <p>{{ item.desc }}</p>
            </article>
          </div>

          <footer>
            <span></span>
            <p>
              BM25、余弦相似度、图谱分与 RRF 属于不同排序尺度。页面仅展示各自的排序贡献，不换算为百分比。
            </p>
          </footer>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { graphRagSearch, hybridSearch, keywordSearch, semanticSearch } from '../api/search'
import { searchMetadata } from '../api/metadata'
import MetadataSearchResultCard from '../components/MetadataSearchResultCard.vue'
import SearchResultCard from '../components/SearchResultCard.vue'
import {
  apiFailureMessage,
  demoFailureMessage,
  demoMode
} from '../config/runtime'
import fallbackResults from '../mock/search_results.json'
import {
  buildDemoSearchResponse,
  resolveSearchExecution
} from '../utils/searchPresentation'

const route = useRoute()
const corpusScope = ref('fulltext')
const mode = ref('hybrid')
const lastRequestedMode = ref('hybrid')
const query = ref(String(route.query.query || '').trim() || '母亲')
const filters = reactive({
  place: '',
  year_normalized: '',
  has_remittance: false
})
const uiFilters = reactive({
  remittanceUnit: false
})
const response = ref({ results: [], grouped_by_record: [] })
const loading = ref(false)
const error = ref('')
const requestFailed = ref(false)
const hasSearched = ref(false)
const searchResultLimit = 100

const searchModes = [
  { value: 'keyword', label: '关键词检索' },
  { value: 'semantic', label: '语义检索' },
  { value: 'hybrid', label: '混合检索' },
  { value: 'graphrag', label: 'GraphRAG' }
]

const searchExamples = [
  {
    query: '壹佰元',
    scope: 'fulltext',
    mode: 'keyword',
    desc: '精确词：命中金额原文，避免语义召回其他金额。'
  },
  {
    query: '新春',
    scope: 'fulltext',
    mode: 'keyword',
    desc: '节令词：命中新春相关祝语与时令问候。'
  },
  {
    query: '成婚',
    scope: 'fulltext',
    mode: 'semantic',
    desc: '语义检索：关键词无命中，但可召回完婚、婚事等相关表达。'
  },
  {
    query: '宋树钊',
    scope: 'fulltext',
    mode: 'keyword',
    desc: '精确检索：展示同一寄批人多封侨批记录的聚合发现。'
  },
  {
    query: '读书',
    scope: 'fulltext',
    mode: 'hybrid',
    desc: '混合检索：展示教育、勤学、学业相关嘱咐。'
  },
  {
    query: '母亲',
    scope: 'fulltext',
    mode: 'graphrag',
    desc: 'GraphRAG：展示母亲、家慈、慈亲等亲属称谓的图谱关联。'
  },
  {
    query: '平安',
    scope: 'fulltext',
    mode: 'graphrag',
    desc: 'GraphRAG：展示 safety 主题节点参与召回。'
  },
  {
    query: '新加坡',
    scope: 'metadata',
    mode: 'hybrid',
    desc: '目录元数据：展示海外地点字段的档案发现。'
  },
  {
    query: '广东',
    scope: 'metadata',
    mode: 'hybrid',
    desc: '目录元数据：展示侨乡地点字段的档案发现。'
  }
]

const availableSearchModes = computed(() =>
  corpusScope.value === 'metadata'
    ? searchModes.filter((item) => item.value !== 'graphrag')
    : searchModes
)

const searchPlaceholder = computed(() =>
  corpusScope.value === 'metadata'
    ? '搜索目录题名、寄收批人、年代、地点或亲属关系，例如：新加坡 母亲 1973'
    : '输入关键词、亲属称谓、地名或语义问题，例如：八元 母亲 新加坡'
)

const searchers = {
  keyword: keywordSearch,
  semantic: semanticSearch,
  hybrid: hybridSearch,
  graphrag: graphRagSearch
}

const evidenceGuide = [
  { title: 'BM25 原始值', desc: 'FTS5 关键词排序信号；只在同一查询内比较。', tone: 'red' },
  { title: '余弦相似度', desc: '同一向量模型下的语义接近程度，不是置信百分比。', tone: 'green' },
  { title: 'RRF 融合值', desc: '融合关键词名次和语义名次，不与余弦值直接比较。', tone: 'teal' },
  { title: '图谱关联分', desc: '综合节点匹配、关系置信度、节点稀有度与多节点覆盖率。', tone: 'green' },
  { title: '证据追溯', desc: '每个命中保留记录、检索单元与来源字段。', tone: 'brown' }
]

const execution = computed(() =>
  resolveSearchExecution(lastRequestedMode.value, response.value, {
    demoMode,
    requestFailed: requestFailed.value,
    failureMessage: error.value
  })
)

const resultCount = computed(() => response.value.results?.length ?? 0)
const recordCount = computed(() => {
  if (corpusScope.value === 'metadata') return response.value.results?.length ?? 0
  if (response.value.grouped_by_record?.length) return response.value.grouped_by_record.length
  return new Set((response.value.results || []).map((item) => item.record_id).filter(Boolean)).size
})

const filterChips = computed(() => [
  {
    key: 'place',
    label: `地点：${filters.place || '新加坡'}`,
    mark: '地',
    active: Boolean(filters.place),
    apply: () => {
      filters.place = filters.place ? '' : '新加坡'
    }
  },
  {
    key: 'has_remittance',
    label: '包含汇款',
    mark: '款',
    active: filters.has_remittance,
    apply: () => {
      filters.has_remittance = !filters.has_remittance
    }
  },
  {
    key: 'year_normalized',
    label: `年代：${filters.year_normalized || '1933'}`,
    mark: '年',
    active: Boolean(filters.year_normalized),
    apply: () => {
      filters.year_normalized = filters.year_normalized ? '' : '1933'
    }
  },
  ...(corpusScope.value === 'fulltext' ? [{
    key: 'remittanceUnit',
    label: '仅汇款证据单元',
    mark: '证',
    active: uiFilters.remittanceUnit,
    apply: () => {
      uiFilters.remittanceUnit = !uiFilters.remittanceUnit
    }
  }] : [])
])

function toggleChip(chip) {
  chip.apply()
}

function clearConditions() {
  query.value = ''
  filters.place = ''
  filters.year_normalized = ''
  filters.has_remittance = false
  uiFilters.remittanceUnit = false
}

function clearFiltersOnly() {
  filters.place = ''
  filters.year_normalized = ''
  filters.has_remittance = false
  uiFilters.remittanceUnit = false
}

function setCorpusScope(scope) {
  corpusScope.value = scope
  if (scope === 'metadata' && mode.value === 'graphrag') {
    mode.value = 'hybrid'
  }
  lastRequestedMode.value = mode.value
  response.value = { results: [], grouped_by_record: [] }
  hasSearched.value = false
}

function activeFilters() {
  const selected = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== false)
  )
  if (corpusScope.value === 'metadata' && selected.year_normalized) {
    selected.year_from = selected.year_normalized
    selected.year_to = selected.year_normalized
    delete selected.year_normalized
  }
  return selected
}

function isActiveExample(example) {
  return (
    corpusScope.value === example.scope &&
    mode.value === example.mode &&
    query.value === example.query
  )
}

async function applySearchExample(example) {
  corpusScope.value = example.scope
  mode.value = example.mode
  lastRequestedMode.value = example.mode
  query.value = example.query
  clearFiltersOnly()
  await runSearch()
}

async function runSearch() {
  loading.value = true
  error.value = ''
  requestFailed.value = false
  lastRequestedMode.value = mode.value
  const payload = {
    query: query.value,
    filters: activeFilters(),
    top_k: searchResultLimit,
    unit_types: uiFilters.remittanceUnit ? ['remittance'] : [],
    expansion_mode: 'balanced'
  }

  try {
    response.value =
      corpusScope.value === 'metadata'
        ? await searchMetadata({
            query: payload.query,
            filters: payload.filters,
            top_k: payload.top_k,
            retrieval_mode: mode.value
          })
        : await searchers[mode.value](payload)
  } catch (requestError) {
    if (demoMode) {
      response.value = buildDemoSearchResponse(fallbackResults, mode.value, query.value)
      error.value = demoFailureMessage('检索请求')
    } else {
      response.value = {
        query: query.value,
        results: [],
        grouped_by_record: [],
        semantic_enabled: false,
        semantic_quality: 'disabled',
        fusion_method: null,
        error_message: null
      }
      requestFailed.value = true
      error.value = apiFailureMessage(requestError, '检索请求')
    }
  } finally {
    loading.value = false
    hasSearched.value = true
  }
}

onMounted(runSearch)
</script>
