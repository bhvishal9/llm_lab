# Eval Run: Post-refactor, gemini-embedding-2, file store
**Date:** 2026-05-01
**Dataset:** ducks (40 queries)
**Model:** gemini-3.1-flash-lite-preview
**Embedding model:** gemini-embedding-2
**Vector store:** file

## Configuration
| Parameter | Value |
|---|---|
| `MAX_CHUNKS` | 1000 |
| `top_k` | 3 |

## Results Summary
| Metric | Value |
|---|---|
| Total examples | 40 |
| Errored examples | 0 |

### Retrieval (factual + multi_hop, n=35)
| Metric | Value |
|---|---|
| Matched | 25 |
| Missed | 10 |
| Observed recall (matched/total) | 0.714 |
| Retrieval recall (matched/non-error) | 0.714 |
| Coverage (returned>0 among non-error) | 0.771 |

### By query type
| Query type | Matched | Total | Recall |
|---|---|---|---|
| factual | 22 | 30 | 0.733 |
| multi_hop | 3 | 5 | 0.600 |
| out_of_scope | 1 | 5 | — |

### Out-of-scope abstention
| Metric | Value |
|---|---|
| Abstention rate | 0.200 |

## Context

First run after refactoring `Indexer`, `VectorStoreClient`, and `Retriever` into distinct concerns. Also the first run with `gemini-embedding-2` and `gemini-3.1-flash-lite-preview` (previously `google/gemma-4-26b-a4b` for both). Pre-Qdrant baseline on the file store backend.

**Isolation confirmed:** Re-running with the pre-refactor code and the same models (`gemini-embedding-2`) produced identical results. The recall regression vs. the April baseline is caused entirely by the embedding model switch, not the refactoring. Switching to `gemini-embedding-001` restores perfect recall — see `2026-05-01_pre-refactor-gemini-embedding-001-1000chunks.md`.

## Regression vs. April baseline (gemma-4-26b-a4b, recall=0.943)

| Metric | Baseline | This run | Delta |
|---|---|---|---|
| Retrieval recall | 0.943 | 0.714 | −0.229 |
| Coverage | 1.000 | 0.771 | −0.229 |
| Abstention rate | 0.000 | 0.200 | +0.200 |
| factual recall | 0.933 | 0.733 | −0.200 |
| multi_hop recall | 1.000 | 0.600 | −0.400 |

Coverage drop (1.000 → 0.771) indicates the retriever returns zero chunks for some queries, not just wrong chunks — `gemini-embedding-2` produces lower similarity scores across the board, causing more queries to fall below threshold.

Slight abstention improvement (0 → 0.200) is a side effect of the same property: lower similarity scores incidentally filter some out-of-scope queries, but this is not a reliable mechanism.

## Misses
_Detail not captured at time of run. Re-run with per-query logging to identify which queries are returning zero chunks vs. wrong chunks._
