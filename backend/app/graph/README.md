# Qiaopi Knowledge Graph Architecture

This directory contains the isolated knowledge graph layer. Step H1 implements
the SQLite foundation: deterministic node/edge table creation and a rebuildable
graph builder. Step H1.1 adds logical edge deduplication, amount node
deduplication, and evidence aggregation. Step H2 implements read-only Graph API
endpoints backed by the SQLite KG tables. Step H3 adds a standalone `kg-viewer/`
app for graph preview and demo recording. It does not implement Neo4j
integration, graph analytics algorithms, or official integration into
`frontend/`.

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

H3 implementation status:

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
- Standalone `kg-viewer/`.
- Vue 3, Vite, Element Plus, ECharts, and Axios viewer stack.
- Graph stats display.
- Record graph display.
- Overview graph display.
- Place flow table.
- Node neighbor display.
- Date nodes prefer `date_standard` labels such as `1933.9.11` and fall back
  to `year_normalized` only when no standard display date is available.

Not implemented yet:

- Neo4j import/export.
- Advanced graph analytics.
- Official integration into `frontend/`.

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

## 6. Relationship with the standalone kg-viewer

H3 creates a standalone viewer at:

```text
kg-viewer/
```

The viewer:

- Use Vue 3, Vite, Element Plus, and ECharts.
- Match the existing frontend's data-workbench layout style.
- Use a left sidebar, top header, and card-based main area.
- Call `/api/graph/*` endpoints.
- Support graph preview and demo recording.
- Remain fully independent from `frontend/`.
- Not import files from `frontend/`.
- Not modify `frontend/`.

`frontend/` remains untouched. `kg-viewer/` visually matches the existing
system style but does not import from `frontend/`.

## 7. Date Normalization

Step Date-1 adds deterministic normalized date fields to
`qiaopi_text_records` and `qiaopi_metadata_records`:

```text
date_standard
date_year
date_month
date_day
date_precision
date_calendar
date_parse_confidence
date_parse_note
```

The graph builder preserves raw `date_text` and `year_normalized` values in
`properties_json`. For `HAS_DATE` edges from text records, it uses
`date_standard` as the date node label and node ID when available. If
`date_standard` is empty but a year is available, it falls back to the year.
Examples:

```text
date:1933.9.11
date:1969
```

Supported source formats include western dates, ROC dates such as
`民国22年9月11日`, Chinese month/day numerals, and traditional expressions with
explicit western years such as `癸(1933)九月十一日` or
`辛（1911）阳月初十日`. ROC dates use `western_year = roc_year + 1911`.

`date_precision` is one of `day`, `month`, `year`, `month_day_no_year`, or
`unknown`. `date_calendar` is one of `gregorian`, `roc`,
`traditional_lunar_text`, or `unknown`. `date_parse_confidence` records the
deterministic parser confidence.

Traditional Chinese month/day expressions are normalized for display only.
They are not converted to exact Gregorian lunar-calendar dates.

## 8. Kinship Normalization

The graph builder normalizes common qiaopi kinship terms before creating
`person` nodes. Matching is longest-first and supports embedded relationship
phrases inside longer sender or recipient labels, such as `黄氏吾妻`,
`荆妻李氏`, `潮汕祖母大人`, or `鹤巢乡李再赐胞兄`. This avoids duplicate
nodes such as `person:慈亲` and `person:母亲`; source labels are kept in
`properties_json.raw_labels`, and original `evidence_text` remains on edges.

Current normalized kinship types:

| Raw terms | Node label | `kinship_type` |
| --- | --- | --- |
| `吾妻`, `贤妻`, `荆妻`, `内妻`, `妻室`, `内人`, `拙荆`, `爱妻` | `妻子` | `wife` |
| `慈亲`, `慈母`, `母亲`, `家慈`, `母亲大人` | `母亲` | `mother` |
| `严亲`, `严父`, `父亲`, `家严`, `父亲大人` | `父亲` | `father` |
| `双亲`, `父母`, `二亲` | `双亲` | `parents` |
| `岳父母`, `岳双亲` | `岳父母` | `parents_in_law` |
| `外祖父母` | `外祖父母` | `maternal_grandparents` |
| `祖父母` | `祖父母` | `grandparents` |
| `岳祖父母` | `岳祖父母` | `grandparents_in_law` |
| `祖母`, `祖慈` | `祖母` | `grandmother` |
| `祖父` | `祖父` | `grandfather` |
| `外祖母` | `外祖母` | `maternal_grandmother` |
| `外祖父` | `外祖父` | `maternal_grandfather` |
| `岳母`, `岳慈亲` | `岳母` | `mother_in_law` |
| `岳父` | `岳父` | `father_in_law` |
| `岳祖母` | `岳祖母` | `grandmother_in_law` |
| `岳祖父` | `岳祖父` | `grandfather_in_law` |
| `兄长`, `胞兄`, `吾兄`, `兄台`, `姻兄`, `表兄`, `大兄` | `兄长` | `elder_brother` |
| `胞弟`, `吾弟`, `贤弟`, `大弟`, `姻弟`, `英弟`, `下蓬英弟`, `逞大弟` | `弟弟` | `younger_brother` |
| `吾姊`, `姻姊`, `大姊`, `姊`, `姐` | `姐姐` | `elder_sister` |
| `胞妹`, `贤妹`, `妹` | `妹妹` | `younger_sister` |
| `侄`, `侄儿`, `贤侄`, `族侄`, `宗侄`, `侄台`, `吾侄`, `内侄`, `两侄` | `侄子` | `nephew` |
| `姨母`, `细姨母` | `姨母` | `aunt_maternal` |
| `嫂`, `嫂嫂`, `表嫂`, `大嫂` | `嫂子` | `sister_in_law` |
| `女儿` | `女儿` | `daughter` |
| `男`, `儿`, `孩儿` | `儿子` | `son` |
| `叔`, `叔父` | `叔父` | `uncle` |

`男` is normalized to `儿子` only in qiaopi self-reference or signature
contexts. Ordinary named-person contexts are not treated as `son`. `氏` alone
and `先生` are not kinship terms. `双亲` remains `parents` and is not collapsed
to `mother`. In-law parent and grandparent terms stay separate from blood
parent and grandparent nodes: `岳慈亲` maps to `岳母`, and `岳祖母` maps to
`岳祖母`, not `母亲` or `祖母`.

Stable collective kinship terms remain collective nodes rather than being
split. For example, `外祖父母` creates `person:外祖父母`, while `岳双亲` creates
`person:岳父母`; both carry `is_collective_kinship`, `member_labels`, and
`member_kinship_types` metadata. Parallel recipient labels can still contribute
to more than one `person` node. For example, `岳祖母、岳慈亲` creates edges to
both `person:岳祖母` and `person:岳母`, and mixed affinal sibling labels such as
`妙姿姻姊、家国姻弟` create edges to both `person:姐姐` and `person:弟弟`. The
same original raw label is preserved in each target node's `raw_labels`, and the
same source `evidence_text` remains on each edge.

Every `person` node now carries these properties when available:

```text
person_kind
kinship_type
raw_labels
normalization_note
confidence
needs_review
detected_terms
is_collective_kinship
member_labels
member_kinship_types
```

`person_kind` is `kinship_term` for normalized relationship terms,
`named_person` for concrete names such as `丁南`, and `unknown` only for
unclear nodes that still need rule review. Named people use
`kinship_type = none`.

Known or suspected kinship terms that do not yet have a normalization rule are
returned from `build_knowledge_graph()` in `kinship_needs_review`, grouped by
raw label with counts and source samples.

The build stats include `kinship_coverage` so each text record can be checked
for whether it has at least one kinship term. The standalone audit command is:

```text
python -m app.graph.audit_kinship_coverage
```

It prints total person nodes, `named_person` / `kinship_term` / `unknown`
counts, kinship edge distribution, record kinship coverage, top raw labels by
`kinship_type`, and possible remaining unknown samples.

## 9. Planned node types

| Node type | Meaning | Source table | Example | Can be used as RAG evidence? |
| --- | --- | --- | --- | --- |
| `record` | A 213-record full-text qiaopi item. | `qiaopi_text_records` | `CSQP-SFHC-TEXT-017` | Yes, when the record has full text and evidence-backed retrieval units. |
| `metadata_record` | A catalog-only or catalog-linked metadata item from the 50064-record archive layer. | `qiaopi_metadata_records` | `CSQP-META-001389` | No. Catalog metadata is not full-text evidence. |
| `person` | A sender, recipient, kinship expression, or mentioned person. | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_entity_mentions` | `母亲`, `夏碧粧` | No by itself. It can participate in explanation only through supporting full-text evidence. |
| `place` | An origin, destination, country/region, or mentioned place. | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_place_mentions` | `新加坡`, `广东潮安` | No by itself. It can participate in explanation only through supporting full-text evidence. |
| `amount` | A remittance amount or amount mention. | `qiaopi_amount_mentions` | `洋银肆元` | No by itself. It can support explanation when connected to full-text evidence. |
| `date` | A normalized display date or normalized year. | `qiaopi_text_records`, `qiaopi_metadata_records` | `1933.9.11`, `1969` | No by itself. It can support explanation when connected to full-text evidence. |
| `theme` | A controlled or derived topic label. | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_evidence_spans` | `theme_remittance`, `theme_family_affection` | No by itself. It can support explanation when grounded in full-text evidence. |
| `evidence` | A full-text evidence span from a qiaopi record. | `qiaopi_evidence_spans` | `兹寄批局，带去洋银肆元，至照查收，以安家计。` | Yes, only when derived from a 213 full-text record. |

## 10. Planned edge types

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
| `HAS_DATE` | `record` or `metadata_record` | `date` | `qiaopi_text_records`, `qiaopi_metadata_records` | Preserve raw `date_text` in properties and prefer `date_standard` for the node label. | `CSQP-SFHC-TEXT-017` `HAS_DATE` `1933.9.11` |
| `HAS_THEME` | `record`, `metadata_record`, or `evidence` | `theme` | `qiaopi_text_records`, `qiaopi_metadata_records`, `qiaopi_evidence_spans` | Preserve when the theme is assigned from a full-text span; omit for catalog-only themes. | `CSQP-SFHC-TEXT-017` `HAS_THEME` `theme_remittance` |
| `SUPPORTED_BY` | `person`, `place`, `amount`, `date`, `theme`, or `record` | `evidence` | `qiaopi_evidence_spans` | Yes. This edge exists to make support explicit. | `洋银肆元` `SUPPORTED_BY` remittance evidence span |
| `LINKED_TO_METADATA` | `record` | `metadata_record` | `qiaopi_text_metadata_links`, `qiaopi_text_metadata_link_candidates` | No. Preserve link method and confidence in properties instead. | `CSQP-SFHC-TEXT-017` `LINKED_TO_METADATA` `CSQP-META-001389` |

Metadata-derived edges can support browsing and visualization. They must not be
presented as full-text evidence unless linked back to a full-text `record` or
`evidence` node.

## 11. Evidence-grounded graph design

The graph should be evidence-grounded where possible.

Design rules:

- Prefer edges derived from explicit full-text evidence spans.
- Preserve `record_id`, `evidence_text`, `source_table`, `source_id`,
  `confidence`, and `properties_json` for important edges.
- Treat metadata-derived nodes and edges as catalog context.
- Keep metadata-only catalog context separate from full-text evidence.
- Use deterministic normalization for labels, node IDs, and edge IDs.
- Use `date_standard` for date labels when available; fall back to year only.
- Normalize configured kinship aliases to standard `person` nodes while keeping
  original terms in `raw_labels`.
- Store extraction details in `properties_json` instead of adding unstable
  top-level fields.
- Surface confidence and source information in graph APIs so the viewer can
  distinguish full-text evidence from catalog-only relationships.

## 12. Planned build pipeline

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

## 13. Graph API endpoints

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

## 14. Future development stages

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
   ECharts. Completed in H3.
11. Use the graph viewer for preview and demo recording while keeping it
    independent from `frontend/`. Completed in H3.
