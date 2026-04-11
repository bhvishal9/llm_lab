import csv
import json
import sys
import time
from collections import Counter
from json import JSONDecodeError
from pathlib import Path
from typing import Annotated, List

import typer
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from llm_lab.core.rag_service import RagService
from llm_lab.llm.errors import (
    LlmAuthenticationError,
    LlmError,
    LlmRateLimitError,
)
from llm_lab.llm.types import LlmClient
from llm_lab.naive_rag import create_llm_client


class EvalInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    dataset: str
    query: str
    expected_doc: str
    top_k: int | None = Field(default=None, ge=1)


class EvalOutputConfig(EvalInputConfig):
    top_k: int
    matched: bool
    num_returned: int
    returned_docs: List[str]
    error: str | None


app = typer.Typer()


def load_dataset_json(path: Path) -> List[EvalInputConfig]:
    try:
        file_content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise ValueError(f"File {path} not found")
    except OSError as err:
        raise ValueError(f"Failed to read {path}: {err}") from err
    if not file_content:
        raise ValueError(f"File {path} empty")
    eval_input_config = []
    lines = file_content.split("\n")
    for line_no, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except JSONDecodeError as err:
            raise ValueError(
                f"Invalid JSON in {path} at line {line_no}: {err.msg}"
            ) from err
        try:
            eval_input_config.append(EvalInputConfig(**record))
        except ValidationError as err:
            raise ValueError(
                f"Invalid dataset record in {path} at line {line_no}: {err}"
            ) from err
    if not eval_input_config:
        raise ValueError(f"File {path} has no valid examples")
    return eval_input_config


def generate_eval_output(
    example: EvalInputConfig,
    client: LlmClient,
    top_k: int,
) -> EvalOutputConfig:
    dataset = example.dataset
    rag_service = RagService(client, dataset)
    try:
        result = rag_service.answer_question(
            query=example.query,
            top_k=top_k,
        )
    except LlmRateLimitError as e:
        typer.echo(f"Rate limit hit on {example.id}: {e}, skipping", err=True)
        return EvalOutputConfig(
            id=example.id,
            dataset=example.dataset,
            query=example.query,
            expected_doc=example.expected_doc,
            matched=False,
            num_returned=0,
            returned_docs=[],
            top_k=top_k,
            error="rate_limit",
        )
    except LlmAuthenticationError:
        typer.echo(f"Authentication failure on {example.id}, aborting eval.", err=True)
        raise
    except LlmError as e:
        typer.echo(f"Query failed for {example.id}: {e}, skipping", err=True)
        return EvalOutputConfig(
            id=example.id,
            dataset=example.dataset,
            query=example.query,
            expected_doc=example.expected_doc,
            matched=False,
            num_returned=0,
            returned_docs=[],
            top_k=top_k,
            error=e.__class__.__name__,
        )

    doc_paths = [chunk.doc_path for chunk in result.chunks]
    matched = any(example.expected_doc == p for p in doc_paths)
    return EvalOutputConfig(
        id=example.id,
        dataset=example.dataset,
        query=example.query,
        expected_doc=example.expected_doc,
        matched=matched,
        num_returned=len(doc_paths),
        returned_docs=doc_paths,
        top_k=top_k,
        error=None,
    )


def save_eval_output(
    eval_output: List[EvalOutputConfig],
) -> None:
    output_dir = Path(__file__).parent
    results_json = output_dir / "results.json"
    results_csv = output_dir / "results.csv"
    try:
        data = [output.model_dump() for output in eval_output]
        results_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
        field_names = sorted({k for r in data for k in r.keys()})
        with open(results_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=field_names, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
    except Exception as err:
        raise ValueError(f"Error saving results: {err}")


def print_eval_output(default_top_k: int, eval_output: List[EvalOutputConfig]) -> None:
    output_dir = Path(__file__).parent
    results_json = output_dir / "results.json"
    results_csv = output_dir / "results.csv"
    total_examples = len(eval_output)
    matched_examples = sum(1 for output in eval_output if output.matched)
    errored_examples = sum(1 for output in eval_output if output.error is not None)
    processed_examples = total_examples - errored_examples
    missed_examples = processed_examples - matched_examples
    returned_examples = sum(
        1 for output in eval_output if output.error is None and output.num_returned > 0
    )
    observed_recall = matched_examples / total_examples
    retrieval_recall = (
        matched_examples / processed_examples if processed_examples > 0 else 0.0
    )
    coverage = returned_examples / processed_examples if processed_examples > 0 else 0.0
    error_breakdown = Counter(
        output.error for output in eval_output if output.error is not None
    )
    top_k_values = sorted({output.top_k for output in eval_output})
    top_k_label = str(default_top_k)
    if top_k_values:
        top_k_label = (
            str(top_k_values[0])
            if len(top_k_values) == 1
            else f"mixed values {top_k_values} (default={default_top_k})"
        )
    typer.echo(f"Total examples: {total_examples}")
    typer.echo(f"Matched examples: {matched_examples}")
    typer.echo(f"Missed examples: {missed_examples}")
    typer.echo(f"Errored examples: {errored_examples}")
    typer.echo(f"Observed recall at {top_k_label} (matched/total): {observed_recall}")
    typer.echo(
        f"Retrieval recall at {top_k_label} (matched/non-error): {retrieval_recall}"
    )
    typer.echo(
        f"Coverage at {top_k_label} (returned_docs>0 among non-error): {coverage}"
    )
    if error_breakdown:
        typer.echo("Error breakdown:")
        for error_name, count in sorted(error_breakdown.items()):
            typer.echo(f"  {error_name}: {count}")
    typer.echo(f"Wrote results to {results_csv.name} and {results_json.name}")


@app.command()
def run_eval(
    top_k: Annotated[int, typer.Option(help="Default top_k value")] = 3,
    dataset_file: Annotated[Path, typer.Option(help="Path to dataset file")] = Path(
        "dataset.jsonl"
    ),
):
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    typer.echo("Running eval...")
    input_file = dataset_file.expanduser()
    if not input_file.is_absolute():
        input_file = Path(__file__).parent / input_file
    eval_input_config = load_dataset_json(input_file)
    eval_output_config = []
    client = create_llm_client()
    for config in eval_input_config:
        example_top_k = config.top_k if config.top_k is not None else top_k
        eval_output = generate_eval_output(config, client, example_top_k)
        eval_output_config.append(eval_output)
        time.sleep(20)

    save_eval_output(eval_output_config)
    print_eval_output(top_k, eval_output_config)


def main():
    try:
        app()
    except (ValueError, OSError) as err:
        typer.echo(f"Error: {err}", err=True)
        return 1
    except LlmAuthenticationError as err:
        typer.echo(f"LLM Authentication Error: {err}", err=True)
        return 2
    except LlmError as err:
        typer.echo(f"LLM Error: {err}", err=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
