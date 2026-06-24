import os
from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionError(Exception):
    """Raised when stored credentials cannot be decrypted (e.g. key rotated)."""


def _get_fernet():
    key = os.getenv("IMAP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "IMAP_ENCRYPTION_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and add it to backend/.env"
        )
    return Fernet(key.encode())


def encrypt_secret(plaintext):
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext):
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CredentialEncryptionError("Stored credential could not be decrypted") from exc
