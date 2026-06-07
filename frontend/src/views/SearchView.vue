<template>
  <section class="page-stack">
    <div class="tool-surface">
      <el-radio-group v-model="mode" class="mode-control">
        <el-radio-button label="keyword">关键词</el-radio-button>
        <el-radio-button label="semantic">语义</el-radio-button>
        <el-radio-button label="hybrid">混合</el-radio-button>
      </el-radio-group>

      <div class="search-form">
        <el-input
          v-model="query"
          size="large"
          clearable
          placeholder="按金额、亲属关系、地点或主题检索"
          @keyup.enter="runSearch"
        />
        <el-button type="primary" size="large" :loading="loading" @click="runSearch">
          <el-icon><Search /></el-icon>
          检索
        </el-button>
      </div>

      <div class="filter-row">
        <el-input v-model="filters.origin_place" clearable placeholder="来源地" />
        <el-input v-model="filters.destination_place" clearable placeholder="目的地" />
        <el-input v-model="filters.kinship" clearable placeholder="亲属关系" />
      </div>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="result-header">
      <strong>{{ response.total || 0 }}</strong>
      <span>条结果</span>
      <el-tag effect="plain">{{ modeLabel(response.mode || mode) }}</el-tag>
    </div>

    <div v-loading="loading" class="result-list">
      <SearchResultCard
        v-for="result in response.results"
        :key="result.record_id"
        :result="result"
      />
      <el-empty v-if="!response.results?.length && !loading" description="暂无记录" />
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import { hybridSearch, keywordSearch, semanticSearch } from '../api/search'
import SearchResultCard from '../components/SearchResultCard.vue'
import fallbackResults from '../mock/search_results.json'

const mode = ref('hybrid')
const query = ref('八元')
const filters = reactive({
  origin_place: '',
  destination_place: '',
  kinship: ''
})
const response = ref({ total: 0, results: [] })
const loading = ref(false)
const error = ref('')

const searchers = {
  keyword: keywordSearch,
  semantic: semanticSearch,
  hybrid: hybridSearch
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
    page: 1,
    page_size: 10
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
    keyword: '关键词',
    semantic: '语义',
    hybrid: '混合',
    similar: '相似推荐'
  }
  return labels[value] || value
}

onMounted(runSearch)
</script>
