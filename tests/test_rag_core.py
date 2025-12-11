import pytest

from llm_lab.rag_core import cosine_similarity


def test_core_cosine_similarity_error() -> None:
    float_a = [1.0, 0.0]
    float_b = [0.0]

    with pytest.raises(ValueError):
        cosine_similarity(float_a, float_b)


def test_core_cosine_similarity() -> None:
    float_a = [1.0, 0.0]
    assert cosine_similarity(float_a, float_a) == 1.0


def test_core_cosine_similarity_zero() -> None:
    float_a = [1.0, 0.0]
    float_b = [0.0, 1.0]

    assert cosine_similarity(float_a, float_b) == 0.0
