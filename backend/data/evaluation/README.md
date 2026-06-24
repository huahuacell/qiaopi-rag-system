# Retrieval Evaluation Benchmark

`retrieval_benchmark.jsonl` is the version-controlled retrieval baseline. Its
judgments are manually authored from known catalog records and full-text
evidence; they are not generated from the current ranking output.

The benchmark contains two independent domains:

- `metadata_catalog`: 50,064 catalog records evaluated at `metadata_id` level
  across keyword, semantic, and hybrid retrieval. These records support archive
  browsing only and are never RAG evidence.
- `full_text_evidence`: 213 full-text records and 1,959 retrieval units,
  evaluated independently at `record_id` and `unit_id` level.

Relevance grades are:

- `3`: exact or primary answer;
- `2`: strongly relevant supporting result;
- `1`: weaker but still relevant result;
- omitted: unjudged/not relevant for the benchmark query.

Run the keyword baseline and any configured production semantic index:

```powershell
cd backend
python -m app.evaluation.retrieval_evaluation
```

Run deterministic plumbing diagnostics with a temporary Hash index:

```powershell
python -m app.evaluation.retrieval_evaluation --build-hash-test-index
```

Hash results are reported, but they are marked `test_hash` and cannot satisfy
production semantic acceptance. A production hybrid candidate must use a
non-Hash manifest, be available for every full-text query, and avoid regression
against keyword retrieval in both NDCG@10 and MRR@10 at retrieval-unit and
text-record levels.

When adding or changing a query, verify all judged IDs against the database and
review the benchmark SHA-256 recorded in the generated report.
