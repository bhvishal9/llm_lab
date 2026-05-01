# Eval Run: Pre-refactor, gemini-embedding-2, 1000 chunks
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

Isolation experiment: pre-refactor code with `gemini-embedding-2`. Results are identical to the post-refactor run with the same models, confirming the refactoring had no effect on retrieval behaviour. The recall regression vs. the April baseline is caused entirely by the embedding model switch.
