"""
Kapitel 19 - Sicherheit & Verschlüsselung

Fernet-basierte symmetrische Verschlüsselung für sensible Inhalte
(Erinnerungen, Personenprofile).  Passwort-Hashing mit PBKDF2.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets

logger = logging.getLogger(__name__)

# Versuche, cryptography zu importieren; Fallback auf XOR-Stub
try:
    from cryptography.fernet import Fernet

    _FERNET_AVAILABLE = True
except ImportError:
    _FERNET_AVAILABLE = False
    logger.warning("cryptography nicht installiert - Verschlüsselung deaktiviert.")


class SecurityManager:
    """
    Verwaltet Schlüssel und stellt Verschlüsselungs-/Entschlüsselungs-
    dienste für Nova bereit.
    """

    PBKDF2_ITERATIONS = 390_000

    def __init__(self, secret_key: str | None = None) -> None:
        self._key_material: bytes = self._derive_key(secret_key)
        if _FERNET_AVAILABLE:
            fernet_key = base64.urlsafe_b64encode(self._key_material)
            self._fernet = Fernet(fernet_key)
        else:
            self._fernet = None

    # ------------------------------------------------------------------
    # Schlüsselableitung
    # ------------------------------------------------------------------

    def _derive_key(self, secret: str | None) -> bytes:
        """Leitet einen 32-Byte-Schlüssel aus dem Geheimnis ab."""
        if secret is None:
            # Zufälliger Sitzungsschlüssel (nicht persistent)
            return secrets.token_bytes(32)
        password = secret.encode()
        # Fester Domänen-Salt (kein direktes Passwort-Hashing, nur KDF)
        salt = b"nova_encryption_key_v1_domain_sep"
        return hashlib.pbkdf2_hmac(
            "sha256", password, salt, self.PBKDF2_ITERATIONS, dklen=32
        )

    # ------------------------------------------------------------------
    # Verschlüsselung
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Gibt den verschlüsselten Text als URL-safe-Base64-String zurück."""
        if self._fernet is None:
            return self._xor_encrypt(plaintext)
        token = self._fernet.encrypt(plaintext.encode())
        return token.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Entschlüsselt einen mit encrypt() verschlüsselten String."""
        if self._fernet is None:
            return self._xor_decrypt(ciphertext)
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception:  # InvalidToken oder andere Fehler
            logger.error("Entschlüsselung fehlgeschlagen.")
            return ""

    # ------------------------------------------------------------------
    # XOR-Fallback (nur wenn cryptography nicht verfügbar)
    # ------------------------------------------------------------------

    def _xor_encrypt(self, text: str) -> str:
        data = text.encode()
        key = self._key_material
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return base64.urlsafe_b64encode(xored).decode()

    def _xor_decrypt(self, text: str) -> str:
        xored = base64.urlsafe_b64decode(text.encode())
        key = self._key_material
        data = bytes(b ^ key[i % len(key)] for i, b in enumerate(xored))
        return data.decode(errors="replace")

    # ------------------------------------------------------------------
    # Passwort-Hashing
    # ------------------------------------------------------------------

    def hash_password(self, password: str) -> str:
        """Erstellt einen sicheren Passwort-Hash (PBKDF2-HMAC-SHA256)."""
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            self.PBKDF2_ITERATIONS,
        )
        combined = salt + dk
        return base64.urlsafe_b64encode(combined).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verifiziert ein Passwort gegen einen gespeicherten Hash."""
        try:
            combined = base64.urlsafe_b64decode(hashed.encode())
            salt, stored_dk = combined[:16], combined[16:]
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                salt,
                self.PBKDF2_ITERATIONS,
            )
            return hmac.compare_digest(dk, stored_dk)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Token-Generierung
    # ------------------------------------------------------------------

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Erzeugt einen kryptografisch sicheren Zufallstoken."""
        return secrets.token_urlsafe(length)
