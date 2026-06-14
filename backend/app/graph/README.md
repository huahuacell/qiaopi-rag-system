# Qiaopi Knowledge Graph Architecture

This directory contains the isolated knowledge graph layer. Step H1 implements
the SQLite foundation: deterministic node/edge table creation and a rebuildable
graph builder. Step H1.1 adds logical edge deduplication, amount node
deduplication, and evidence aggregation. Step H2 implements read-only Graph API
endpoints backed by the SQLite KG tables. It does not implement Neo4j
integration, graph analytics algorithms, frontend integration, or a viewer.

## 1. Purpose

The knowledge graph will be a separate derived layer for relationship modeling,
visualization, and explanation across qiaopi records. It will make people,
places, dates, amounts, themes, catalog records, and supporting evidence easier
to inspect without changing the existing search, RAG, Qwen generation,
validation, semantic search, or metadata catalog behavior.

The graph should answer questions such as:

- Which people, places, dates, amounts, and themes are connected to a record?
- Which records mention the same person, place, amount pattern, or theme?
- Which relationships are supported by full-text evidence spans?
- Which full-text records are linked to catalog-only metadata records?

H2 implementation status:

Implemented:

- SQLite KG tables: `qiaopi_kg_nodes` and `qiaopi_kg_edges`.
- Deterministic `python -m app.ingestion.build_knowledge_graph` command.
- Evidence-grounded node and edge construction from existing SQLite tables.
- Logical edge deduplication by `record_id`, `source_node_id`,
  `target_node_id`, and `edge_type`.
- Amount node deduplication by record, normalized amount, currency, and raw
  amount form.
- Evidence aggregation into `properties_json` for duplicate facts from multiple
  extraction sources.
- Graph API endpoints based on SQLite KG tables.
- Record-centered graph query.
- Node neighbor query.
- Limited graph overview query.
- Place flow statistics.

Not implemented yet:

- `kg-viewer/`.
- Neo4j import/export.
- Advanced graph analytics.

## 2. Architectural boundaries

Graph logic must remain isolated from the existing backend modules.

Allowed future graph ownership:

```text
backend/app/graph/
backend/app/api/graph.py
backend/app/services/graph_service.py
backend/app/ingestion/build_knowledge_graph.py
backend/app/ingestion/export_neo4j_graph.py
backend/app/ingestion/import_neo4j_graph.py
```

Graph logic must not be mixed into:

```text
backend/app/search/
backend/app/rag/
backend/app/llm/
backend/app/validation/
backend/app/metadata/
```

The planned graph module layout is:

```text
backend/app/graph/
├── __init__.py
├── README.md
├── graph_builder.py
├── graph_repository.py
├── normalizers.py
├── neo4j_exporter.py
├── neo4j_importer.py
└── graph_analytics.py

backend/app/api/graph.py
backend/app/services/graph_service.py
backend/app/ingestion/build_knowledge_graph.py
backend/app/ingestion/export_neo4j_graph.py
backend/app/ingestion/import_neo4j_graph.py
```

In H2, `__init__.py`, `README.md`, `graph_builder.py`,
`graph_repository.py`, `normalizers.py`,
`backend/app/ingestion/build_knowledge_graph.py`,
`backend/app/api/graph.py`, and `backend/app/services/graph_service.py` are
implemented. Neo4j files and analytics modules remain planned only.

## 3. Relationship with SQLite

SQLite remains the source of truth. The graph is a derived projection built from
existing SQLite tables and can be rebuilt when the source data changes.

Existing source tables include:

- `qiaopi_text_records`
- `qiaopi_metadata_records`
- `qiaopi_text_metadata_links`
- `qiaopi_text_metadata_link_candidates`
- `qiaopi_amount_mentions`
- `qiaopi_entity_mentions`
- `qiaopi_place_mentions`
- `qiaopi_evidence_spans`

H1 implements these derived SQLite graph tables:

### `qiaopi_kg_nodes`

| Field | Purpose |
| --- | --- |
| `node_id` | Stable graph node identifier. |
| `node_type` | One of the planned node types such as `record`, `person`, or `place`. |
| `label` | Display label. |
| `normalized_label` | Normalized label for matching and deduplication. |
| `record_id` | Full-text record scope when the node is record-derived. |
| `source_table` | SQLite table that produced the node. |
| `source_id` | Source row identifier or stable source field identifier. |
| `properties_json` | Extra non-contract attributes as JSON. |
| `created_at` | Creation timestamp for the derived graph row. |

### `qiaopi_kg_edges`

| Field | Purpose |
| --- | --- |
| `edge_id` | Stable graph edge identifier. |
| `source_node_id` | Source graph node. |
| `target_node_id` | Target graph node. |
| `edge_type` | One of the planned edge types such as `SENT_BY` or `HAS_AMOUNT`. |
| `record_id` | Full-text record scope when the edge is record-derived. |
| `evidence_text` | Supporting full-text span when available. |
| `source_table` | SQLite table that produced the edge. |
| `source_id` | Source row identifier or stable source field identifier. |
| `weight` | Optional relationship strength for analytics and visualization. |
| `confidence` | Extraction or linking confidence. |
| `properties_json` | Extra non-contract attributes as JSON. |
| `created_at` | Creation timestamp for the derived graph row. |

These tables must be generated from existing SQLite data. They must not become
the primary storage for qiaopi records or catalog metadata.

Duplicate facts from multiple extraction sources are merged before insertion.
For example, repeated `MENTIONS_PLACE` edges from record fields and structured
place mentions become one logical edge. The edge keeps the best row-level
`evidence_text`, maximum confidence, and strongest source in top-level columns,
while preserving all supporting `evidence_texts`, `source_tables`,
`source_ids`, `confidences`, `raw_labels`, and `deduplicated_count` in
`properties_json`.

Duplicate amount mentions for the same record and normalized amount become one
logical `amount` node and one `HAS_AMOUNT` edge where possible. Original raw
forms and supporting evidence texts remain in `properties_json`.

## 4. Relationship with Neo4j

Neo4j is a future derived graph database layer, not a replacement for SQLite.
The planned flow is:

```text
SQLite source tables
-> qiaopi_kg_nodes / qiaopi_kg_edges
-> optional Neo4j export/import
-> graph APIs and visualization
```

Neo4j integration should be optional and reproducible. Exporters/importers should
read from the derived graph tables and preserve provenance fields. They must not
read secrets from code, must not require Neo4j for normal backend startup, and
must not change existing search or generation behavior.

## 5. Relationship with RAG / Qwen generation

The graph is not a RAG replacement and must not alter Qwen generation prompts.

Rules:

- Existing RAG context continues to use full-text retrieval units and evidence
  references.
- Existing Qwen generation continues to use the current RAG and validation
  pipeline.
- Graph APIs may expose relationships and evidence for explanation, but they
  must not inject metadata-only records into RAG context.
- `record` and `evidence` nodes derived from full-text records may support RAG
  explanation.
- `metadata_record` nodes are catalog-level only and must not be treated as
  full-text evidence.
- Metadata-only records must never be inserted into `qiaopi_retrieval_units`,
  `qiaopi_retrieval_units_fts`, the semantic index, RAG context, or Qwen
  generation prompts.

## 6. Relationship with the future standalone kg-viewer

A future standalone viewer may be created at:

```text
kg-viewer/
```

The viewer should:

- Use Vue 3, Vite, Element Plus, and ECharts.
- Match the existing frontend's data-workbench layout style.
- Use a left sidebar, top header, and card-based main area.
- Call `/api/graph/*` endpoints.
- Support graph preview and demo recording.
- Remain fully independent from `frontend/`.
- Not import files from `frontend/`.
- Not modify `frontend/`.

Step H2 does not create `kg-viewer/`.

## 7. Planned node types

| Node type | Meaning | Source table | Example | Can be used as RAG evidence? |
| --- | --- | --- | --- | --- |
| `record` | A 213-record full-text qiaopi item. | `qiaopi_text_records` | `CSQP-SFHC-TEXT-017` | Yes, when the record has full text and evidence-backed retrieval units. |
| `metadata_record` | A catalog-only or catalog-linked metadata item from the 50064-record archive layer. | `qiaopi_metadata_records` | `CSQP-META-001389` | No. Catalog metadata is not full-text evidence. |
| `person` | A sender, recipient, kinship expression, or mentioned person. | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_entity_mentions` | `母亲`, `夏碧粧` | No by itself. It can participate in explanation only through supporting full-text evidence. |
| `place` | An origin, destination, country/region, or mentioned place. | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_place_mentions` | `新加坡`, `广东潮安` | No by itself. It can participate in explanation only through supporting full-text evidence. |
| `amount` | A remittance amount or amount mention. | `qiaopi_amount_mentions` | `洋银肆元` | No by itself. It can support explanation when connected to full-text evidence. |
| `date` | A date expression or normalized year. | `qiaopi_text_records`, `qiaopi_metadata_records` | `癸九月十一日`, `1931` | No by itself. It can support explanation when connected to full-text evidence. |
| `theme` | A controlled or derived topic label. | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_evidence_spans` | `theme_remittance`, `theme_family_affection` | No by itself. It can support explanation when grounded in full-text evidence. |
| `evidence` | A full-text evidence span from a qiaopi record. | `qiaopi_evidence_spans` | `兹寄批局，带去洋银肆元，至照查收，以安家计。` | Yes, only when derived from a 213 full-text record. |

## 8. Planned edge types

Every important edge should eventually preserve these provenance properties:

```text
record_id
evidence_text
source_table
source_id
confidence
properties_json
```

| Edge type | Source node type | Target node type | Source table | Preserve `evidence_text`? | Example |
| --- | --- | --- | --- | --- | --- |
| `SENT_BY` | `record` or `metadata_record` | `person` | `qiaopi_text_records`, `qiaopi_metadata_records` | Preserve when derived from a full-text span; omit for metadata-only catalog fields. | `CSQP-SFHC-TEXT-017` `SENT_BY` `寄批人` |
| `RECEIVED_BY` | `record` or `metadata_record` | `person` | `qiaopi_text_records`, `qiaopi_metadata_records` | Preserve when derived from a full-text span; omit for metadata-only catalog fields. | `CSQP-SFHC-TEXT-017` `RECEIVED_BY` `母亲` |
| `MENTIONS_PERSON` | `record` or `evidence` | `person` | `qiaopi_entity_mentions` | Yes, when the mention row contains or points to source text. | Evidence span `MENTIONS_PERSON` `胞弟` |
| `MENTIONS_PLACE` | `record` or `evidence` | `place` | `qiaopi_place_mentions` | Yes, when the mention row contains or points to source text. | Evidence span `MENTIONS_PLACE` `星洲` |
| `SENT_FROM` | `record` or `metadata_record` | `place` | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_place_mentions` | Preserve when derived from full text; omit for metadata-only catalog fields. | `CSQP-SFHC-TEXT-017` `SENT_FROM` `新加坡` |
| `SENT_TO` | `record` or `metadata_record` | `place` | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_place_mentions` | Preserve when derived from full text; omit for metadata-only catalog fields. | `CSQP-SFHC-TEXT-017` `SENT_TO` `广东侨乡` |
| `HAS_AMOUNT` | `record` or `evidence` | `amount` | `qiaopi_amount_mentions` | Yes. Amount edges should retain the amount sentence or supporting span. | Evidence span `HAS_AMOUNT` `洋银肆元` |
| `HAS_DATE` | `record` or `metadata_record` | `date` | `qiaopi_text_records`, `qiaopi_metadata_records` | Preserve when the date is grounded in full text; omit for metadata-only catalog fields. | `CSQP-SFHC-TEXT-017` `HAS_DATE` `癸九月十一日` |
| `HAS_THEME` | `record`, `metadata_record`, or `evidence` | `theme` | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_evidence_spans` | Preserve when the theme is assigned from a full-text span; omit for catalog-only themes. | `CSQP-SFHC-TEXT-017` `HAS_THEME` `theme_remittance` |
| `SUPPORTED_BY` | `person`, `place`, `amount`, `date`, `theme`, or `record` | `evidence` | `qiaopi_evidence_spans` | Yes. This edge exists to make support explicit. | `洋银肆元` `SUPPORTED_BY` remittance evidence span |
| `LINKED_TO_METADATA` | `record` | `metadata_record` | `qiaopi_text_metadata_links`, `qiaopi_text_metadata_link_candidates` | No. Preserve link method and confidence in properties instead. | `CSQP-SFHC-TEXT-017` `LINKED_TO_METADATA` `CSQP-META-001389` |

Metadata-derived edges can support browsing and visualization. They must not be
presented as full-text evidence unless linked back to a full-text `record` or
`evidence` node.

## 9. Evidence-grounded graph design

The graph should be evidence-grounded where possible.

Design rules:

- Prefer edges derived from explicit full-text evidence spans.
- Preserve `record_id`, `evidence_text`, `source_table`, `source_id`,
  `confidence`, and `properties_json` for important edges.
- Treat metadata-derived nodes and edges as catalog context.
- Keep metadata-only catalog context separate from full-text evidence.
- Use deterministic normalization for labels, node IDs, and edge IDs.
- Store extraction details in `properties_json` instead of adding unstable
  top-level fields.
- Surface confidence and source information in graph APIs so the viewer can
  distinguish full-text evidence from catalog-only relationships.

## 10. Planned build pipeline

The future build pipeline should be deterministic and rebuildable:

1. Read source rows from the existing SQLite database.
2. Normalize person, place, amount, date, and theme labels.
3. Create `record` nodes for full-text records.
4. Create `metadata_record` nodes for catalog records.
5. Create entity nodes from source fields and mention tables.
6. Create `evidence` nodes from full-text evidence spans.
7. Create provenance-rich relationship edges.
8. Link full-text `record` nodes to `metadata_record` nodes using existing link
   tables.
9. Write derived rows to `qiaopi_kg_nodes` and `qiaopi_kg_edges`.
10. Run graph statistics and consistency checks.
11. Optionally export the derived graph tables to Neo4j.

The builder must not call Qwen, create embeddings, modify retrieval units, alter
FTS tables, or change metadata linking behavior.

## 11. Graph API endpoints

H2 implements these read-only APIs over the derived SQLite graph tables:

```text
GET /api/graph/stats
GET /api/graph/record/{record_id}
GET /api/graph/node/{node_id}/neighbors
GET /api/graph/overview
GET /api/graph/flows/places
```

Future analytics endpoints remain planned only:

```text
GET /api/graph/analytics/top-nodes
GET /api/graph/analytics/centrality
```

Endpoint intent:

- `/api/graph/stats`: graph node, edge, type, and provenance counts.
- `/api/graph/record/{record_id}`: subgraph for one full-text record.
- `/api/graph/node/{node_id}/neighbors`: local neighborhood expansion.
- `/api/graph/overview`: small overview graph for landing visualization.
- `/api/graph/flows/places`: origin/destination or mention flow aggregation.
- `/api/graph/analytics/top-nodes`: high-degree or weighted top nodes.
- `/api/graph/analytics/centrality`: planned graph centrality outputs.

The API reads from `qiaopi_kg_nodes` and `qiaopi_kg_edges`. It does not call
Neo4j and does not feed metadata-only records into RAG or Qwen generation.

## 12. Future development stages

1. Finalize graph schema and ID conventions. Completed for the H1 SQLite
   foundation.
2. Implement deterministic normalizers in `backend/app/graph/normalizers.py`.
   Completed for the H1 SQLite foundation.
3. Implement the SQLite graph repository in
   `backend/app/graph/graph_repository.py`.
   Completed for the H1 SQLite foundation.
4. Implement the graph builder in `backend/app/graph/graph_builder.py`.
   Completed for the H1 SQLite foundation.
5. Add ingestion commands to build and validate `qiaopi_kg_nodes` and
   `qiaopi_kg_edges`. Completed for the H1 SQLite foundation.
6. Optimize duplicate fact handling and evidence aggregation. Completed in H1.1.
7. Add read-only graph service and API endpoints. Completed in H2.
8. Add graph analytics over the derived graph tables.
9. Add optional Neo4j exporter/importer.
10. Create the standalone `kg-viewer/` app using Vue 3, Vite, Element Plus, and
   ECharts.
11. Use the graph viewer for preview and demo recording while keeping it
    independent from `frontend/`.
