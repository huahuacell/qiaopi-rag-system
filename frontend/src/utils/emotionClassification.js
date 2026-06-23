const WORD_CLOUD_PALETTE = [
  '#0F4A43',
  '#A74432',
  '#6D765F',
  '#1A6B61',
  '#8A6A47',
  '#6F7C78'
]

function finiteNumber(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function boundedRatio(value) {
  return Math.min(1, Math.max(0, finiteNumber(value)))
}

function cleanTerm(value) {
  return String(value || '')
    .replace(/[，。！？；：、“”‘’（）《》〈〉【】\s]/g, '')
    .trim()
}

function countOccurrences(text, term) {
  if (!text || !term) return 0
  let count = 0
  let cursor = 0

  while (cursor < text.length) {
    const index = text.indexOf(term, cursor)
    if (index < 0) break
    count += 1
    cursor = index + term.length
  }

  return count
}

function hashString(value) {
  let hash = 2166136261
  for (const character of String(value || '')) {
    hash ^= character.codePointAt(0)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

function createSeededRandom(seed) {
  let state = seed || 0x9e3779b9
  return () => {
    state ^= state << 13
    state ^= state >>> 17
    state ^= state << 5
    return (state >>> 0) / 4294967296
  }
}

function boxesOverlap(left, right, padding = 5) {
  return !(
    left.x + left.width + padding < right.x ||
    right.x + right.width + padding < left.x ||
    left.y + left.height + padding < right.y ||
    right.y + right.height + padding < left.y
  )
}

export function normalizeEmotionDistribution(items) {
  const source = Array.isArray(items) ? items : []
  const total = source.reduce((sum, item) => sum + Number(item?.record_count || 0), 0)
  const maximumCount = Math.max(
    0,
    ...source.map((item) => Number(item?.record_count || 0))
  )
  if (!total) {
    return source.map((item) => ({
      ...item,
      normalized_ratio: 0,
      relative_ratio: 0,
      display_percent: 0
    }))
  }

  const normalized = source.map((item, index) => {
    const ratio = Number(item?.record_count || 0) / total
    const exactPercent = ratio * 100
    return {
      ...item,
      normalized_ratio: ratio,
      relative_ratio: maximumCount ? Number(item?.record_count || 0) / maximumCount : 0,
      display_percent: Math.floor(exactPercent),
      remainder: exactPercent - Math.floor(exactPercent),
      original_index: index
    }
  })
  let remaining = 100 - normalized.reduce((sum, item) => sum + item.display_percent, 0)

  normalized
    .slice()
    .sort((left, right) => right.remainder - left.remainder || left.original_index - right.original_index)
    .forEach((item) => {
      if (remaining <= 0) return
      normalized[item.original_index].display_percent += 1
      remaining -= 1
    })

  return normalized.map(({ remainder, original_index, ...item }) => item)
}

const REMITTANCE_AMOUNT_BUCKETS = [
  { key: 'up-to-5', label: '5元及以下', minimum: 0, maximum: 5 },
  { key: '6-to-10', label: '6—10元', minimum: 5, maximum: 10 },
  { key: '11-to-30', label: '11—30元', minimum: 10, maximum: 30 },
  { key: '31-to-100', label: '31—100元', minimum: 30, maximum: 100 },
  { key: 'over-100', label: '100元以上', minimum: 100, maximum: Infinity }
]

const NATIONAL_THEME_RULES = [
  {
    key: 'national-crisis',
    label: '国难与民生',
    terms: ['国难时期', '国难', '抗战', '抗日', '救亡', '救国']
  },
  {
    key: 'diaspora-policy',
    label: '侨汇与国家',
    terms: ['祖国领事', '华侨寄银', '华侨汇款', '侨汇']
  },
  {
    key: 'homeland-return',
    label: '乡国归思',
    terms: ['回归祖国', '报效祖国']
  }
]

function parseRemittanceMentions(record) {
  const source = record?.raw_fields?.remittance_mentions_json
  if (Array.isArray(source)) return source
  if (!source) return []

  try {
    const parsed = JSON.parse(source)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function primaryRemittance(record) {
  const mentions = parseRemittanceMentions(record)
  const mention =
    mentions.find((item) => Boolean(item?.is_primary_candidate)) ||
    mentions[0] ||
    null
  const amountNumber = finiteNumber(
    mention?.amount_number ?? record?.raw_fields?.remittance_amount_number,
    NaN
  )

  if (!Number.isFinite(amountNumber) || amountNumber <= 0) return null
  return {
    amountNumber,
    currency: String(
      mention?.currency || record?.raw_fields?.currency || '未标注币种'
    ).trim() || '未标注币种'
  }
}

export function buildRemittanceAmountSummary(records) {
  const source = Array.isArray(records) ? records : []
  const remittances = source.map(primaryRemittance).filter(Boolean)
  const maximumBucketCount = Math.max(
    0,
    ...REMITTANCE_AMOUNT_BUCKETS.map((bucket) =>
      remittances.filter(
        (item) =>
          item.amountNumber > bucket.minimum &&
          item.amountNumber <= bucket.maximum
      ).length
    )
  )
  const buckets = REMITTANCE_AMOUNT_BUCKETS.map((bucket) => {
    const count = remittances.filter(
      (item) =>
        item.amountNumber > bucket.minimum &&
        item.amountNumber <= bucket.maximum
    ).length
    return {
      key: bucket.key,
      label: bucket.label,
      count,
      ratio: remittances.length ? count / remittances.length : 0,
      relativeRatio: maximumBucketCount ? count / maximumBucketCount : 0
    }
  })
  const currencies = new Map()

  remittances.forEach((item) => {
    currencies.set(item.currency, (currencies.get(item.currency) || 0) + 1)
  })

  return {
    totalRecords: source.length,
    amountRecordCount: remittances.length,
    coverageRatio: source.length ? remittances.length / source.length : 0,
    buckets,
    currencies: [...currencies.entries()]
      .map(([label, count]) => ({
        label,
        count,
        ratio: remittances.length ? count / remittances.length : 0
      }))
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, 'zh-CN'))
  }
}

function contextualSnippet(text, term, radius = 62) {
  const source = String(text || '').replace(/\s+/g, ' ').trim()
  const index = source.indexOf(term)
  if (index < 0) return ''
  const start = Math.max(0, index - radius)
  const end = Math.min(source.length, index + term.length + radius)
  return `${start > 0 ? '…' : ''}${source.slice(start, end)}${end < source.length ? '…' : ''}`
}

export function selectNationalThemeRecords(records, limit = 4) {
  return (Array.isArray(records) ? records : [])
    .map((record) => {
      if (Number(record?.has_full_text) !== 1) return null
      const text = String(record?.body_core || record?.body_clean || '')
      if (!text) return null

      const rule = NATIONAL_THEME_RULES.find((item) =>
        item.terms.some((term) => text.includes(term))
      )
      if (!rule) return null

      const rawMatchedTerms = rule.terms.filter((term) => text.includes(term))
      const matchedTerms = rawMatchedTerms.filter(
        (term) =>
          !rawMatchedTerms.some(
            (otherTerm) => otherTerm !== term && otherTerm.includes(term)
          )
      )
      return {
        recordId: String(record.record_id || ''),
        year: String(record.year_normalized || ''),
        title: String(record.title_reference || record.title || record.record_id || ''),
        themeKey: rule.key,
        themeLabel: rule.label,
        matchedTerms,
        snippet: contextualSnippet(text, matchedTerms[0])
      }
    })
    .filter(Boolean)
    .sort((left, right) => (
      Number(left.year || Infinity) - Number(right.year || Infinity) ||
      left.recordId.localeCompare(right.recordId)
    ))
    .slice(0, Math.max(0, Number(limit) || 0))
}

const CORPUS_STOP_TERMS = new Set([
  '一片',
  '一事',
  '一下',
  '一些',
  '一切',
  '一书中',
  '一方',
  '一日',
  '一时',
  '一月',
  '不胜',
  '不能',
  '之内',
  '之事',
  '之用',
  '之至',
  '之后',
  '之故',
  '之情',
  '之意',
  '之日',
  '之时',
  '之项',
  '之类',
  '亦可',
  '以后',
  '以为',
  '以作',
  '以及',
  '此次',
  '但是',
  '何人',
  '何时',
  '何等',
  '其余',
  '则可',
  '即日',
  '又及',
  '只因',
  '可知',
  '可得',
  '另者',
  '各事',
  '各情',
  '因此',
  '如命',
  '如此',
  '已悉',
  '已经',
  '并无',
  '不一',
  '对于',
  '应知',
  '应用',
  '当知',
  '所有',
  '日后',
  '日前',
  '敬启者',
  '敬禀者',
  '时候',
  '未卜',
  '查收为荷',
  '此事',
  '此情',
  '然后',
  '现刻',
  '现时',
  '现在',
  '禀者',
  '祈查收',
  '至祈',
  '至祈查收',
  '由于',
  '等情',
  '至今',
  '至时',
  '至于',
  '兹逢',
  '兹付',
  '兹者',
  '余言',
  '余无别',
  '作家',
  '刻下',
  '启者',
  '容后',
  '将来',
  '如何',
  '所以',
  '收次',
  '示知',
  '知悉',
  '作为',
  '来知',
  '详悉',
  '近来',
  '而已',
  '专此',
  '祈为',
  '肃此',
  '特此',
  '若有',
  '虽有',
  '诸件',
  '诸事',
  '诸务',
  '近日',
  '迄今',
  '这样',
  '那些'
])

function normalizeCorpusText(value) {
  return String(value || '')
    .replace(/\r?\n/g, '')
    .replace(/[，。！？；：、“”‘’（）()《》〈〉【】\[\]〔〕—…·\s]/g, '')
}

function corpusTerms(value) {
  return [...new Set(
    String(value || '')
      .split(/[；;、,\n]+/)
      .map(cleanTerm)
      .filter((term) => (
        term.length >= 2 &&
        term.length <= 8 &&
        /^[\u3400-\u9fff]+$/u.test(term) &&
        !CORPUS_STOP_TERMS.has(term)
      ))
  )]
}

export function buildCorpusKeywordCloud(records, maxWords = 72) {
  const metrics = new Map()
  const corpus = (Array.isArray(records) ? records : [])
    .filter((record) => Number(record?.has_full_text) === 1)

  corpus.forEach((record) => {
    const text = normalizeCorpusText(record.body_core || record.body_clean)
    if (!text) return

    corpusTerms(record.retrieval_keywords).forEach((term) => {
      const normalizedTerm = normalizeCorpusText(term)
      const occurrences = countOccurrences(text, normalizedTerm)
      if (!occurrences) return

      const current = metrics.get(term) || {
        label: term,
        termFrequency: 0,
        recordIds: new Set()
      }

      current.termFrequency += occurrences
      current.recordIds.add(String(record.record_id || '未知记录'))
      metrics.set(term, current)
    })
  })

  const ranked = [...metrics.values()]
    .map((item) => ({
      ...item,
      recordCount: item.recordIds.size,
      score: item.termFrequency * (1 + Math.log1p(item.recordIds.size))
    }))
    .filter((item) => item.recordCount >= 2)
    .sort((left, right) => (
      right.score - left.score ||
      right.recordCount - left.recordCount ||
      right.termFrequency - left.termFrequency ||
      left.label.localeCompare(right.label, 'zh-CN')
    ))
    .slice(0, Math.max(0, Number(maxWords) || 0))

  const maximumScore = ranked[0]?.score || 1
  const minimumScore = ranked.at(-1)?.score || maximumScore
  const scoreRange = Math.max(maximumScore - minimumScore, 0.0001)

  return ranked.map((item, index) => {
    const normalized = ranked.length === 1
      ? 1
      : (item.score - minimumScore) / scoreRange

    return {
      label: item.label,
      score: Number(item.score.toFixed(4)),
      termFrequency: item.termFrequency,
      recordCount: item.recordCount,
      size: Math.round(14 + Math.sqrt(normalized) * 36),
      color: WORD_CLOUD_PALETTE[index % WORD_CLOUD_PALETTE.length],
      weight: normalized > 0.52 ? 700 : normalized > 0.16 ? 600 : 500
    }
  })
}

export function layoutCorpusKeywordCloud(words) {
  const width = 1000
  const height = 620
  const centerX = width / 2
  const centerY = height / 2 + 8
  const placed = []
  const source = (Array.isArray(words) ? words : [])
    .map((word, index) => ({
      ...word,
      originalIndex: index,
      layoutSeed: hashString(`${word.label}:${word.score}:${index}`)
    }))
    .sort((left, right) => right.size - left.size || left.layoutSeed - right.layoutSeed)

  function isInsideEnvelope(box) {
    const right = box.x + box.width
    const bottom = box.y + box.height
    return box.x >= 132 && right <= 868 && box.y >= 72 && bottom <= 548
  }

  source.forEach((word, placementIndex) => {
    const random = createSeededRandom(word.layoutSeed ^ 0x51f15e5d)
    const plannedRotation = 0
    const approximateWidth = Math.min(
      210,
      Math.max(34, word.label.length * word.size * (word.label.length > 4 ? 0.86 : 0.98))
    )
    const baseWidth = approximateWidth + 12
    const baseHeight = word.size * 1.38 + 8
    const rotationRadians = Math.abs(plannedRotation) * Math.PI / 180
    const boxWidth =
      Math.abs(baseWidth * Math.cos(rotationRadians)) +
      Math.abs(baseHeight * Math.sin(rotationRadians))
    const boxHeight =
      Math.abs(baseWidth * Math.sin(rotationRadians)) +
      Math.abs(baseHeight * Math.cos(rotationRadians))
    let selectedBox = null
    let selectedRotation = 0

    for (let attempt = 0; attempt < 900; attempt += 1) {
      const xCenter = centerX + (random() - 0.5) * 690
      const yCenter = centerY + (random() - 0.5) * 420
      const candidate = {
        x: xCenter - boxWidth / 2,
        y: yCenter - boxHeight / 2,
        width: boxWidth,
        height: boxHeight
      }
      if (!isInsideEnvelope(candidate)) continue
      if (placed.some((item) => boxesOverlap(candidate, item.box, word.size > 30 ? 6 : 2))) {
        continue
      }

      selectedBox = candidate
      selectedRotation = plannedRotation
      break
    }

    if (!selectedBox) {
      const columnCount = 70
      const rowCount = 40
      const startColumn = word.layoutSeed % columnCount
      const startRow = (word.layoutSeed >>> 8) % rowCount

      for (let rowOffset = 0; rowOffset < rowCount && !selectedBox; rowOffset += 1) {
        for (let columnOffset = 0; columnOffset < columnCount; columnOffset += 1) {
          const column = (startColumn + columnOffset) % columnCount
          const row = (startRow + rowOffset) % rowCount
          const candidate = {
            x: 58 + column * 12,
            y: 54 + row * 12,
            width: boxWidth,
            height: boxHeight
          }
          if (!isInsideEnvelope(candidate)) continue
          if (placed.some((item) => boxesOverlap(candidate, item.box, 1))) continue
          selectedBox = candidate
          selectedRotation = plannedRotation
          break
        }
      }
    }

    if (!selectedBox) {
      const columns = 12
      const fallbackX = 76 + (placementIndex % columns) * 72
      const fallbackY = 66 + Math.floor(placementIndex / columns) * 78
      selectedBox = {
        x: Math.min(fallbackX, 930 - boxWidth),
        y: Math.min(fallbackY, 556 - boxHeight),
        width: boxWidth,
        height: boxHeight
      }
      selectedRotation = 0
    }

    placed.push({
      word,
      box: selectedBox,
      rotation: selectedRotation
    })
  })

  return placed
    .sort((left, right) => left.word.originalIndex - right.word.originalIndex)
    .map(({ word, box, rotation }) => ({
      ...word,
      left: Number((((box.x + box.width / 2) / width) * 100).toFixed(3)),
      top: Number((((box.y + box.height / 2) / height) * 100).toFixed(3)),
      rotation
    }))
}

export function selectEmotionEvidenceExamples(examples, emotionKey, limit = 9) {
  if (!emotionKey) return []
  return (Array.isArray(examples) ? examples : [])
    .filter((item) => item?.emotion_key === emotionKey && item?.text)
    .sort((left, right) => {
      const reviewDifference = Number(Boolean(left.needs_review)) - Number(Boolean(right.needs_review))
      if (reviewDifference) return reviewDifference

      const confidenceDifference =
        boundedRatio(right.confidence) - boundedRatio(left.confidence)
      if (confidenceDifference) return confidenceDifference

      const lengthDifference = String(left.text).length - String(right.text).length
      if (lengthDifference) return lengthDifference

      return String(left.record_id || '').localeCompare(String(right.record_id || ''))
    })
    .slice(0, Math.max(0, Number(limit) || 0))
}

function sortEvidenceExamples(examples) {
  return [...examples].sort((left, right) => {
    const reviewDifference = Number(Boolean(left.needs_review)) - Number(Boolean(right.needs_review))
    if (reviewDifference) return reviewDifference

    const confidenceDifference =
      boundedRatio(right.confidence) - boundedRatio(left.confidence)
    if (confidenceDifference) return confidenceDifference

    const lengthDifference = String(left.text).length - String(right.text).length
    if (lengthDifference) return lengthDifference

    return String(left.record_id || '').localeCompare(String(right.record_id || ''))
  })
}

export function selectValenceEvidenceExamples(examples, valenceKey, limit = 9) {
  if (!valenceKey) return []
  return sortEvidenceExamples(
    (Array.isArray(examples) ? examples : [])
      .filter((item) => item?.valence === valenceKey && item?.text)
  ).slice(0, Math.max(0, Number(limit) || 0))
}

export function selectCooccurrenceEvidenceExamples(
  examples,
  leftKey,
  rightKey,
  limit = 9
) {
  if (!leftKey || !rightKey) return []
  const source = (Array.isArray(examples) ? examples : [])
    .filter((item) => item?.text && [leftKey, rightKey].includes(item.emotion_key))
  const emotionsByRecord = new Map()

  source.forEach((item) => {
    const recordId = String(item.record_id || '')
    if (!emotionsByRecord.has(recordId)) emotionsByRecord.set(recordId, new Set())
    emotionsByRecord.get(recordId).add(item.emotion_key)
  })

  const cooccurringRecordIds = new Set(
    [...emotionsByRecord.entries()]
      .filter(([, keys]) => keys.has(leftKey) && keys.has(rightKey))
      .map(([recordId]) => recordId)
  )
  const preferred = sortEvidenceExamples(
    source.filter((item) => cooccurringRecordIds.has(String(item.record_id || '')))
  )
  const fallback = sortEvidenceExamples(
    source.filter((item) => !cooccurringRecordIds.has(String(item.record_id || '')))
  )
  const unique = []
  const seen = new Set()

  for (const item of [...preferred, ...fallback]) {
    const identity = `${item.record_id}-${item.text}`
    if (seen.has(identity)) continue
    seen.add(identity)
    unique.push(item)
    if (unique.length >= Math.max(0, Number(limit) || 0)) break
  }
  return unique
}

function keywordSnippet(text, keyword, radius = 58) {
  const source = String(text || '').replace(/\s+/g, ' ').trim()
  const index = source.indexOf(keyword)
  if (index < 0) return ''
  const start = Math.max(0, index - radius)
  const end = Math.min(source.length, index + keyword.length + radius)
  return `${start > 0 ? '…' : ''}${source.slice(start, end)}${end < source.length ? '…' : ''}`
}

export function selectKeywordEvidenceExamples(records, keyword, limit = 9) {
  if (!keyword) return []
  return (Array.isArray(records) ? records : [])
    .map((record) => {
      const text = String(record?.body_core || record?.body_clean || '')
      const snippet = keywordSnippet(text, keyword)
      if (!snippet) return null
      return {
        record_id: String(record.record_id || ''),
        year: String(record.year_normalized || ''),
        emotion_key: `keyword:${keyword}`,
        emotion_label: `关键词：${keyword}`,
        text: snippet,
        trigger_terms: [keyword],
        confidence: null,
        valence: 'neutral',
        needs_review: false
      }
    })
    .filter(Boolean)
    .sort((left, right) => (
      left.text.length - right.text.length ||
      left.record_id.localeCompare(right.record_id)
    ))
    .slice(0, Math.max(0, Number(limit) || 0))
}

export function selectTypicalEmotionEvidence(examples, emotionKey) {
  return selectEmotionEvidenceExamples(examples, emotionKey, 1)[0] || null
}

export function buildEmotionKeywordCloud(examples, maxWords = 28) {
  const metrics = new Map()
  const sourceItems = Array.isArray(examples) ? examples : []

  sourceItems.forEach((example) => {
    const text = String(example?.text || '')
    const confidence = boundedRatio(example?.confidence)
    const terms = [...new Set(
      (Array.isArray(example?.trigger_terms) ? example.trigger_terms : [])
        .map(cleanTerm)
        .filter((term) => term.length >= 2 && text.includes(term))
    )]

    terms.forEach((term) => {
      const occurrences = countOccurrences(text, term)
      if (!occurrences) return

      const current = metrics.get(term) || {
        label: term,
        termFrequency: 0,
        segmentFrequency: 0,
        recordIds: new Set(),
        score: 0
      }

      current.termFrequency += occurrences
      current.segmentFrequency += 1
      current.recordIds.add(String(example.record_id || '未知记录'))
      current.score += occurrences * confidence
      metrics.set(term, current)
    })
  })

  const ranked = [...metrics.values()]
    .sort((left, right) => (
      right.score - left.score ||
      right.segmentFrequency - left.segmentFrequency ||
      right.termFrequency - left.termFrequency ||
      left.label.localeCompare(right.label, 'zh-CN')
    ))
    .slice(0, Math.max(0, Number(maxWords) || 0))

  const maximumScore = ranked[0]?.score || 1
  const minimumScore = ranked.at(-1)?.score || maximumScore
  const scoreRange = Math.max(maximumScore - minimumScore, 0.0001)

  return ranked.map((item, index) => {
    const normalized = ranked.length === 1
      ? 1
      : (item.score - minimumScore) / scoreRange

    return {
      label: item.label,
      score: Number(item.score.toFixed(4)),
      termFrequency: item.termFrequency,
      segmentFrequency: item.segmentFrequency,
      recordCount: item.recordIds.size,
      size: Math.round(18 + normalized * 30),
      color: WORD_CLOUD_PALETTE[index % WORD_CLOUD_PALETTE.length],
      weight: normalized > 0.55 ? 700 : normalized > 0.2 ? 600 : 500
    }
  })
}
