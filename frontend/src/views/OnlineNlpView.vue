<template>
  <section class="nlp-workbench">
    <header class="nlp-hero">
      <div>
        <p>ONLINE NLP · 可追溯规则抽取</p>
        <h1>侨批文本在线解析</h1>
        <span>
          在线与离线建库共享同一套文本规范化规则。每个实体、关系和任务槽位均返回
          原文及规范文本偏移、规则版本、置信度与复核标记。
        </span>
      </div>
      <aside>
        <small>运行模式</small>
        <strong>{{ result.engine === 'deterministic_rule' ? '确定性规则' : '尚未执行' }}</strong>
        <em>{{ result.pipeline_version || '等待分析' }}</em>
      </aside>
    </header>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="nlp-alert"
    />

    <section class="nlp-input-card">
      <header>
        <div>
          <h2>输入待解析文本</h2>
          <p>最多 20,000 字；结果不会静默回退到 mock。</p>
        </div>
        <el-select v-model="task" aria-label="NLP 任务类型">
          <el-option label="通用抽取" value="general" />
          <el-option label="白话释读槽位" value="interpretation" />
          <el-option label="风格转换槽位" value="style_transfer" />
        </el-select>
      </header>
      <el-input
        v-model="text"
        type="textarea"
        :rows="9"
        maxlength="20000"
        show-word-limit
        placeholder="输入侨批原文或现代家书文本"
      />
      <footer>
        <el-button @click="resetText">恢复示例</el-button>
        <el-button type="primary" :loading="loading" :disabled="!text.trim()" @click="runAnalysis">
          {{ loading ? '解析中…' : '执行在线 NLP' }}
        </el-button>
      </footer>
    </section>

    <template v-if="hasResult">
      <section class="nlp-summary-grid">
        <article>
          <span>实体</span>
          <strong>{{ result.summary.entity_count }}</strong>
          <small>{{ result.entity_extractor_version }}</small>
        </article>
        <article>
          <span>关系</span>
          <strong>{{ result.summary.relation_count }}</strong>
          <small>{{ result.relation_extractor_version }}</small>
        </article>
        <article>
          <span>任务槽位</span>
          <strong>{{ result.summary.slot_count }}</strong>
          <small>{{ result.slot_extractor_version }}</small>
        </article>
        <article :class="{ warning: result.review_required }">
          <span>人工复核</span>
          <strong>{{ result.review_required ? result.summary.review_item_count : '无需' }}</strong>
          <small>{{ result.review_required ? '存在低置信或不确定文本' : '规则结果通过' }}</small>
        </article>
      </section>

      <el-alert
        v-if="result.review_required"
        title="该结果需要人工复核"
        type="warning"
        show-icon
        :closable="false"
        class="nlp-alert"
      >
        <p v-for="reason in result.review_reasons" :key="reason">{{ reason }}</p>
      </el-alert>

      <el-alert
        v-if="spanIntegrityFailures"
        :title="`${spanIntegrityFailures} 个偏移未通过前端一致性检查`"
        type="error"
        show-icon
        :closable="false"
        class="nlp-alert"
      />

      <section class="nlp-normalization-card">
        <header>
          <div>
            <h2>规范化结果</h2>
            <p>{{ result.normalization_version }}</p>
          </div>
          <el-tag :type="result.normalization_changed ? 'warning' : 'success'" effect="plain">
            {{ result.normalization_changed ? '文本已规范化' : '原文无需改写' }}
          </el-tag>
        </header>
        <div class="nlp-text-compare">
          <article>
            <span>原文</span>
            <pre>{{ result.original_text }}</pre>
          </article>
          <article>
            <span>规范文本</span>
            <pre>{{ result.normalized_text }}</pre>
          </article>
        </div>
      </section>

      <section class="nlp-result-card">
        <header>
          <h2>实体与值</h2>
          <p>偏移采用半开区间 [start, end)。</p>
        </header>
        <div v-if="result.entities.length" class="nlp-entity-grid">
          <article
            v-for="entity in result.entities"
            :key="entity.entity_id"
            :class="{ review: entity.needs_review }"
          >
            <div class="nlp-item-heading">
              <el-tag effect="plain">{{ entityTypeLabel(entity.entity_type) }}</el-tag>
              <span>{{ confidenceText(entity.confidence) }}</span>
            </div>
            <h3>{{ entity.value }}</h3>
            <blockquote>{{ entity.source_text }}</blockquote>
            <dl>
              <div><dt>原文偏移</dt><dd>{{ formatOffset(entity) }}</dd></div>
              <div><dt>规范偏移</dt><dd>{{ formatOffset(entity, true) }}</dd></div>
              <div><dt>规则</dt><dd>{{ entity.rule_id }}</dd></div>
              <div><dt>版本</dt><dd>{{ entity.extractor_version }}</dd></div>
            </dl>
            <el-tag v-if="entity.needs_review" type="warning" size="small">需要复核</el-tag>
          </article>
        </div>
        <el-empty v-else description="未抽取到实体" />
      </section>

      <section class="nlp-result-card">
        <header>
          <h2>关系抽取</h2>
          <p>关系证据同样保留原文与规范文本偏移。</p>
        </header>
        <div v-if="result.relations.length" class="nlp-relation-list">
          <article
            v-for="relation in result.relations"
            :key="relation.relation_id"
            :class="{ review: relation.needs_review }"
          >
            <div>
              <el-tag effect="plain">{{ relationTypeLabel(relation.relation_type) }}</el-tag>
              <strong>{{ relation.source_value }} → {{ relation.target_value }}</strong>
              <span>{{ confidenceText(relation.confidence) }}</span>
            </div>
            <blockquote>{{ relation.evidence_text }}</blockquote>
            <footer>
              <code>{{ formatOffset(relation) }}</code>
              <code>{{ formatOffset(relation, true) }}</code>
              <small>{{ relation.rule_id }} · {{ relation.extractor_version }}</small>
            </footer>
          </article>
        </div>
        <el-empty v-else description="未抽取到关系" />
      </section>

      <section class="nlp-result-card">
        <header>
          <h2>生成任务槽位</h2>
          <p>可供白话释读、侨批风格转换和后续一致性检查使用。</p>
        </header>
        <el-table :data="result.slots" empty-text="未抽取到任务槽位">
          <el-table-column label="槽位" min-width="130">
            <template #default="{ row }">{{ slotLabel(row.slot_name) }}</template>
          </el-table-column>
          <el-table-column prop="value" label="值" min-width="150" />
          <el-table-column prop="source_text" label="来源文本" min-width="200" />
          <el-table-column label="偏移" min-width="210">
            <template #default="{ row }">
              <code>{{ formatOffset(row) }}</code><br />
              <code>{{ formatOffset(row, true) }}</code>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="100">
            <template #default="{ row }">{{ confidenceText(row.confidence) }}</template>
          </el-table-column>
          <el-table-column label="复核" width="90">
            <template #default="{ row }">
              <el-tag :type="row.needs_review ? 'warning' : 'success'" size="small">
                {{ row.needs_review ? '需要' : '通过' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { analyzeNlpText } from '../api/nlp'
import { apiFailureMessage } from '../config/runtime'
import {
  ENTITY_TYPE_LABELS,
  RELATION_TYPE_LABELS,
  SLOT_LABELS,
  confidenceText,
  formatOffset,
  validateSpanItem
} from '../utils/nlpPresentation'

const sampleText =
  '寄批人：儿海泉\n收批人：母亲大人\n\n母亲大人尊前：我在星洲平安，今寄回中央法币陆元，给家中买米和药。戊七月初十日。'

const text = ref(sampleText)
const task = ref('general')
const loading = ref(false)
const error = ref('')
const result = reactive({
  engine: '',
  pipeline_version: '',
  normalization_version: '',
  entity_extractor_version: '',
  relation_extractor_version: '',
  slot_extractor_version: '',
  original_text: '',
  normalized_text: '',
  normalization_changed: false,
  review_required: false,
  review_reasons: [],
  entities: [],
  relations: [],
  slots: [],
  summary: { entity_count: 0, relation_count: 0, slot_count: 0, review_item_count: 0 }
})

const hasResult = computed(() => Boolean(result.pipeline_version))
const spanIntegrityFailures = computed(() =>
  [...result.entities, ...result.relations, ...result.slots].filter(
    (item) => !validateSpanItem(item, result.original_text, result.normalized_text)
  ).length
)

function entityTypeLabel(value) {
  return ENTITY_TYPE_LABELS[value] || value
}

function relationTypeLabel(value) {
  return RELATION_TYPE_LABELS[value] || value
}

function slotLabel(value) {
  return SLOT_LABELS[value] || value
}

async function runAnalysis() {
  if (!text.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    Object.assign(result, await analyzeNlpText(text.value, task.value))
  } catch (requestError) {
    error.value = apiFailureMessage(requestError, '在线 NLP 请求')
  } finally {
    loading.value = false
  }
}

function resetText() {
  text.value = sampleText
}

onMounted(runAnalysis)
</script>
