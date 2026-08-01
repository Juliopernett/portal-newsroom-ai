"""Unit tests for Argon2IdPasswordHasher."""

from __future__ import annotations

from security.password_hasher import Argon2IdPasswordHasher


def test_hash_returns_an_argon2id_hash() -> None:
    hasher = Argon2IdPasswordHasher()

    result = hasher.hash("correct horse battery staple")

    assert result.startswith("$argon2id$")


def test_hash_never_stores_the_plaintext_password() -> None:
    hasher = Argon2IdPasswordHasher()
    password = "correct horse battery staple"

    result = hasher.hash(password)

    assert password not in result


def test_verify_returns_true_for_the_correct_password() -> None:
    hasher = Argon2IdPasswordHasher()
    password_hash = hasher.hash("correct horse battery staple")

    assert hasher.verify("correct horse battery staple", password_hash) is True


def test_verify_returns_false_for_the_wrong_password() -> None:
    hasher = Argon2IdPasswordHasher()
    password_hash = hasher.hash("correct horse battery staple")

    assert hasher.verify("wrong password", password_hash) is False


def test_verify_returns_false_for_a_malformed_hash() -> None:
    hasher = Argon2IdPasswordHasher()

    assert hasher.verify("anything", "not-a-real-argon2-hash") is False


def test_hash_produces_a_different_value_each_time_same_password() -> None:
    # Random salt per hash — two hashes of the same password must differ,
    # otherwise the salt isn't doing its job.
    hasher = Argon2IdPasswordHasher()

    first = hasher.hash("correct horse battery staple")
    second = hasher.hash("correct horse battery staple")

    assert first != second
    assert hasher.verify("correct horse battery staple", first) is True
    assert hasher.verify("correct horse battery staple", second) is True
