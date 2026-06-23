# Reproducible Data Build

`qiaopi.db` and semantic-index files are generated runtime artifacts and are
not stored in Git. A fresh checkout must complete data construction before the
backend or frontend is started.

From `backend/`, run the complete installation build:

```powershell
cd backend
python -m app.ingestion.build_all `
  --embedding-provider hash `
  --promote
```

This command:

1. creates a unique directory under `backend/data/builds/`;
2. preprocesses the 213-record raw workbook;
3. builds a new SQLite database;
4. imports and indexes the 50,064 metadata records;
5. links text and metadata records;
6. builds the SQLite knowledge graph;
7. builds the retrieval-unit vector index;
8. runs database, relationship, vector, and retrieval-regression acceptance;
9. writes `qiaopi_build_manifest.json`;
10. promotes the accepted database, manifest, processed files, and semantic
    index to their runtime paths with rollback on promotion failure.

Only after this command reports `"status": "accepted"` and
`"promoted": true`, start the API:

```powershell
python -m uvicorn main:app `
  --host 127.0.0.1 `
  --port 8000 `
  --reload
```

Startup performs a read-only acceptance check. It never creates a missing
database, builds tables, or repairs a partial graph. If the accepted database
or manifest is missing/incomplete, startup stops and prints the exact
`build_all --promote` command to run. This prevents a partially initialized
SQLite file from appearing to be a valid installation.

For CI or diagnostics, omit `--promote`. The accepted build remains isolated
and all live runtime assets stay untouched:

```powershell
python -m app.ingestion.build_all --embedding-provider hash
```

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

The 50,064-record metadata catalog uses an independent semantic index so
catalog-only records cannot leak into full-text RAG evidence. After the main
build, create or refresh it with:

```powershell
python -m app.ingestion.build_metadata_semantic_index --provider local
```

Set `SEMANTIC_SEARCH_ENABLED=true` only when both the configured provider and
the required index artifacts are ready. Metadata semantic search remains an
archive-discovery feature and never supplies generation evidence by itself.

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

## Rebuilding an Existing Installation

Stop the backend first on Windows, then rebuild and promote:

```powershell
python -m app.ingestion.build_all --embedding-provider hash --promote
```

Promotion happens only after acceptance passes. Staged files are copied to
temporary siblings first. Existing live files are moved to backups, and all
targets are rolled back if any replacement fails.

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
