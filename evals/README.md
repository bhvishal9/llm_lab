# Evals

This directory contains a CLI script to run retrieval evals against the RAG service.

## Run

From the repository root:

```bash
uv run python evals/run_eval.py
```

Prerequisite: set `LLM_API_KEY` in your environment before running evals.

Options:

- `--top-k INTEGER`: default retrieval depth when a dataset row does not set `top_k` (default: `3`)
- `--dataset-file PATH`: dataset file to load (default: `dataset.jsonl`)

## Dataset format

Input is JSONL (one JSON object per line).

Required fields:

- `id` (string)
- `dataset` (string)
- `query` (string)
- `expected_doc` (string)

Optional field:

- `top_k` (integer, `>= 1`) per-example override for the CLI `--top-k`

Example line:

```json
{"id":"q1","dataset":"ducks","query":"What is Bubble Shield?","expected_doc":"assets/docs/duck_technology.md","top_k":3}
```

## Dataset path behavior

- Absolute paths are used as-is (for example `/tmp/my_eval.jsonl`).
- Relative paths are resolved relative to this directory (`evals/`), not the current working directory.

Examples:

- `--dataset-file dataset.jsonl` resolves to `evals/dataset.jsonl`
- `--dataset-file /tmp/my_eval.jsonl` resolves to `/tmp/my_eval.jsonl`

## Outputs

Each run overwrites:

- `evals/results.json`
- `evals/results.csv`

Per example, output includes:

- `matched`: whether `expected_doc` was found in returned doc paths
- `returned_docs`: returned doc path list
- `num_returned`: number of returned docs
- `error`: `null` on success, or an error label (for example `rate_limit`)

## Summary metrics

The CLI prints:

- `Matched examples`
- `Missed examples` (non-error rows where `matched=false`)
- `Errored examples`
- `Observed recall` = `matched / total`
- `Retrieval recall` = `matched / non-error`
- `Coverage` = `num_returned > 0` among non-error rows
- `Error breakdown` by error value (for example rate limits vs other LLM errors)

## Output streams

- Per-example error logs are written to stderr.
- Summary and normal progress logs are written to stdout.

## Exit codes

- `0`: success
- `1`: dataset/IO/validation error
- `2`: LLM authentication error
- `3`: other LLM error
