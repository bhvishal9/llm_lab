# Eval Run: Pre-refactor, gemini-embedding-001, 5000 chunks
**Date:** 2026-05-01
**Dataset:** ducks (40 queries)
**Model:** gemini-3.1-flash-lite-preview
**Embedding model:** gemini-embedding-001
**Vector store:** file

## Configuration
| Parameter | Value |
|---|---|
| `MAX_CHUNKS` | 5000 |
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

Same as the 1000-chunk run with `gemini-embedding-001`, only `MAX_CHUNKS` raised to 5000. Results are identical — confirms that the corpus fits comfortably within 1000 chunks and chunk count is not a limiting factor for this dataset. No further signal from increasing the limit.
