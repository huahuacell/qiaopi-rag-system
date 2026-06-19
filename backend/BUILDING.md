# Reproducible Data Build

The complete derived-data pipeline is:

```powershell
cd backend
python -m app.ingestion.build_all --embedding-provider hash
```

By default this command:

1. creates a unique directory under `backend/data/builds/`;
2. preprocesses the 213-record raw workbook;
3. builds a new SQLite database;
4. imports and indexes the 50,064 metadata records;
5. links text and metadata records;
6. builds the SQLite knowledge graph;
7. builds the retrieval-unit vector index;
8. runs database, relationship, vector, and retrieval-regression acceptance;
9. writes `qiaopi_build_manifest.json`;
10. leaves all live assets untouched.

The command never calls a remote embedding API. Supported providers are:

- `hash`: deterministic dependency-free acceptance/smoke index.
- `local`: the configured sentence-transformers model. Install production
  semantic dependencies with `pip install -r requirements-semantic.txt`.

There is no implicit `local` to `hash` fallback. Hash must be selected
explicitly, is recorded as `semantic_quality: test_hash`, and cannot pass
production semantic retrieval acceptance.

For real semantic retrieval, use `local` or a configured production provider.
The runtime provider, model, dimension, ordered retrieval-unit corpus, and
corpus fingerprint must agree with the promoted semantic manifest. A mismatch
causes the backend to refuse loading the index.

## Acceptance Manifest

The manifest records:

- source workbook SHA-256 fingerprints;
- counts for every relational asset;
- canonical per-table relationship checksums;
- a combined relationship checksum and schema checksum;
- embedding provider and model identifier;
- embedding dimension and vector count;
- ordered retrieval-unit ID corpus manifest;
- retrieval corpus fingerprint;
- ranked unit IDs for fixed retrieval regression queries.

Columns such as `created_at` are excluded from relationship checksums. Vector
index bytes and floating-point scores are recorded for diagnostics but are not
used as cross-hardware equality requirements.

## Reproducibility Check

Build once, then use its manifest as a baseline:

```powershell
python -m app.ingestion.build_all `
  --embedding-provider hash `
  --baseline-manifest backend/data/builds/<first-build>/qiaopi_build_manifest.json
```

The second build must match:

- every relational table count and canonical checksum;
- the relational schema checksum;
- vector provider, model, dimension, count, and corpus fingerprint;
- ranked unit IDs for the fixed regression queries.

Minor floating-point score differences and vector-file byte differences do not
fail this comparison.

## Promotion

After inspecting an accepted staging manifest:

```powershell
python -m app.ingestion.build_all --embedding-provider hash --promote
```

Promotion happens only after acceptance passes. Staged files are copied to
temporary siblings first. Existing live files are moved to backups, and all
targets are rolled back if any replacement fails.

Stop the backend before promotion on Windows so SQLite and index files are not
held open.

## Diagnostic Reuse

To test database/index rebuilding without rerunning full-text preprocessing:

```powershell
python -m app.ingestion.build_all `
  --reuse-processed backend/data/processed `
  --embedding-provider hash
```

This mode is for diagnostics and tests. The default path from raw Excel remains
the reproducibility acceptance path.

## Retrieval Evaluation

The version-controlled benchmark is
`data/evaluation/retrieval_benchmark.jsonl`. It keeps the 50,064-record metadata
catalog separate from the 213 full-text records and 1,959 evidence retrieval
units.

Run the configured retrieval engines:

```powershell
python -m app.evaluation.retrieval_evaluation
```

For deterministic vector plumbing tests only:

```powershell
python -m app.evaluation.retrieval_evaluation --build-hash-test-index
```

The report writes Recall@1/3/5/10, NDCG@1/3/5/10, and MRR@10. Hash scores are
diagnostic only. Production hybrid acceptance requires a non-Hash manifest,
complete query coverage, and no NDCG@10 or MRR@10 regression against keyword
retrieval at either retrieval-unit or text-record level.
