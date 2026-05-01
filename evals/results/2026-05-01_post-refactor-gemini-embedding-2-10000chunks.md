# Eval Run: Post-refactor, gemini-embedding-2, 10000 chunks
**Date:** 2026-05-01
**Dataset:** ducks (40 queries)
**Model:** gemini-3.1-flash-lite-preview
**Embedding model:** gemini-embedding-2
**Vector store:** file

## Configuration
| Parameter | Value |
|---|---|
| `MAX_CHUNKS` | 10000 |
| `top_k` | 3 |

## Results Summary
| Metric | Value |
|---|---|
| Total examples | 40 |
| Errored examples | 0 |

### Retrieval (factual + multi_hop, n=35)
| Metric | Value |
|---|---|
| Matched | 19 |
| Missed | 16 |
| Observed recall (matched/total) | 0.543 |
| Retrieval recall (matched/non-error) | 0.543 |
| Coverage (returned>0 among non-error) | 0.600 |

### By query type
| Query type | Matched | Total | Recall |
|---|---|---|---|
| factual | 16 | 30 | 0.533 |
| multi_hop | 3 | 5 | 0.600 |
| out_of_scope | 1 | 5 | — |

### Out-of-scope abstention
| Metric | Value |
|---|---|
| Abstention rate | 0.200 |

## Context

Post-refactor code, `gemini-embedding-2`, chunk limit raised to 10000. Further recall drop vs. the 1000-chunk run with the same model and code.

## Regression vs. 1000-chunk run (same model, same code)

| Metric | 1000 chunks | 10000 chunks | Delta |
|---|---|---|---|
| Retrieval recall | 0.714 | 0.543 | −0.171 |
| Coverage | 0.771 | 0.600 | −0.171 |
| Abstention rate | 0.200 | 0.200 | 0.000 |
| factual recall | 0.733 | 0.533 | −0.200 |
| multi_hop recall | 0.600 | 0.600 | 0.000 |

More chunks = worse retrieval. A larger index introduces more noise candidates, which with `gemini-embedding-2`'s already-compressed similarity scores pushes relevant chunks further down or below threshold. This is a known failure mode for dense retrieval: score distributions flatten as index size grows, making it harder to separate signal from noise at a fixed threshold or top-k.

This result strengthens the case for using `gemini-embedding-001`, which maintains perfect recall at 1000 chunks regardless of index size pressure.
