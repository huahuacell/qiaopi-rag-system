import request from './request'

export async function fetchRecordDetail(recordId) {
  const response = await request.get(`/api/records/${encodeURIComponent(recordId)}`)
  return response.data
}

export async function fetchRecordEntities(recordId) {
  const response = await request.get(`/api/records/${recordId}/entities`)
  return response.data
}

export async function fetchRecordEvidence(recordId) {
  const response = await request.get(`/api/records/${recordId}/evidence`)
  return response.data
}

export async function fetchRecordCorpus(totalRecords, concurrency = 12) {
  const count = Math.max(0, Number(totalRecords) || 0)
  const workerCount = Math.min(Math.max(1, Number(concurrency) || 1), count || 1)
  const recordIds = Array.from(
    { length: count },
    (_, index) => `CSQP-SFHC-TEXT-${String(index + 1).padStart(3, '0')}`
  )
  const records = []
  let cursor = 0

  async function worker() {
    while (cursor < recordIds.length) {
      const recordId = recordIds[cursor]
      cursor += 1

      try {
        const record = await fetchRecordDetail(recordId)
        records.push(record)
      } catch {
        // Keep the corpus usable when an individual record is unavailable.
      }
    }
  }

  await Promise.all(Array.from({ length: workerCount }, worker))
  return records.sort((left, right) =>
    String(left.record_id || '').localeCompare(String(right.record_id || ''))
  )
}

export async function fetchFullTextCorpus(totalRecords, concurrency = 12) {
  const records = await fetchRecordCorpus(totalRecords, concurrency)
  return records.filter(
    (record) =>
      Number(record?.has_full_text) === 1 &&
      Boolean(record?.body_core || record?.body_clean)
  )
}
