const valenceKeys = ['positive', 'neutral', 'negative', 'mixed']

export const emptyEmotionAnalysis = Object.freeze({
  total_records: 0,
  analyzed_records: 0,
  analyzed_segments: 0,
  multi_label_records: 0,
  mixed_valence_records: 0,
  low_confidence_records: 0,
  dominant_emotion_key: '',
  dominant_emotion_label: '暂无',
  label_distribution: [],
  valence_distribution: [],
  cooccurrence: [],
  time_trend: [],
  evidence_examples: [],
  model: {
    engine: 'python_compatible_fallback',
    model_version: 'unavailable',
    torch_available: false,
    device: 'cpu',
    classifier_type: '',
    label_count: 0,
    threshold: 0,
    calibrated: false,
    methodology: '',
    limitations: ''
  },
  warnings: []
})

function finiteNumber(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function boundedRatio(value) {
  return Math.min(1, Math.max(0, finiteNumber(value)))
}

export function normalizeEmotionAnalysis(payload) {
  const source = payload && typeof payload === 'object' ? payload : {}
  const valenceByKey = new Map(
    (Array.isArray(source.valence_distribution) ? source.valence_distribution : [])
      .filter((item) => item && valenceKeys.includes(item.key))
      .map((item) => [item.key, item])
  )

  return {
    ...emptyEmotionAnalysis,
    ...source,
    total_records: Math.max(0, finiteNumber(source.total_records)),
    analyzed_records: Math.max(0, finiteNumber(source.analyzed_records)),
    analyzed_segments: Math.max(0, finiteNumber(source.analyzed_segments)),
    multi_label_records: Math.max(0, finiteNumber(source.multi_label_records)),
    mixed_valence_records: Math.max(0, finiteNumber(source.mixed_valence_records)),
    low_confidence_records: Math.max(0, finiteNumber(source.low_confidence_records)),
    label_distribution: (Array.isArray(source.label_distribution) ? source.label_distribution : [])
      .map((item) => ({
        ...item,
        record_count: Math.max(0, finiteNumber(item?.record_count)),
        segment_count: Math.max(0, finiteNumber(item?.segment_count)),
        ratio: boundedRatio(item?.ratio),
        average_confidence: boundedRatio(item?.average_confidence)
      }))
      .sort((left, right) => right.record_count - left.record_count),
    valence_distribution: valenceKeys.map((key) => {
      const item = valenceByKey.get(key) || {}
      return {
        key,
        label: item.label || key,
        record_count: Math.max(0, finiteNumber(item.record_count)),
        ratio: boundedRatio(item.ratio)
      }
    }),
    cooccurrence: Array.isArray(source.cooccurrence) ? source.cooccurrence : [],
    time_trend: Array.isArray(source.time_trend) ? source.time_trend : [],
    evidence_examples: Array.isArray(source.evidence_examples) ? source.evidence_examples : [],
    warnings: Array.isArray(source.warnings) ? source.warnings : [],
    model: {
      ...emptyEmotionAnalysis.model,
      ...(source.model || {})
    }
  }
}

export function percentText(value, digits = 0) {
  return `${(boundedRatio(value) * 100).toFixed(digits)}%`
}

