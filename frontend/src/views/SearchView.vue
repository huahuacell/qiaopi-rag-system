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
          type="warning"
          show-icon
          :closable="false"
          class="archive-search-alert"
        />

        <section class="archive-result-summary">
          <div>
            <span>检索结果：</span>
            <strong>{{ resultCount }}</strong>
            <span>条相关侨批记录</span>
          </div>
          <i></i>
          <div>
            <span>当前模式：</span>
            <em>{{ modeLabel(response.mode || mode) }}</em>
          </div>
          <i></i>
          <div class="summary-evidence">
            <span>证据来源：</span>
            <b>原文片段</b>
            <b>元数据字段</b>
            <b>语义匹配</b>
          </div>
          <i></i>
          <p>数据状态：{{ error ? '本地演示数据' : '接口数据 / 本地回退可用' }}</p>
        </section>

        <section v-loading="loading" class="archive-result-list">
          <SearchResultCard
            v-for="(result, index) in response.results"
            :key="result.record_id"
            :result="result"
            :rank="index + 1"
          />
          <el-empty v-if="!response.results?.length && !loading" description="暂无记录" />
        </section>

        <aside class="archive-search-hint">
          <span>i</span>
          <p>如果后端语义索引尚未初始化，系统将显示本地演示结果并保留检索流程展示。</p>
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
            <p>各证据来源相互补充，混合检索模式下优先返回原文证据与语义匹配的交集记录。</p>
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
import fallbackResults from '../mock/search_results.json'

const mode = ref('hybrid')
const query = ref('八元 母亲 新加坡')
const filters = reactive({
  origin_place: '新加坡',
  destination_place: '',
  kinship: '母亲'
})
const uiFilters = reactive({
  era: true,
  evidenceFirst: true,
  rag: true
})
const response = ref({ total: 0, results: [] })
const loading = ref(false)
const error = ref('')

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
  { title: '原文片段', desc: '来自侨批正文中的直接匹配内容', tone: 'red' },
  { title: '元数据字段', desc: '来源地、亲属关系、年代等结构化信息', tone: 'green' },
  { title: '语义匹配', desc: '基于语义相似度返回的相关记录', tone: 'teal' },
  { title: 'RAG 证据', desc: '用于释读和生成任务的可追溯依据', tone: 'brown' }
]

const resultCount = computed(() => response.value.total ?? response.value.results?.length ?? 0)

const filterChips = computed(() => [
  {
    key: 'origin_place',
    label: `来源地：${filters.origin_place || '新加坡'}`,
    mark: '地',
    active: Boolean(filters.origin_place),
    apply: () => {
      filters.origin_place = filters.origin_place ? '' : '新加坡'
    }
  },
  {
    key: 'kinship',
    label: `亲属关系：${filters.kinship || '母亲'}`,
    mark: '亲',
    active: Boolean(filters.kinship),
    apply: () => {
      filters.kinship = filters.kinship ? '' : '母亲'
    }
  },
  {
    key: 'era',
    label: '年代：1930s',
    mark: '年',
    active: uiFilters.era,
    apply: () => {
      uiFilters.era = !uiFilters.era
    }
  },
  {
    key: 'evidenceFirst',
    label: '证据优先',
    mark: '证',
    active: uiFilters.evidenceFirst,
    apply: () => {
      uiFilters.evidenceFirst = !uiFilters.evidenceFirst
    }
  },
  {
    key: 'rag',
    label: 'RAG 片段',
    mark: 'R',
    active: uiFilters.rag,
    apply: () => {
      uiFilters.rag = !uiFilters.rag
    }
  }
])

function toggleChip(chip) {
  chip.apply()
}

function clearConditions() {
  query.value = ''
  filters.origin_place = ''
  filters.destination_place = ''
  filters.kinship = ''
  uiFilters.era = false
  uiFilters.evidenceFirst = false
  uiFilters.rag = false
}

function activeFilters() {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
}

async function runSearch() {
  loading.value = true
  error.value = ''
  const payload = {
    query: query.value,
    filters: activeFilters(),
    top_k: 10,
    expansion_mode: 'balanced'
  }

  try {
    response.value = await searchers[mode.value](payload)
  } catch {
    response.value = { ...fallbackResults, mode: mode.value, query: query.value }
    error.value = '后端不可用，已加载检索本地 mock 数据。'
  } finally {
    loading.value = false
  }
}

function modeLabel(value) {
  const labels = {
    keyword: '关键词检索',
    semantic: '语义检索',
    hybrid: '混合检索',
    similar: '相似推荐'
  }
  return labels[value] || value
}

onMounted(runSearch)
</script>
