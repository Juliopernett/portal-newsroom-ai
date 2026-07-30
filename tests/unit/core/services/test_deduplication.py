"""Unit tests for the content-hashing domain service."""

from __future__ import annotations

from core.services.deduplication import generate_candidate_hash


def test_same_source_and_url_produce_the_same_hash() -> None:
    first = generate_candidate_hash(source="vallenato-hoy", url="https://vallenatohoy.example.com/a")
    second = generate_candidate_hash(source="vallenato-hoy", url="https://vallenatohoy.example.com/a")

    assert first == second


def test_different_urls_produce_different_hashes() -> None:
    first = generate_candidate_hash(source="vallenato-hoy", url="https://vallenatohoy.example.com/a")
    second = generate_candidate_hash(source="vallenato-hoy", url="https://vallenatohoy.example.com/b")

    assert first != second


def test_different_sources_with_same_url_produce_different_hashes() -> None:
    first = generate_candidate_hash(source="vallenato-hoy", url="https://vallenatohoy.example.com/a")
    second = generate_candidate_hash(source="el-pilon-cultural", url="https://vallenatohoy.example.com/a")

    assert first != second


def test_hash_is_case_and_whitespace_insensitive() -> None:
    first = generate_candidate_hash(
        source="Vallenato-Hoy", url=" https://VallenatoHoy.example.com/a "
    )
    second = generate_candidate_hash(source="vallenato-hoy", url="https://vallenatohoy.example.com/a")

    assert first == second
