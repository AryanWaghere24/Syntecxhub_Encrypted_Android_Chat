# GhostProtocol - Production-Ready Encrypted Chat App 🔐

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Encryption: AES-256-GCM](https://img.shields.io/badge/Encryption-AES--256--GCM-brightgreen.svg)]()
[![Status: Active](https://img.shields.io/badge/Status-Active-success.svg)]()

## 📋 Overview

**GhostProtocol** is a production-ready, end-to-end encrypted desktop chat application built with pure Python. Every message is encrypted with **AES-256-GCM** before it leaves your device — no servers, no plaintext, no traces. Designed for developers, security researchers, and privacy enthusiasts who want to understand or prototype encrypted communication systems.

### ✨ Key Features

- **🔐 AES-256-GCM Encryption** - Military-grade authenticated encryption per message
- **🛡️ HMAC-SHA256 Integrity** - Independent integrity check over full message metadata
- **🔑 PBKDF2 Key Derivation** - 310,000 iterations with 256-bit random salt
- **👻 Two-Party Simulation** - Alice & Bob chat with encrypted auto-replies
- **🔍 Ciphertext Inspector** - View raw nonce/ciphertext/HMAC per message
- **🧬 Key Fingerprint** - SHA-256 digest for out-of-band MITM detection
- **📤 Encrypted Log Export** - One-click export of full encrypted chat history
- **🎨 Premium Dark UI** - Material Design 3 cyberpunk dark theme

---

## 🎯 Project Meets ALL Requirements

| Requirement | Status | Details |
|---|---|---|
| AES Client-Side Encryption | ✅ Complete | AES-256-GCM per message |
| Send & Receive Messages | ✅ Complete | Full two-party Alice ↔ Bob simulation |
| Secure Key Storage | ✅ Complete | PBKDF2 derivation + risk comments in code |
| Message History | ✅ Complete | Persistent encrypted JSON log |
| Robust Error Handling | ✅ Complete | Tamper detection, decryption failure handling |
| Dark Theme UI | ✅ Complete | Material Design 3 dark CustomTkinter |
| Encryption Status Icon | ✅ Complete | 🔒 HMAC badge per bubble |
| Timestamp Per Message | ✅ Complete | HH:MM:SS on every bubble |
| Encrypted vs Decrypted View | ✅ Complete | Toggle raw ciphertext per message |
| Key Fingerprint Display | ✅ Complete | SHA-256 short + full fingerprint |
| Message Integrity Check | ✅ Complete | HMAC-SHA256 over all metadata |
| Simulated Two-Party Chat | ✅ Complete | Alice & Bob with auto-reply engine |
| Export Encrypted Chat Log | ✅ Complete | One-click JSON export |
| Encryption Algorithm Panel | ✅ Complete | Full tech breakdown + risk discussion |

---

## 🚀 Quick Start

### Installation

```bash
# Direct Download
1. Download main.py and crypto_engine.py
2. Place both files in the same directory
3. Run: python main.py
```

### Basic Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Launch GhostProtocol
python main.py
```

---

## 📚 Full Documentation

### On Launch

```
1. A passphrase dialog appears
2. Enter a shared passphrase (min 8 characters)
3. Keys are derived via PBKDF2 (takes ~1-2 seconds)
4. Start chatting as Alice or Bob
5. Every message is encrypted before display
```

### UI Controls

```
Send As        →  Switch between Alice and Bob sender
Send 🔒        →  Encrypt and send message (or press Enter)
[ view ciphertext ] →  Toggle raw nonce/ciphertext/HMAC display
ℹ Info         →  Open encryption algorithm info panel
📤 Export      →  Save encrypted log to JSON file
🔁 Rotate      →  Derive new keys from new passphrase
🗑 Clear       →  Delete all messages from local log
Bob auto-reply →  Toggle simulated Bob encrypted responses
```

### Examples

```bash
# Standard launch
python main.py

# First time setup
# → Enter passphrase e.g. "MySecret@2024"
# → Keys derived in ~1 second
# → Type as Alice, Bob auto-replies

# View encryption details per message
# → Click [ view ciphertext ] under any bubble

# Export your encrypted chat
# → Click 📤 Export → choose save location

# Rotate keys mid-session
# → Click 🔁 Rotate → enter new passphrase
```

---

## 🏗️ Architecture

### Core Modules

**crypto_engine.py**
- AES-256-GCM encryption / decryption
- HMAC-SHA256 integrity verification
- PBKDF2-HMAC-SHA256 key derivation
- Per-message nonce generation
- Encrypted JSON chat log persistence

**main.py**
- Premium CustomTkinter dark UI
- Message bubble renderer with integrity badges
- Passphrase setup dialog with strength meter
- Algorithm info panel with risk discussion
- Bob auto-reply simulation engine
- Export, rotate, and clear functions

### Core Classes

**SessionKeys**
- Holds AES key + HMAC key derived from passphrase
- Exposes short and full SHA-256 key fingerprint
- Domain-separated key derivation (AES key ≠ HMAC key)

**EncryptedMessage**
- Dataclass representing a single encrypted packet
- Fields: version, sender, timestamp, nonce, ciphertext, hmac, salt
- Serializable to/from JSON for persistent storage

**DecryptedMessage**
- Result of decryption: plaintext, sender, timestamp
- integrity_ok flag — False if HMAC or GCM tag fails
- fingerprint for UI display

**ChatLog**
- Append-only encrypted JSON message store
- Auto-saves on every message
- Export to arbitrary path
- Load and decrypt history on startup

**SecureChatApp**
- Main CustomTkinter window
- Manages session keys, chat log, bubble rendering
- Non-blocking PBKDF2 derivation via threading

**MessageBubble**
- Per-message CTkFrame widget
- Shows plaintext, HMAC badge, timestamp, fingerprint
- Toggle raw ciphertext inspector inline

### Data Flow

```
Passphrase → PBKDF2 → AES Key + HMAC Key →
Encrypt Message → Append to ChatLog →
Render Bubble → Toggle Ciphertext View →
Export / Rotate / Clear
```

---

## 🔑 Security Architecture

```
         ┌─────────────────────────────────────────┐
         │            USER PASSPHRASE              │
         └──────────────────┬──────────────────────┘
                            │
              PBKDF2-HMAC-SHA256 (310,000 iterations)
                    256-bit random salt
                            │
               ┌────────────┴────────────┐
               │                         │
         AES-256 Key                HMAC-256 Key
               │                         │
               ▼                         ▼
       AES-256-GCM                 HMAC-SHA256
     Encrypt / Decrypt         over (version | sender |
    + 128-bit GCM tag           timestamp | nonce | ct)
               │                         │
               └────────────┬────────────┘
                            │
                  EncryptedMessage {
                    version, sender, timestamp,
                    nonce, ciphertext, hmac, salt
                  }
```

### Per-Message Packet Layout

```
EncryptedMessage {
  version:        1                          ← protocol version byte
  sender:         "Alice"                    ← plaintext sender name
  timestamp:      1716890400.123456          ← Unix float64
  nonce_b64:      base64( 12 random bytes )  ← fresh 96-bit nonce per message ⚡
  ciphertext_b64: base64( AES-GCM output )   ← payload + 128-bit GCM auth tag
  hmac_b64:       base64( HMAC-SHA256 )      ← integrity over ALL fields above
  salt_b64:       base64( 32 random bytes )  ← PBKDF2 session salt
  algorithm:      "AES-256-GCM + HMAC-SHA256 / PBKDF2-SHA256"
}
```

---

## 📊 Cryptographic Spec

| Parameter | Value |
|---|---|
| **Cipher** | AES-256-GCM (Authenticated Encryption) |
| **Key size** | 256 bits (32 bytes) |
| **Nonce size** | 96 bits (12 bytes) — random, per-message |
| **GCM tag size** | 128 bits (16 bytes) |
| **MAC** | HMAC-SHA256 (independent of GCM tag) |
| **KDF** | PBKDF2-HMAC-SHA256 |
| **KDF iterations** | 310,000 (NIST SP 800-132, 2023) |
| **Salt size** | 256 bits (32 bytes) |
| **Key domains** | 2 independent keys (AES ≠ HMAC) |
| **Nonce reuse** | Impossible — `os.urandom(12)` per message |
| **Timing attacks** | Mitigated via `hmac.compare_digest()` |

---

## 📋 Sample Output

### Chat Bubble View

```
======================================================================
GHOST PROTOCOL — ENCRYPTED CHAT SESSION
======================================================================
Session Key:   EFDB 5151 5C6B 3735
Algorithm:     AES-256-GCM + HMAC-SHA256 / PBKDF2-SHA256
KDF Iters:     310,000
Status:        ✅ Session Active

──────────────────────────────────────────────────────────────────────
Alice                                               12:04:31
┌─────────────────────────────────────────────────────────┐
│  The channel is secure. We can proceed.                 │
│  🔒 HMAC ✓                                  12:04:31   │
└─────────────────────────────────────────────────────────┘
🔑 EFDB 5151 5C6B 3735
[ view ciphertext ]

                                                      Bob   12:04:33
        ┌─────────────────────────────────────────────────┐
        │  Copy that. No man-in-the-middle detected.      │
        │  🔒 HMAC ✓                          12:04:33   │
        └─────────────────────────────────────────────────┘
                               🔑 EFDB 5151 5C6B 3735
                                      [ view ciphertext ]
======================================================================
```

### Ciphertext Inspector (expanded)

```
NONCE:  8BcsCcBeb9nt8LNL3xpK4Q==
CIPHER: HRXDbW40cs5axwwLD2xyRic8oTO8gEq9...
HMAC:   VDsPxDKvcWTbe+wvZeBsH82Mp/AJaRp4...
```

### Exported JSON Log

```json
[
  {
    "version": 1,
    "sender": "Alice",
    "timestamp": 1716890671.482341,
    "nonce_b64": "8BcsCcBeb9nt8LNL3xpK4Q==",
    "ciphertext_b64": "HRXDbW40cs5axwwLD2xyRic8oTO8gEq9...",
    "hmac_b64": "VDsPxDKvcWTbe+wvZeBsH82Mp/AJaRp4...",
    "salt_b64": "k9P2mXqR7vLnTwYsH5oJcA...",
    "algorithm": "AES-256-GCM + HMAC-SHA256 / PBKDF2-SHA256"
  }
]
```

---

## ⚠️ Known Security Risks (see code comments)

```
1. 🧠 RAM EXPOSURE       — Keys live in Python memory. OS-level attacker can dump them.
                           → Production fix: Use HSM or Android Keystore / SecureEnclave

2. 🔁 NO FORWARD SECRECY — Single long-lived session key.
                           → Production fix: Implement DH ratchet (Signal Protocol / X3DH)

3. 💾 FILE PERMISSIONS   — chat_log.json is unprotected on disk.
                           → Production fix: chmod 600 or use SQLCipher

4. 🕵️  NO MITM PROTECTION — Fingerprints must be compared out-of-band manually.
                           → Production fix: PKI or Trust-On-First-Use (TOFU) model

5. ⏱  PYTHON TIMING      — Python integers are not constant-time by default.
                           → Mitigated: hmac.compare_digest() used for all MAC checks
```

---

## 💻 Requirements

- **Python**: 3.11 or higher
- **OS**: Windows, macOS, Linux
- **Dependencies**: `customtkinter`, `cryptography`, `Pillow`

```bash
# Verify Python installation
python --version
```

---

## 🔧 Installation Methods

### Method 1: Git Clone (Recommended)

```bash
git clone https://github.com/AryanWaghere24/Syntecxhub_Encrypted_Android_Chat.git
cd Syntecxhub_Encrypted_Android_Chat
pip install -r requirements.txt
python main.py
```

### Method 2: Direct Download

```
1. Download main.py and crypto_engine.py
2. Place both files in the same folder
3. Run: pip install customtkinter cryptography pillow
4. Run: python main.py
```

---

## 🐛 Troubleshooting

### Python not found

```bash
# Ubuntu/Debian
sudo apt-get install python3

# macOS
brew install python3

# Windows
# Download from python.org
```

### Module not found

```bash
pip install customtkinter cryptography pillow
```

### UI not rendering properly

```bash
# Ensure CustomTkinter is up to date
pip install --upgrade customtkinter
```

### Passphrase dialog not appearing

```bash
# Run directly, not inside an IDE terminal
python main.py
```

---

## 📈 Features Breakdown

### Encryption
- ✅ AES-256-GCM Authenticated Encryption
- ✅ HMAC-SHA256 Integrity Verification
- ✅ PBKDF2-HMAC-SHA256 Key Derivation
- ✅ Per-message 96-bit Random Nonce
- ✅ Domain-Separated Dual Keys (AES ≠ HMAC)

### Chat
- ✅ Two-party Simulation (Alice & Bob)
- ✅ Bob Auto-Reply Engine
- ✅ Persistent Encrypted Chat Log
- ✅ One-click Log Export (JSON)
- ✅ Mid-session Key Rotation
- ✅ Clear Chat History

### UI
- ✅ Material Design 3 Dark Theme
- ✅ Per-message Encryption Badge (🔒 HMAC ✓)
- ✅ Inline Ciphertext Inspector Toggle
- ✅ Key Fingerprint Per Bubble
- ✅ Passphrase Strength Meter
- ✅ Algorithm Info Panel
- ✅ Sender Switcher (Alice / Bob)
- ✅ Non-blocking PBKDF2 with Live Status

---

## 📝 Code Statistics

```
Total Lines:       ~700+
Modules:           2 (main.py, crypto_engine.py)
Classes:           8
Functions:         25+
Error Handling:    Comprehensive
Security Comments: Full risk discussion in crypto_engine.py
Documentation:     Complete
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Improve documentation
- Optimize performance

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Aryan Waghere

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 👤 Author

**Aryan Waghere**
- GitHub: [@AryanWaghere24](https://github.com/AryanWaghere24)

---

## 🙏 Acknowledgments

- Python `cryptography` library and OpenSSL bindings
- NIST SP 800-132 PBKDF2 recommendations
- CustomTkinter open-source community
- Cybersecurity and cryptography research community

---

## 📞 Support

For issues, questions, or suggestions:
1. Open an issue on GitHub
2. Check existing documentation
3. Review the troubleshooting section

---

## 🎓 What This Project Demonstrates

- AES-256-GCM authenticated encryption
- HMAC-SHA256 message integrity
- PBKDF2 key derivation (NIST standard)
- Secure nonce management
- Desktop GUI development with CustomTkinter
- Multi-threaded key derivation
- JSON-based encrypted persistence
- Tamper detection and error handling
- Real-world cryptographic risk assessment

---

## 📊 Project Status

- ✅ Core encryption engine: Complete
- ✅ UI application: Complete
- ✅ Testing: Comprehensive
- ✅ Documentation: Complete
- ✅ Production prototype: Yes
- 🚀 Active development: Ongoing

---

## 🔮 Future Enhancements

- [ ] Signal Protocol / X3DH key exchange
- [ ] Forward secrecy via DH ratchet
- [ ] Multi-user group chat
- [ ] Network socket support (real two-device chat)
- [ ] SQLCipher encrypted database backend
- [ ] Mobile port (Kivy / BeeWare)
- [ ] QR code key fingerprint verification
- [ ] Self-destructing messages

---

**⭐ If you found this useful, please give it a star!**

---

*Last updated: May 2026*
*Made with ❤️ by [Aryan Waghere](https://github.com/AryanWaghere24)*
