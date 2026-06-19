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
          支持关键词检索、语义检索与混合检索，从侨批文本中定位相关记录、证据片段与匹配原因，帮助用户追溯书信中的人物关系、来源地与文化记忆。
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
          <div class="search-mode-tabs" role="tablist" aria-label="检索模式">
            <button
              v-for="item in searchModes"
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
                placeholder="输入关键词、亲属称谓、地名或语义问题，例如：八元 母亲 新加坡"
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

        <section class="archive-result-summary">
          <div>
            <span>命中单元：</span>
            <strong>{{ resultCount }}</strong>
            <span>条</span>
          </div>
          <div>
            <span>涉及记录：</span>
            <strong>{{ recordCount }}</strong>
            <span>封</span>
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
            v-for="(result, index) in response.results"
            :key="result.unit_id || `${result.record_id}-${index}`"
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
            正式接口模式不会静默回退到 Mock。混合检索降级时，页面会明确显示“关键词检索（混合降级）”。
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
              BM25、余弦相似度与 RRF 属于不同排序尺度。页面仅展示各自的排序贡献，不换算为百分比。
            </p>
          </footer>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { hybridSearch, keywordSearch, semanticSearch } from '../api/search'
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

const mode = ref('hybrid')
const lastRequestedMode = ref('hybrid')
const query = ref('母亲 寄款 查收')
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

const searchModes = [
  { value: 'keyword', label: '关键词检索' },
  { value: 'semantic', label: '语义检索' },
  { value: 'hybrid', label: '混合检索' }
]

const searchers = {
  keyword: keywordSearch,
  semantic: semanticSearch,
  hybrid: hybridSearch
}

const evidenceGuide = [
  { title: 'BM25 原始值', desc: 'FTS5 关键词排序信号；只在同一查询内比较。', tone: 'red' },
  { title: '余弦相似度', desc: '同一向量模型下的语义接近程度，不是置信百分比。', tone: 'green' },
  { title: 'RRF 融合值', desc: '融合关键词名次和语义名次，不与余弦值直接比较。', tone: 'teal' },
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
  {
    key: 'remittanceUnit',
    label: '仅汇款证据单元',
    mark: '证',
    active: uiFilters.remittanceUnit,
    apply: () => {
      uiFilters.remittanceUnit = !uiFilters.remittanceUnit
    }
  }
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

function activeFilters() {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== false)
  )
}

async function runSearch() {
  loading.value = true
  error.value = ''
  requestFailed.value = false
  lastRequestedMode.value = mode.value
  const payload = {
    query: query.value,
    filters: activeFilters(),
    top_k: 10,
    unit_types: uiFilters.remittanceUnit ? ['remittance'] : [],
    expansion_mode: 'balanced'
  }

  try {
    response.value = await searchers[mode.value](payload)
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
