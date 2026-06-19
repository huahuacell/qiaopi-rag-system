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
- `local`: the configured sentence-transformers model; if the optional
  dependency is unavailable, the existing provider behavior falls back to
  `hash` and records that effective provider in the manifest.

For real semantic retrieval, use `local` and make sure the runtime
`EMBEDDING_PROVIDER` and `EMBEDDING_MODEL` agree with the promoted semantic
manifest.

## Acceptance Manifest

The manifest records:

- source workbook SHA-256 fingerprints;
- counts for every relational asset;
- canonical per-table relationship checksums;
- a combined relationship checksum and schema checksum;
- embedding provider and model identifier;
- embedding dimension and vector count;
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
