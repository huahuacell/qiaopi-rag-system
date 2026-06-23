import {
  getDisplayLabel,
  getRelationDisplay,
  getSearchableKeywords,
  getThemeDisplay,
  getVisualNodeType,
  normalizeThemeCode
} from './graphLabelMap.js'

export function decorateGraph(rawGraph = {}) {
  const nodes = (rawGraph.nodes || []).map(decorateNode)
  const nodeIds = new Set(nodes.map((node) => node.id))
  const edges = (rawGraph.edges || [])
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map(decorateEdge)
  return { ...rawGraph, nodes, edges }
}

export function transformGraphForKinshipCommunication(rawGraph = {}, options = {}) {
  const maxNodes = Number(options.maxNodes || 60)
  const decorated = augmentKinshipCommunicationGraph(decorateGraph(rawGraph))
  const degree = countDegree(decorated.edges)
  const evidenceByRecord = evidenceCountsByRecord(rawGraph)

  const ranked = decorated.nodes.map((node) => ({
    ...node,
    importance:
      (degree.get(node.id) || 0) * 4 +
      Number(node.properties?.deduplicated_count || 0) +
      Number(node.properties?.record_ids?.length || 0) * 2 +
      (node.visualType === 'kinship' ? 16 : 0) +
      (node.visualType === 'person' ? 10 : 0) +
      Number(evidenceByRecord.get(node.record_id) || 0)
  }))
  const rankedByType = (type, predicate = () => true) =>
    ranked
      .filter((node) => node.visualType === type && predicate(node))
      .sort((left, right) => right.importance - left.importance)

  const anchorQuotas = kinshipAnchorQuotas(maxNodes)
  const anchors = [
    ...rankedByType('kinship', (node) => node.id.startsWith('kinship:')).slice(
      0,
      anchorQuotas.kinship
    ),
    ...rankedByType('place').slice(0, anchorQuotas.place),
    ...rankedByType('person').slice(0, anchorQuotas.person),
    ...rankedByType('theme').slice(0, anchorQuotas.theme),
    ...rankedByType('amount').slice(0, anchorQuotas.amount)
  ]
  const anchorIds = new Set(anchors.map((node) => node.id))
  const scoredRecords = rankedByType('record')
    .map((node) => {
      const connectedEdges = decorated.edges.filter(
        (edge) =>
          (edge.source === node.id && anchorIds.has(edge.target)) ||
          (edge.target === node.id && anchorIds.has(edge.source))
      )
      const connectedTypes = new Set(
        connectedEdges.map((edge) => {
          const otherId = edge.source === node.id ? edge.target : edge.source
          return decorated.nodes.find((item) => item.id === otherId)?.visualType || ''
        })
      )
      return {
        ...node,
        anchorConnectionCount: connectedEdges.length,
        importance:
          node.importance +
          connectedEdges.length * 10 +
          connectedTypes.size * 8
      }
    })
    .filter((node) => node.anchorConnectionCount >= 2)
    .sort((left, right) => right.importance - left.importance)
  const records = selectRecordsForAnchorCoverage(
    scoredRecords,
    decorated.edges,
    new Set(
      anchors
        .filter((node) => ['kinship', 'place'].includes(node.visualType))
        .map((node) => node.id)
    ),
    Math.max(12, maxNodes - anchors.length)
  )

  const selectedNodes = [...anchors, ...records].slice(0, maxNodes)
  const selectedIds = new Set(selectedNodes.map((node) => node.id))
  const selectedEdges = decorated.edges.filter(
    (edge) => selectedIds.has(edge.source) && selectedIds.has(edge.target)
  )

  const recordRelations = groupEdgesByRecord(selectedEdges)
  const communicationEdges = []
  for (const [recordId, recordEdges] of recordRelations) {
    const senders = recordEdges
      .filter((edge) => edge.rawType === 'SENT_BY')
      .map((edge) => edge.target)
    const recipients = recordEdges
      .filter((edge) =>
        ['RECEIVED_BY', 'KINSHIP_ADDRESS'].includes(edge.rawType)
      )
      .map((edge) => edge.target)
    for (const sender of senders) {
      for (const recipient of recipients) {
        if (sender === recipient) continue
        communicationEdges.push(
          decorateEdge({
            id: `communication:${recordId}:${sender}:${recipient}`,
            source: sender,
            target: recipient,
            type: 'COMMUNICATES_WITH',
            record_id: recordId,
            confidence: 0.95,
            properties: {
              synthetic: true,
              record_ids: [recordId]
            }
          })
        )
      }
    }
  }

  const edges = dedupeEdges([...selectedEdges, ...communicationEdges])
  const connectedIds = new Set()
  for (const edge of edges) {
    connectedIds.add(edge.source)
    connectedIds.add(edge.target)
  }
  const nodes = selectedNodes.filter((node) => connectedIds.has(node.id))

  return {
    nodes,
    edges,
    summary: {
      mode: 'kinship',
      totalNodes: decorated.nodes.length,
      visibleNodes: nodes.length,
      kinshipCount: nodes.filter((node) => node.visualType === 'kinship').length,
      placeCount: nodes.filter((node) => node.visualType === 'place').length
    }
  }
}

export function transformGraphForFlow(rawGraph = {}, placeFlows = [], options = {}) {
  const maxFlows = Number(options.maxFlows || 14)
  const flowRows = (placeFlows || []).filter(
    (flow) => flow.origin_place || flow.destination_place
  )
  const derivedFlows = flowRows.length ? flowRows : derivePlaceFlows(rawGraph)
  const selectedFlows = derivedFlows
    .sort((left, right) => Number(right.count || 0) - Number(left.count || 0))
    .slice(0, maxFlows)

  const nodeMap = new Map()
  const edges = []

  for (const [flowIndex, flow] of selectedFlows.entries()) {
    const origin = normalizeFlowPlaceLabel(flow.origin_place, 'origin')
    const destination = normalizeFlowPlaceLabel(flow.destination_place, 'destination')
    const originId = `flow-origin:${origin}`
    const destinationId = `flow-destination:${destination}`
    const recordIds = unique(flow.record_ids || flow.record_ids_sample || [])

    upsertFlowPlace(nodeMap, {
      id: originId,
      label: origin,
      visualType: 'overseas_place',
      role: 'origin',
      flowIndex,
      recordIds
    })
    upsertFlowPlace(nodeMap, {
      id: destinationId,
      label: destination,
      visualType: 'hometown_place',
      role: 'destination',
      flowIndex,
      recordIds
    })

    const groupId = `flow-group:${origin}:${destination}`
    nodeMap.set(
      groupId,
      decorateNode({
        id: groupId,
        label: `${Number(flow.count || recordIds.length || 1)} 封侨批`,
        type: 'record_group',
        visualType: 'record_group',
        synthetic: true,
        properties: {
          record_ids: recordIds,
          count: Number(flow.count || recordIds.length || 1),
          flow_index: flowIndex,
          origin_place: origin,
          destination_place: destination
        }
      })
    )
    edges.push(
      flowEdge(originId, groupId, 'FLOW_ORIGIN', flow, recordIds),
      flowEdge(groupId, destinationId, 'FLOW_DESTINATION', flow, recordIds)
    )
  }

  return {
    nodes: [...nodeMap.values()],
    edges: dedupeEdges(edges),
    summary: {
      mode: 'flow',
      flowCount: selectedFlows.length,
      recordCount: unique(
        selectedFlows.flatMap((flow) => flow.record_ids || flow.record_ids_sample || [])
      ).length
    }
  }
}

export function transformGraphForRecord(rawGraph = {}) {
  const decorated = decorateGraph(rawGraph)
  return {
    ...decorated,
    nodes: decorated.nodes.map((node) => ({
      ...node,
      visualType:
        node.visualType === 'place' && hasEdge(rawGraph.edges, node.id, 'SENT_FROM')
          ? 'overseas_place'
          : node.visualType === 'place' && hasEdge(rawGraph.edges, node.id, 'SENT_TO')
            ? 'hometown_place'
            : node.visualType
    })),
    summary: { mode: 'record' }
  }
}

export function filterTransformedGraph(graph = {}, filters = {}) {
  const query = String(filters.query || '').trim().toLowerCase()
  const theme = normalizeThemeCode(filters.theme)
  const year = String(filters.year || '').trim()
  const evidenceOnly = Boolean(filters.evidenceOnly)
  const nodes = graph.nodes || []
  const edges = graph.edges || []

  const themeRecordIds = theme
    ? recordIdsForTheme(nodes, edges, theme)
    : new Set()
  const yearRecordIds = year ? recordIdsForYear(nodes, edges, year) : new Set()
  const queryNodeIds = query
    ? new Set(
        nodes
          .filter((node) =>
            (node.searchableKeywords || getSearchableKeywords(node)).some((keyword) =>
              keyword.includes(query)
            )
          )
          .map((node) => node.id)
      )
    : new Set()

  const matchingRecordIds = new Set()
  for (const node of nodes) {
    if (node.record_id && queryNodeIds.has(node.id)) matchingRecordIds.add(node.record_id)
    for (const recordId of node.properties?.record_ids || []) {
      if (queryNodeIds.has(node.id)) matchingRecordIds.add(recordId)
    }
  }
  for (const edge of edges) {
    if (queryNodeIds.has(edge.source) || queryNodeIds.has(edge.target)) {
      if (edge.record_id) matchingRecordIds.add(edge.record_id)
      for (const recordId of edge.properties?.record_ids || []) {
        matchingRecordIds.add(recordId)
      }
    }
  }

  const keepNode = (node) => {
    const recordIds = nodeRecordIds(node)
    if (theme && !intersects(recordIds, themeRecordIds) && node.themeCode !== theme) {
      return false
    }
    if (year && !intersects(recordIds, yearRecordIds) && nodeYear(node) !== year) {
      return false
    }
    if (
      query &&
      !queryNodeIds.has(node.id) &&
      !intersects(recordIds, matchingRecordIds)
    ) {
      return false
    }
    return true
  }

  const filteredNodes = nodes.filter(keepNode)
  const nodeIds = new Set(filteredNodes.map((node) => node.id))
  const filteredEdges = edges.filter((edge) => {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) return false
    if (!evidenceOnly) return true
    return Boolean(
      edge.evidence_text ||
        edge.source_table === 'qiaopi_evidence_spans' ||
        edge.properties?.evidence_texts?.length ||
        edge.confidence >= 0.85
    )
  })

  const connectedIds = new Set()
  for (const edge of filteredEdges) {
    connectedIds.add(edge.source)
    connectedIds.add(edge.target)
  }

  return {
    ...graph,
    nodes: evidenceOnly
      ? filteredNodes.filter(
          (node) => connectedIds.has(node.id) || node.visualType === 'record'
        )
      : filteredNodes,
    edges: filteredEdges
  }
}

export function graphFilterOptions(rawGraph = {}) {
  const decorated = decorateGraph(rawGraph)
  const themes = unique(
    decorated.nodes
      .filter((node) => node.visualType === 'theme')
      .map((node) => node.themeCode)
      .filter(Boolean)
  ).map((value) => ({ value, label: getThemeDisplay(value) }))

  const years = unique(
    decorated.nodes
      .map(nodeYear)
      .filter((value) => /^\d{4}$/.test(value))
  ).sort((left, right) => right.localeCompare(left))

  return { themes, years }
}

export function selectedGraphContext(selected, graph = {}) {
  if (!selected) {
    return {
      recordIds: [],
      themes: [],
      places: [],
      amounts: [],
      evidence: [],
      relatedNodes: []
    }
  }
  const selectedIds = new Set([selected.id, selected.source, selected.target].filter(Boolean))
  const relatedEdges = (graph.edges || []).filter(
    (edge) => selectedIds.has(edge.source) || selectedIds.has(edge.target) || edge.id === selected.id
  )
  const relatedNodeIds = new Set()
  for (const edge of relatedEdges) {
    relatedNodeIds.add(edge.source)
    relatedNodeIds.add(edge.target)
  }
  const relatedNodes = (graph.nodes || []).filter((node) => relatedNodeIds.has(node.id))
  const recordIds = unique([
    selected.record_id,
    ...(selected.properties?.record_ids || []),
    ...relatedNodes.flatMap(nodeRecordIds),
    ...relatedEdges.flatMap((edge) => [
      edge.record_id,
      ...(edge.properties?.record_ids || [])
    ])
  ])

  return {
    recordIds,
    themes: unique(
      relatedNodes
        .filter((node) => node.visualType === 'theme')
        .map((node) => node.displayLabel)
    ),
    places: unique(
      relatedNodes
        .filter((node) =>
          ['place', 'overseas_place', 'hometown_place'].includes(node.visualType)
        )
        .map((node) => node.displayLabel)
    ),
    amounts: unique(
      relatedNodes
        .filter((node) => node.visualType === 'amount')
        .map((node) => node.displayLabel)
    ),
    evidence: uniqueEvidence(
      relatedEdges.flatMap((edge) => {
        const texts = [
          edge.evidence_text,
          ...(edge.properties?.evidence_texts || [])
        ].filter(Boolean)
        return texts.map((text) => ({
          text,
          relation: edge.displayLabel || getRelationDisplay(edge),
          recordId: edge.record_id || recordIds[0] || '',
          sourceTable: edge.source_table || '',
          sourceId: edge.source_id || ''
        }))
      })
    ),
    relatedNodes
  }
}

function decorateNode(node = {}) {
  const visualType = node.visualType || getVisualNodeType(node)
  const displayLabel = getDisplayLabel({ ...node, visualType })
  const themeCode =
    visualType === 'theme'
      ? normalizeThemeCode(node.label || node.normalized_label || node.id)
      : ''
  return {
    ...node,
    visualType,
    displayLabel,
    themeCode,
    rawLabel: node.label || node.normalized_label || '',
    searchableKeywords: getSearchableKeywords({ ...node, visualType, displayLabel })
  }
}

function augmentKinshipCommunicationGraph(graph = {}) {
  const nodeMap = new Map((graph.nodes || []).map((node) => [node.id, node]))
  const edges = [...(graph.edges || [])]
  const edgeKeys = new Set(edges.map((edge) => `${edge.source}|${edge.target}|${edge.rawType}`))

  for (const edge of graph.edges || []) {
    if (!['RECEIVED_BY', 'MENTIONS_PERSON'].includes(edge.rawType)) continue
    const target = nodeMap.get(edge.target)
    if (!target || target.visualType !== 'kinship') continue
    for (const kinship of canonicalKinshipLabels(
      target.properties?.kinship_type || target.displayLabel
    )) {
      upsertCanonicalKinship(nodeMap, edges, edgeKeys, {
        recordId: edge.record_id,
        recordNodeId: edge.source,
        kinship,
        sourceId: edge.source_id,
        sourceTable: edge.source_table
      })
    }
  }

  for (const record of graph.nodes || []) {
    if (record.visualType !== 'record') continue
    const properties = record.properties || {}
    upsertDerivedPerson(nodeMap, edges, edgeKeys, {
      record,
      label: properties.sender_name_clean || properties.sender,
      role: 'SENT_BY'
    })

    const recipientLabel =
      properties.recipient_name_clean || properties.recipient || ''
    const kinshipLabels = canonicalKinshipLabels(recipientLabel)
    if (kinshipLabels.length) {
      for (const kinship of kinshipLabels) {
        upsertCanonicalKinship(nodeMap, edges, edgeKeys, {
          recordId: record.record_id,
          recordNodeId: record.id,
          kinship,
          sourceId: `${record.record_id}:recipient`,
          sourceTable: 'qiaopi_text_records'
        })
      }
    } else {
      upsertDerivedPerson(nodeMap, edges, edgeKeys, {
        record,
        label: recipientLabel,
        role: 'RECEIVED_BY'
      })
    }

    const themeValues = unique([
      properties.main_intent,
      ...String(properties.theme_tags || '')
        .split(/[;,；]/)
        .map((value) => value.trim())
        .filter(Boolean)
    ]).slice(0, 1)
    for (const rawTheme of themeValues) {
      const themeCode = normalizeThemeCode(rawTheme)
      if (!themeCode) continue
      const themeId = `theme:${themeCode}`
      if (!nodeMap.has(themeId)) {
        nodeMap.set(
          themeId,
          decorateNode({
            id: themeId,
            type: 'theme',
            label: rawTheme,
            normalized_label: themeCode,
            synthetic: true,
            properties: { record_ids: [record.record_id] }
          })
        )
      } else {
        mergeNodeRecordId(nodeMap, themeId, record.record_id)
      }
      addDerivedEdge(edges, edgeKeys, {
        source: record.id,
        target: themeId,
        type: 'HAS_THEME',
        recordId: record.record_id,
        confidence: 0.75
      })
    }
  }

  return { ...graph, nodes: [...nodeMap.values()], edges }
}

function upsertDerivedPerson(nodeMap, edges, edgeKeys, { record, label, role }) {
  const cleanLabel = String(label || '').trim()
  if (!cleanLabel) return
  const existingPerson = [...nodeMap.values()].find(
    (node) =>
      node.visualType === 'person' &&
      String(node.displayLabel || '').trim() === cleanLabel
  )
  const personId = existingPerson?.id || `derived-person:${cleanLabel}`
  if (!nodeMap.has(personId)) {
    nodeMap.set(
      personId,
      decorateNode({
        id: personId,
        label: cleanLabel,
        type: 'person',
        visualType: 'person',
        synthetic: true,
        properties: {
          role,
          record_ids: [record.record_id],
          derived_from_record: true
        }
      })
    )
  } else {
    mergeNodeRecordId(nodeMap, personId, record.record_id)
  }
  addDerivedEdge(edges, edgeKeys, {
    source: record.id,
    target: personId,
    type: role,
    recordId: record.record_id,
    confidence: 0.9
  })
}

function upsertCanonicalKinship(
  nodeMap,
  edges,
  edgeKeys,
  { recordId, recordNodeId, kinship, sourceId = '', sourceTable = '' }
) {
  if (!recordId || !recordNodeId || !kinship) return
  const kinshipId = `kinship:${kinship}`
  if (!nodeMap.has(kinshipId)) {
    nodeMap.set(
      kinshipId,
      decorateNode({
        id: kinshipId,
        label: kinship,
        type: 'person',
        visualType: 'kinship',
        synthetic: true,
        source_table: sourceTable,
        source_id: sourceId,
        properties: {
          record_ids: [recordId],
          derived_from_recipient: true
        }
      })
    )
  } else {
    mergeNodeRecordId(nodeMap, kinshipId, recordId)
  }
  addDerivedEdge(edges, edgeKeys, {
    source: recordNodeId,
    target: kinshipId,
    type: 'KINSHIP_ADDRESS',
    recordId,
    confidence: 0.9,
    sourceId,
    sourceTable
  })
}

function mergeNodeRecordId(nodeMap, nodeId, recordId) {
  const existing = nodeMap.get(nodeId)
  if (!existing) return
  const recordIds = unique([...(existing.properties?.record_ids || []), recordId])
  nodeMap.set(nodeId, {
    ...existing,
    properties: {
      ...(existing.properties || {}),
      record_ids: recordIds,
      occurrence_count: recordIds.length
    }
  })
}

function addDerivedEdge(
  edges,
  edgeKeys,
  {
    source,
    target,
    type,
    recordId,
    confidence,
    sourceId = '',
    sourceTable = ''
  }
) {
  const edgeKey = `${source}|${target}|${type}`
  if (edgeKeys.has(edgeKey)) return
  edgeKeys.add(edgeKey)
  edges.push(
    decorateEdge({
      id: `derived:${type}:${recordId}:${target}`,
      source,
      target,
      type,
      record_id: recordId,
      confidence,
      source_id: sourceId,
      source_table: sourceTable,
      synthetic: true,
      properties: {
        record_ids: [recordId],
        derived_from_record: true
      }
    })
  )
}

function decorateEdge(edge = {}) {
  const rawType = edge.rawType || edge.type || edge.label || edge.edge_type || ''
  return {
    ...edge,
    rawType,
    displayLabel: getRelationDisplay(rawType),
    properties: edge.properties || {}
  }
}

function countDegree(edges = []) {
  const degree = new Map()
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1)
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1)
  }
  return degree
}

function evidenceCountsByRecord(rawGraph = {}) {
  const counts = new Map()
  for (const edge of rawGraph.edges || []) {
    if (
      edge.type === 'SUPPORTED_BY' ||
      edge.evidence_text ||
      edge.source_table === 'qiaopi_evidence_spans'
    ) {
      counts.set(edge.record_id, (counts.get(edge.record_id) || 0) + 1)
    }
  }
  return counts
}

function groupEdgesByRecord(edges = []) {
  const groups = new Map()
  for (const edge of edges) {
    if (!edge.record_id) continue
    if (!groups.has(edge.record_id)) groups.set(edge.record_id, [])
    groups.get(edge.record_id).push(edge)
  }
  return groups
}

function dedupeEdges(edges = []) {
  const map = new Map()
  for (const edge of edges) {
    const key = edge.id || `${edge.source}|${edge.target}|${edge.rawType}`
    map.set(key, edge)
  }
  return [...map.values()]
}

function derivePlaceFlows(rawGraph = {}) {
  const nodes = new Map((rawGraph.nodes || []).map((node) => [node.id, node]))
  const records = new Map()
  for (const edge of rawGraph.edges || []) {
    if (!edge.record_id || !['SENT_FROM', 'SENT_TO'].includes(edge.type)) continue
    if (!records.has(edge.record_id)) {
      records.set(edge.record_id, { origins: [], destinations: [] })
    }
    const label = getDisplayLabel(nodes.get(edge.target) || {})
    if (edge.type === 'SENT_FROM') records.get(edge.record_id).origins.push(label)
    if (edge.type === 'SENT_TO') records.get(edge.record_id).destinations.push(label)
  }

  const flows = new Map()
  for (const [recordId, value] of records) {
    for (const origin of value.origins) {
      for (const destination of value.destinations) {
        const key = `${origin}|${destination}`
        if (!flows.has(key)) {
          flows.set(key, {
            origin_place: origin,
            destination_place: destination,
            count: 0,
            record_ids_sample: []
          })
        }
        const flow = flows.get(key)
        flow.count += 1
        flow.record_ids_sample.push(recordId)
      }
    }
  }
  return [...flows.values()]
}

function upsertFlowPlace(nodeMap, value) {
  const existing = nodeMap.get(value.id)
  const recordIds = unique([
    ...(existing?.properties?.record_ids || []),
    ...(value.recordIds || [])
  ])
  nodeMap.set(
    value.id,
    decorateNode({
      ...(existing || {}),
      id: value.id,
      label: value.label,
      type: 'place',
      visualType: value.visualType,
      synthetic: true,
      properties: {
        ...(existing?.properties || {}),
        role: value.role,
        record_ids: recordIds,
        flow_indices: unique([
          ...(existing?.properties?.flow_indices || []),
          value.flowIndex
        ])
      }
    })
  )
}

function flowEdge(source, target, type, flow, recordIds) {
  return decorateEdge({
    id: `${type}:${source}:${target}`,
    source,
    target,
    type,
    confidence: 0.9,
    weight: Number(flow.count || 1),
    synthetic: true,
    properties: {
      count: Number(flow.count || 1),
      record_ids: recordIds,
      origin_place: flow.origin_place || '未知海外地点',
      destination_place: flow.destination_place || '未知侨乡'
    }
  })
}

function recordIdsForTheme(nodes, edges, theme) {
  const themeNodeIds = new Set(
    nodes.filter((node) => node.themeCode === theme).map((node) => node.id)
  )
  const recordIds = new Set()
  for (const edge of edges) {
    if (!themeNodeIds.has(edge.source) && !themeNodeIds.has(edge.target)) continue
    if (edge.record_id) recordIds.add(edge.record_id)
    for (const id of edge.properties?.record_ids || []) recordIds.add(id)
  }
  return recordIds
}

function recordIdsForYear(nodes, edges, year) {
  const dateNodeIds = new Set(
    nodes.filter((node) => nodeYear(node) === year).map((node) => node.id)
  )
  const recordIds = new Set()
  for (const node of nodes) {
    if (node.visualType === 'record' && nodeYear(node) === year && node.record_id) {
      recordIds.add(node.record_id)
    }
  }
  for (const edge of edges) {
    if (!dateNodeIds.has(edge.source) && !dateNodeIds.has(edge.target)) continue
    if (edge.record_id) recordIds.add(edge.record_id)
  }
  return recordIds
}

function nodeYear(node = {}) {
  const value =
    node.properties?.year_normalized ||
    node.properties?.date_year ||
    node.properties?.date_standard ||
    node.displayLabel ||
    ''
  return String(value).match(/\b(18|19|20)\d{2}\b/)?.[0] || ''
}

function nodeRecordIds(node = {}) {
  return unique([
    node.record_id,
    ...(node.properties?.record_ids || []),
    node.visualType === 'record' ? String(node.id || '').replace(/^record:/, '') : ''
  ])
}

function hasEdge(edges = [], nodeId, type) {
  return edges.some((edge) => edge.target === nodeId && edge.type === type)
}

function intersects(values, set) {
  return values.some((value) => set.has(value))
}

function unique(values = []) {
  return [...new Set(values.map((value) => String(value || '').trim()).filter(Boolean))]
}

function uniqueEvidence(values = []) {
  const map = new Map()
  for (const value of values) {
    const key = `${value.recordId}|${value.text}`
    if (value.text && !map.has(key)) map.set(key, value)
  }
  return [...map.values()]
}

function normalizeFlowPlaceLabel(value, role) {
  const label = String(value || '').trim()
  if (role === 'origin') {
    if (!label || /^(未知|不详|未详)$/.test(label)) return '海外地点未详'
    if (/^(海外|外洋|国外|异邦)$/.test(label)) return '海外（地点未详）'
  }
  if (!label || /^(未知|不详|未详)$/.test(label)) return '侨乡地点未详'
  return label
}

function canonicalKinshipLabels(value) {
  const text = String(value || '').trim()
  if (!text) return []
  const labels = []
  let remaining = text
  const rules = [
    ['岳父母', /岳双亲|岳父母|parents_in_law/i],
    ['外祖父母', /外祖父母|maternal_grandparents/i],
    ['祖父母', /祖父母|grandparents$/i],
    ['双亲', /双亲|父母|二亲|parents$/i],
    ['岳母', /岳母|母亲姻亲|mother_in_law/i],
    ['岳父', /岳父|father_in_law/i],
    ['外祖母', /外祖母|maternal_grandmother/i],
    ['外祖父', /外祖父|maternal_grandfather/i],
    ['祖母', /祖母|祖慈|家祖|grandmother/i],
    ['祖父', /祖父|grandfather/i],
    ['母亲', /慈亲|母亲|家慈|慈母|令堂|慈座|mother$/i],
    ['父亲', /严亲|父亲|家严|严父|令尊|father$/i],
    ['妻子', /吾妻|荆妻|贤妻|爱妻|内妻|内人|内助|内子|妻子|wife|spouse/i],
    ['嫂子', /大嫂|嫂子|嫂/],
    ['兄长', /大兄|胞兄|吾兄|贤兄|姻兄|兄台|兄/],
    ['弟弟', /贤弟|胞弟|姻弟|英弟|弟/],
    ['姐姐', /姻姊|姊|姐姐|姐/],
    ['妹妹', /姑妹|妹妹|妹/],
    ['女儿', /女儿|daughter/i],
    ['儿子', /长男|儿子|儿$|男$|son$/i],
    ['媳妇', /媳妇|大媳|媳/],
    ['侄辈', /贤侄|族侄|宗侄|侄儿|内侄|侄|nephew/i],
    ['孙辈', /孙男|孙儿|孙|grandchild/i],
    ['叔伯', /叔父|伯父|叔|伯|uncle/i],
    ['姑母', /姑母|家姑|姑|aunt/i],
    ['姨母', /细姨母|姨母|姨/],
    ['婶母', /二婶|婶/],
    ['舅母', /妗/],
    ['舅父', /舅/]
  ]
  for (const [label, pattern] of rules) {
    if (!pattern.test(remaining)) continue
    labels.push(label)
    remaining = remaining.replace(pattern, ' ')
  }
  return unique(labels)
}

function kinshipAnchorQuotas(maxNodes) {
  return {
    kinship: Math.min(18, Math.max(10, Math.round(maxNodes * 0.25))),
    place: Math.min(10, Math.max(6, Math.round(maxNodes * 0.13))),
    person: Math.min(12, Math.max(7, Math.round(maxNodes * 0.14))),
    theme: Math.min(7, Math.max(4, Math.round(maxNodes * 0.09))),
    amount: Math.min(4, Math.max(0, Math.round(maxNodes * 0.04)))
  }
}

function selectRecordsForAnchorCoverage(records, edges, anchorIds, limit) {
  const selected = []
  const selectedIds = new Set()
  const uncovered = new Set(anchorIds)
  const connectionsByRecord = new Map()

  for (const record of records) {
    const connectedAnchors = new Set()
    for (const edge of edges) {
      if (edge.source === record.id && anchorIds.has(edge.target)) {
        connectedAnchors.add(edge.target)
      }
      if (edge.target === record.id && anchorIds.has(edge.source)) {
        connectedAnchors.add(edge.source)
      }
    }
    connectionsByRecord.set(record.id, connectedAnchors)
  }

  while (selected.length < limit && uncovered.size) {
    const candidate = records
      .filter((record) => !selectedIds.has(record.id))
      .map((record) => {
        const newCoverage = [...(connectionsByRecord.get(record.id) || [])].filter(
          (id) => uncovered.has(id)
        ).length
        return {
          record,
          newCoverage,
          score: newCoverage * 1000 + record.importance
        }
      })
      .filter((item) => item.newCoverage > 0)
      .sort((left, right) => right.score - left.score)[0]
    if (!candidate) break
    selected.push(candidate.record)
    selectedIds.add(candidate.record.id)
    for (const id of connectionsByRecord.get(candidate.record.id) || []) {
      uncovered.delete(id)
    }
  }

  for (const record of records) {
    if (selected.length >= limit) break
    if (selectedIds.has(record.id)) continue
    selected.push(record)
    selectedIds.add(record.id)
  }
  return selected
}
