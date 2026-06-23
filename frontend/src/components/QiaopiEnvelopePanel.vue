<template>
  <div
    class="qiaopi-result-panel"
    :class="[
      `is-${envelopeState}`,
      { 'is-editing': viewMode === 'edit', 'has-content': hasContent }
    ]"
    :style="assetVariables"
  >
    <div
      class="qiaopi-letter-stage"
      :data-envelope-state="envelopeState"
      :aria-busy="isAnimating"
    >
      <template v-if="!hasContent">
        <div class="qiaopi-letter-paper is-empty">
          <span class="qiaopi-paper-redline one" aria-hidden="true"></span>
          <span class="qiaopi-paper-redline two" aria-hidden="true"></span>
          <span class="qiaopi-paper-seal" aria-hidden="true">侨批</span>
          <p>暂无生成结果。输入内容后点击生成侨批体。</p>
        </div>
      </template>

      <template v-else>
        <div v-show="envelopeState === 'idle'" class="qiaopi-letter-paper">
          <span class="qiaopi-paper-redline one" aria-hidden="true"></span>
          <span class="qiaopi-paper-redline two" aria-hidden="true"></span>
          <span class="qiaopi-paper-seal" aria-hidden="true">侨批</span>
          <textarea
            v-if="viewMode === 'edit'"
            v-model="draftText"
            class="qiaopi-letter-editor"
            aria-label="编辑侨批体生成结果"
            @input="emitLatestDraft"
          ></textarea>
          <div v-else class="qiaopi-letter-display" aria-label="侨批体生成结果">
            <p
              v-for="(line, index) in letterLines"
              :key="`${index}-${line}`"
              :class="{ head: index === 0, foot: index === letterLines.length - 1 }"
            >
              {{ line || '\u00A0' }}
            </p>
          </div>
        </div>

        <div
          v-if="isAnimating"
          class="qiaopi-folding-letter"
          aria-hidden="true"
        >
          <div class="qiaopi-folding-letter-text">
            {{ compactPreview }}
          </div>
        </div>

        <div
          v-if="isAnimating"
          class="qiaopi-envelope-open"
          aria-hidden="true"
        ></div>

        <div
          v-if="envelopeState === 'sealing' || envelopeState === 'sealed'"
          class="qiaopi-envelope-sealed"
          aria-hidden="true"
        >
          <span class="qiaopi-wax-seal"></span>
          <span class="qiaopi-postmark"></span>
        </div>

        <div v-if="envelopeState === 'sealed'" class="qiaopi-sealed-message">
          <span aria-hidden="true">封</span>
          <strong>书信已封存</strong>
          <p>侨批已收入信封，文字修改仍被完整保留。</p>
        </div>
      </template>
    </div>

    <div class="qiaopi-result-toolbar" aria-label="生成结果操作">
      <template v-if="envelopeState === 'sealed'">
        <button class="primary" type="button" @click="openEnvelope">拆开重看</button>
        <button type="button" :disabled="!hasContent" @click="$emit('copy')">复制文本</button>
      </template>
      <template v-else>
        <button
          v-if="viewMode === 'display'"
          type="button"
          :disabled="!hasContent || isAnimating"
          @click="beginEditing"
        >
          编辑结果
        </button>
        <button
          v-else
          class="primary"
          type="button"
          :disabled="!hasContent"
          @click="saveEditing"
        >
          保存修改
        </button>
        <button type="button" :disabled="!hasContent || isAnimating" @click="$emit('copy')">
          复制文本
        </button>
        <button
          class="seal-action"
          type="button"
          :disabled="!hasContent || isAnimating || viewMode === 'edit' || loading"
          @click="sealLetter"
        >
          {{ isAnimating ? stateActionLabel : '装入信封' }}
        </button>
      </template>
    </div>

    <p class="qiaopi-envelope-status" role="status" aria-live="polite">
      {{ statusMessage }}
    </p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import '../assets/styles/qiaopi-envelope.css'
import envelopeOpen from '../assets/qiaopi-envelope/envelope-open.png'
import envelopeSealed from '../assets/qiaopi-envelope/envelope-sealed.png'
import foldedPaper from '../assets/qiaopi-envelope/folded-paper.png'
import letterPaper from '../assets/qiaopi-envelope/letter-paper.png'
import postmark from '../assets/qiaopi-envelope/postmark.png'
import waxSeal from '../assets/qiaopi-envelope/wax-seal.png'
import {
  ENVELOPE_STATES,
  envelopeSequence,
  isEnvelopeAnimating
} from '../utils/envelopeAnimation'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  generationKey: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'copy'])

const draftText = ref(props.modelValue)
const viewMode = ref('display')
const envelopeState = ref(ENVELOPE_STATES.IDLE)
const activeTimers = new Set()

const assetVariables = {
  '--qiaopi-letter-paper': `url("${letterPaper}")`,
  '--qiaopi-folded-paper': `url("${foldedPaper}")`,
  '--qiaopi-envelope-open': `url("${envelopeOpen}")`,
  '--qiaopi-envelope-sealed': `url("${envelopeSealed}")`,
  '--qiaopi-wax-seal': `url("${waxSeal}")`,
  '--qiaopi-postmark': `url("${postmark}")`
}

const hasContent = computed(() => Boolean(draftText.value.trim()))
const isAnimating = computed(() => isEnvelopeAnimating(envelopeState.value))
const letterLines = computed(() => splitLetterLines(draftText.value))
const compactPreview = computed(() =>
  draftText.value.replace(/\s+/g, ' ').trim().slice(0, 150)
)

const stateActionLabel = computed(() => {
  const labels = {
    folding: '折叠书信…',
    inserting: '收入信封…',
    sealing: '封缄归档…'
  }
  return labels[envelopeState.value] || '装入信封'
})

const statusMessage = computed(() => {
  if (!hasContent.value) return '生成结果出现后，可在此修改、复制或装入信封。'
  if (envelopeState.value === ENVELOPE_STATES.SEALED) return '封装完成，可拆开重看或复制最新文本。'
  if (isAnimating.value) return stateActionLabel.value
  if (viewMode.value === 'edit') return '正在编辑生成结果；保存后可装入信封。'
  return '生成结果可继续修改，复制操作始终使用最新版本。'
})

watch(
  () => props.modelValue,
  (nextValue) => {
    if (nextValue === draftText.value) return
    draftText.value = nextValue || ''
    resetPresentation()
  }
)

watch(
  () => props.generationKey,
  () => {
    draftText.value = props.modelValue || ''
    resetPresentation()
  }
)

function splitLetterLines(text) {
  if (!text) return []
  const normalized = String(text).trim()
  if (normalized.includes('\n')) return normalized.split('\n')
  return normalized
    .replace(/([。！？；：])/g, '$1\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function emitLatestDraft() {
  emit('update:modelValue', draftText.value)
}

function beginEditing() {
  if (!hasContent.value || isAnimating.value) return
  viewMode.value = 'edit'
}

function saveEditing() {
  emitLatestDraft()
  viewMode.value = 'display'
}

function prefersReducedMotion() {
  return typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function sealLetter() {
  if (!hasContent.value || isAnimating.value || viewMode.value === 'edit') return
  clearTimers()
  const sequence = envelopeSequence(prefersReducedMotion())
  for (const step of sequence) {
    if (step.at === 0) {
      envelopeState.value = step.state
      continue
    }
    const timerId = window.setTimeout(() => {
      activeTimers.delete(timerId)
      envelopeState.value = step.state
    }, step.at)
    activeTimers.add(timerId)
  }
}

function openEnvelope() {
  clearTimers()
  envelopeState.value = ENVELOPE_STATES.IDLE
  viewMode.value = 'display'
}

function resetPresentation() {
  clearTimers()
  envelopeState.value = ENVELOPE_STATES.IDLE
  viewMode.value = 'display'
}

function clearTimers() {
  for (const timerId of activeTimers) {
    window.clearTimeout(timerId)
  }
  activeTimers.clear()
}

onBeforeUnmount(clearTimers)
</script>
