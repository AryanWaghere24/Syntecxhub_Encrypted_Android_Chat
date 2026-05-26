"""
crypto_engine.py — AES-256-GCM encryption + HMAC-SHA256 integrity

SECURITY MODEL:
  • AES-256-GCM provides authenticated encryption (confidentiality + integrity + authenticity).
  • A fresh 96-bit nonce is generated per message — nonce reuse with GCM is catastrophic,
    so NEVER derive or re-use nonces.
  • HMAC-SHA256 is layered on top as an independent integrity binding that also covers
    metadata (sender, timestamp) — GCM's tag only covers ciphertext.
  • Keys are derived from a shared passphrase via PBKDF2-HMAC-SHA256 (310 000 iterations,
    NIST recommendation 2023).  In production, replace with X3DH / Signal Protocol.

RISK DISCUSSION:
  • KEY STORAGE RISK: Keys live in memory (Python dict) and are written to a JSON file
    encrypted with the master key.  If an attacker has OS-level access they can ptrace the
    process and dump keys from RAM.  Mitigation: use a hardware security module (HSM) or
    Android Keystore / SecureEnclave in a real app.
  • SIDE-CHANNEL: Python's integer arithmetic is NOT constant-time.  hmac.compare_digest()
    is used for all MAC comparisons to prevent timing attacks.
  • FORWARD SECRECY: This demo uses a single long-lived session key.  Production systems
    should rotate ephemeral keys per session (e.g. Diffie-Hellman ratchet).
  • PASSPHRASE ENTROPY: A weak passphrase undermines everything.  Enforce min 12 chars
    with complexity requirements in production.
"""

import os
import hmac
import hashlib
import base64
import json
import struct
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# ─── Constants ────────────────────────────────────────────────────────────────
AES_KEY_BYTES   = 32          # AES-256
HMAC_KEY_BYTES  = 32          # HMAC-SHA256
NONCE_BYTES     = 12          # GCM nonce — 96 bits is the NIST-recommended fixed length
PBKDF2_ITERS    = 310_000     # NIST SP 800-132 recommendation (2023)
SALT_BYTES      = 32
VERSION         = 1           # protocol version byte, prepended to every message


# ─── Data Structures ──────────────────────────────────────────────────────────
@dataclass
class EncryptedMessage:
    version:     int
    sender:      str
    timestamp:   float
    nonce_b64:   str           # base64-encoded 96-bit nonce
    ciphertext_b64: str        # base64-encoded AES-GCM ciphertext+tag
    hmac_b64:    str           # base64-encoded HMAC-SHA256 over (version|sender|ts|nonce|ct)
    salt_b64:    str           # KDF salt (per-session, not per-message in this demo)
    algorithm:   str = "AES-256-GCM + HMAC-SHA256 / PBKDF2-SHA256"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "EncryptedMessage":
        return EncryptedMessage(**d)


@dataclass
class DecryptedMessage:
    sender:    str
    plaintext: str
    timestamp: float
    integrity_ok: bool
    fingerprint:  str          # SHA-256[:16] of the AES key — visible in UI


# ─── Key Material ─────────────────────────────────────────────────────────────
class SessionKeys:
    """Holds the two keys derived from the shared passphrase."""

    def __init__(self, aes_key: bytes, hmac_key: bytes, salt: bytes):
        self.aes_key  = aes_key
        self.hmac_key = hmac_key
        self.salt     = salt

    @property
    def fingerprint(self) -> str:
        """Short fingerprint users can compare out-of-band to detect MITM."""
        digest = hashlib.sha256(self.aes_key + self.hmac_key).hexdigest()
        # Format as 4 groups of 4 hex chars, easy to read aloud
        return " ".join(digest[i:i+4].upper() for i in range(0, 16, 4))

    @property
    def full_fingerprint(self) -> str:
        digest = hashlib.sha256(self.aes_key + self.hmac_key).hexdigest()
        return " ".join(digest[i:i+8].upper() for i in range(0, 64, 8))


# ─── KDF ──────────────────────────────────────────────────────────────────────
def derive_keys(passphrase: str, salt: Optional[bytes] = None) -> SessionKeys:
    """
    Derive two independent 256-bit keys from a passphrase.
    Uses PBKDF2-HMAC-SHA256 twice with different info bytes to achieve domain separation.
    """
    if salt is None:
        salt = os.urandom(SALT_BYTES)

    def _pbkdf2(info: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt + info,          # domain separation via salt extension
            iterations=PBKDF2_ITERS,
            backend=default_backend(),
        )
        return kdf.derive(passphrase.encode("utf-8"))

    aes_key  = _pbkdf2(b"aes-encryption-key-v1")
    hmac_key = _pbkdf2(b"hmac-integrity-key-v1")
    return SessionKeys(aes_key, hmac_key, salt)


# ─── Encrypt ──────────────────────────────────────────────────────────────────
def encrypt_message(plaintext: str, sender: str, keys: SessionKeys) -> EncryptedMessage:
    """
    Encrypt a UTF-8 plaintext string.

    Layout of HMAC-covered data (big-endian):
      [1 byte version] [sender UTF-8 length as 2B LE] [sender UTF-8]
      [8 byte float64 timestamp] [12 byte nonce] [ciphertext bytes]
    """
    nonce     = os.urandom(NONCE_BYTES)
    timestamp = time.time()
    aesgcm    = AESGCM(keys.aes_key)

    # Additional authenticated data bound into GCM tag
    aad = f"{VERSION}:{sender}:{timestamp:.6f}".encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)

    # HMAC-SHA256 over version + sender + timestamp + nonce + ciphertext
    sender_bytes = sender.encode("utf-8")
    mac_input = (
        struct.pack(">B", VERSION)
        + struct.pack(">H", len(sender_bytes))
        + sender_bytes
        + struct.pack(">d", timestamp)
        + nonce
        + ciphertext
    )
    mac = hmac.new(keys.hmac_key, mac_input, hashlib.sha256).digest()

    return EncryptedMessage(
        version        = VERSION,
        sender         = sender,
        timestamp      = timestamp,
        nonce_b64      = base64.b64encode(nonce).decode(),
        ciphertext_b64 = base64.b64encode(ciphertext).decode(),
        hmac_b64       = base64.b64encode(mac).decode(),
        salt_b64       = base64.b64encode(keys.salt).decode(),
    )


# ─── Decrypt ──────────────────────────────────────────────────────────────────
def decrypt_message(msg: EncryptedMessage, keys: SessionKeys) -> DecryptedMessage:
    """
    Decrypt and verify a message.  Returns a DecryptedMessage with integrity_ok=False
    if the HMAC or GCM tag verification fails — never raises silently.
    """
    nonce      = base64.b64decode(msg.nonce_b64)
    ciphertext = base64.b64decode(msg.ciphertext_b64)
    mac_given  = base64.b64decode(msg.hmac_b64)

    # 1. Verify HMAC first (fast, constant-time)
    sender_bytes = msg.sender.encode("utf-8")
    mac_input = (
        struct.pack(">B", msg.version)
        + struct.pack(">H", len(sender_bytes))
        + sender_bytes
        + struct.pack(">d", msg.timestamp)
        + nonce
        + ciphertext
    )
    mac_expected = hmac.new(keys.hmac_key, mac_input, hashlib.sha256).digest()
    integrity_ok = hmac.compare_digest(mac_given, mac_expected)  # constant-time compare

    # 2. Decrypt (GCM tag also verified internally by cryptography library)
    try:
        aesgcm = AESGCM(keys.aes_key)
        aad = f"{msg.version}:{msg.sender}:{msg.timestamp:.6f}".encode("utf-8")
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad).decode("utf-8")
    except Exception:
        plaintext    = "[DECRYPTION FAILED — message tampered or wrong key]"
        integrity_ok = False

    return DecryptedMessage(
        sender       = msg.sender,
        plaintext    = plaintext,
        timestamp    = msg.timestamp,
        integrity_ok = integrity_ok,
        fingerprint  = keys.fingerprint,
    )


# ─── Chat Log Persistence ─────────────────────────────────────────────────────
class ChatLog:
    """
    Persistent encrypted chat log stored as a JSON array of EncryptedMessage dicts.

    RISK: The log file is only as secure as the filesystem.  On a multi-user system
    ensure file permissions are 0600.  Consider encrypting the entire file at rest
    (e.g. SQLCipher) in a production app.
    """

    def __init__(self, path: str = "chat_log.json"):
        self.path = path
        self._messages: list[EncryptedMessage] = []
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._messages = [EncryptedMessage.from_dict(d) for d in raw]
        except (FileNotFoundError, json.JSONDecodeError):
            self._messages = []

    def append(self, msg: EncryptedMessage):
        self._messages.append(msg)
        self._save()

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self._messages], f, indent=2)

    def export(self, path: str):
        """Export full encrypted log to a separate file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self._messages], f, indent=2)

    @property
    def messages(self) -> list[EncryptedMessage]:
        return list(self._messages)

    def clear(self):
        self._messages = []
        self._save()
