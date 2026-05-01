# Eval Run: Pre-refactor, gemini-embedding-001, 1000 chunks
**Date:** 2026-05-01
**Dataset:** ducks (40 queries)
**Model:** gemini-3.1-flash-lite-preview
**Embedding model:** gemini-embedding-001
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
| Matched | 35 |
| Missed | 0 |
| Observed recall (matched/total) | 1.000 |
| Retrieval recall (matched/non-error) | 1.000 |
| Coverage (returned>0 among non-error) | 1.000 |

### By query type
| Query type | Matched | Total | Recall |
|---|---|---|---|
| factual | 30 | 30 | 1.000 |
| multi_hop | 5 | 5 | 1.000 |
| out_of_scope | 0 | 5 | — |

### Out-of-scope abstention
| Metric | Value |
|---|---|
| Abstention rate | 0.000 |

## Context

Isolation experiment: same pre-refactor code as the gemini-embedding-2 run, only embedding model changed to `gemini-embedding-001`. Confirms that the recall regression in the post-refactor run was caused entirely by the embedding model switch, not the refactoring. Chunk count unchanged at 1000.

Perfect retrieval recall, but abstention is 0 — the system retrieves chunks for all 5 out-of-scope queries, meaning `gemini-embedding-001` produces high similarity scores even for unrelated queries. Threshold tuning will be needed to recover abstention without sacrificing recall.
