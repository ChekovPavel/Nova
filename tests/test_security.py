"""Tests for nova.security.encryption – SecurityManager."""
from __future__ import annotations

import pytest


class TestEncryptDecrypt:
    """Symmetric encrypt/decrypt round-trip."""

    def test_round_trip(self, security):
        plaintext = "Geheime Nachricht"
        ciphertext = security.encrypt(plaintext)
        assert ciphertext != plaintext
        assert security.decrypt(ciphertext) == plaintext

    def test_empty_string(self, security):
        ct = security.encrypt("")
        assert security.decrypt(ct) == ""

    def test_unicode(self, security):
        text = "Ünïcödé: 日本語テスト 🔑"
        assert security.decrypt(security.encrypt(text)) == text

    def test_decrypt_invalid_returns_empty(self, security):
        result = security.decrypt("not-valid-ciphertext")
        assert result == ""

    def test_different_keys_cannot_decrypt(self):
        from nova.security.encryption import SecurityManager

        mgr_a = SecurityManager(secret_key="key-alpha")
        mgr_b = SecurityManager(secret_key="key-beta")

        ct = mgr_a.encrypt("secret")
        assert mgr_b.decrypt(ct) == ""


class TestPasswordHashing:
    """Password hashing and verification."""

    def test_hash_and_verify(self, security):
        pw = "mein-passwort-123"
        hashed = security.hash_password(pw)
        assert hashed != pw
        assert security.verify_password(pw, hashed)

    def test_wrong_password_fails(self, security):
        hashed = security.hash_password("correct")
        assert not security.verify_password("wrong", hashed)


class TestTokenGeneration:
    """Cryptographically secure token generation."""

    def test_default_length(self, security):
        token = security.generate_token()
        assert len(token) > 0

    def test_unique_tokens(self, security):
        tokens = {security.generate_token() for _ in range(50)}
        assert len(tokens) == 50, "Tokens should be unique"


class TestFallbackEncryption:
    """SecurityManager should work even without the cryptography library."""

    def test_no_key_still_works(self):
        from nova.security.encryption import SecurityManager

        mgr = SecurityManager(secret_key=None)
        ct = mgr.encrypt("hello")
        assert mgr.decrypt(ct) == "hello"
