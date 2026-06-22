import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "email_connectors"))

import crypto_utils


def test_encrypt_then_decrypt_round_trips(monkeypatch):
    monkeypatch.setenv("IMAP_ENCRYPTION_KEY", Fernet.generate_key().decode())

    ciphertext = crypto_utils.encrypt_secret("super-secret-app-password")
    assert ciphertext != "super-secret-app-password"

    plaintext = crypto_utils.decrypt_secret(ciphertext)
    assert plaintext == "super-secret-app-password"


def test_decrypt_with_wrong_key_raises(monkeypatch):
    monkeypatch.setenv("IMAP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    ciphertext = crypto_utils.encrypt_secret("super-secret-app-password")

    monkeypatch.setenv("IMAP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(crypto_utils.CredentialEncryptionError):
        crypto_utils.decrypt_secret(ciphertext)


def test_encrypt_without_key_set_raises(monkeypatch):
    monkeypatch.delenv("IMAP_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError):
        crypto_utils.encrypt_secret("anything")
