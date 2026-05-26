"""
main.py — SecureChat: Production-Ready Encrypted Desktop Chat
Tech Stack: Python 3.11+ · CustomTkinter (Material-inspired dark UI) · cryptography lib

Run:
    pip install customtkinter cryptography pillow
    python main.py
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
import json
import os
import random
import hashlib
from datetime import datetime
from typing import Optional

from crypto_engine import (
    derive_keys, encrypt_message, decrypt_message,
    ChatLog, EncryptedMessage, SessionKeys
)

# ─── Theme Constants ───────────────────────────────────────────────────────────
DARK_BG         = "#0A0E1A"
SURFACE         = "#111827"
SURFACE_2       = "#1A2234"
SURFACE_3       = "#1E2D45"
ACCENT_CYAN     = "#00D4FF"
ACCENT_TEAL     = "#00B4AA"
ALICE_BUBBLE    = "#1A3A5C"
ALICE_ACCENT    = "#2196F3"
BOB_BUBBLE      = "#1A3320"
BOB_ACCENT      = "#00C853"
DANGER          = "#FF5252"
WARNING         = "#FFB300"
SUCCESS         = "#69F0AE"
TEXT_PRIMARY    = "#E8EFF8"
TEXT_SECONDARY  = "#8899B0"
TEXT_DIM        = "#4A5568"
FONT_MONO       = ("JetBrains Mono", 10) if os.name != "nt" else ("Consolas", 10)

# ─── Simulated Bob Auto-Replies ───────────────────────────────────────────────
BOB_REPLIES = [
    "Got it, message received and verified ✓",
    "The encryption looks solid — HMAC checks passed on my end.",
    "Interesting. Let me run the key fingerprint comparison...",
    "Confirmed. AES-256-GCM is holding up beautifully.",
    "This channel is secure. We can proceed.",
    "Copy that. No integrity violations detected.",
    "Roger. The ciphertext arrived intact.",
    "Acknowledged. Key rotation scheduled for next session.",
    "All clear on this end. No man-in-the-middle detected.",
    "Received. PBKDF2 derivation successful, salts match.",
]


# ─── Passphrase Setup Dialog ──────────────────────────────────────────────────
class PassphraseDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SecureChat — Session Key Setup")
        self.geometry("480x380")
        self.configure(fg_color=DARK_BG)
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None

        self._build()
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 480) // 2
        y = (self.winfo_screenheight() - 380) // 2
        self.geometry(f"480x380+{x}+{y}")

    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="🔐  SESSION KEY SETUP",
                     font=("SF Pro Display", 15, "bold"),
                     text_color=ACCENT_CYAN).pack(pady=20)

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=20)

        ctk.CTkLabel(body,
            text="Enter a shared passphrase.\nBoth parties must use the SAME passphrase.",
            font=("SF Pro Text", 12), text_color=TEXT_SECONDARY,
            justify="center").pack(pady=(0, 16))

        # Passphrase entry
        self.entry = ctk.CTkEntry(
            body, placeholder_text="Minimum 8 characters...",
            show="●", width=380, height=44,
            fg_color=SURFACE_2, border_color=ACCENT_CYAN,
            text_color=TEXT_PRIMARY, font=("SF Pro Text", 13),
        )
        self.entry.pack(pady=(0, 8))

        # Strength meter
        self.strength_label = ctk.CTkLabel(body, text="",
            font=("SF Pro Text", 11), text_color=TEXT_DIM)
        self.strength_label.pack()

        self.entry.bind("<KeyRelease>", self._update_strength)

        # Show/hide toggle
        self.show_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(body, text="Show passphrase",
                        variable=self.show_var, command=self._toggle_show,
                        fg_color=ACCENT_TEAL, text_color=TEXT_SECONDARY,
                        font=("SF Pro Text", 11)).pack(pady=8)

        # Warning
        warn_frame = ctk.CTkFrame(body, fg_color="#1A1200", corner_radius=8)
        warn_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(warn_frame,
            text="⚠  Keys are derived via PBKDF2-SHA256 (310,000 iterations).\n"
                 "   A strong passphrase is your only protection.",
            font=FONT_MONO, text_color=WARNING,
            justify="left").pack(padx=12, pady=8)

        # Button
        ctk.CTkButton(body, text="DERIVE KEYS & START SESSION",
                      command=self._confirm,
                      fg_color=ACCENT_TEAL, hover_color="#007A72",
                      text_color="#000", font=("SF Pro Display", 13, "bold"),
                      height=44, corner_radius=8).pack(pady=(12, 0), fill="x")

    def _update_strength(self, _event=None):
        pw = self.entry.get()
        score = 0
        if len(pw) >= 8:  score += 1
        if len(pw) >= 12: score += 1
        if any(c.isupper() for c in pw): score += 1
        if any(c.isdigit() for c in pw): score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw): score += 1
        labels = ["", "Weak 🔴", "Fair 🟡", "Good 🟢", "Strong 💪", "Excellent 🛡"]
        self.strength_label.configure(text=f"Strength: {labels[score]}" if pw else "")

    def _toggle_show(self):
        self.entry.configure(show="" if self.show_var.get() else "●")

    def _confirm(self):
        pw = self.entry.get()
        if len(pw) < 8:
            self.strength_label.configure(text="⚠ Minimum 8 characters required", text_color=DANGER)
            return
        self.result = pw
        self.destroy()


# ─── Info Panel ───────────────────────────────────────────────────────────────
class InfoPanel(ctk.CTkToplevel):
    def __init__(self, parent, keys: SessionKeys):
        super().__init__(parent)
        self.title("Encryption Info")
        self.geometry("560x520")
        self.configure(fg_color=DARK_BG)
        self.resizable(False, False)

        self._build(keys)
        self.after(100, self._center)

    def _center(self):
        x = (self.winfo_screenwidth()  - 560) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"560x520+{x}+{y}")

    def _build(self, keys: SessionKeys):
        ctk.CTkLabel(self, text="🛡  ENCRYPTION ALGORITHM INFO",
                     font=("SF Pro Display", 15, "bold"),
                     text_color=ACCENT_CYAN).pack(pady=(24, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        rows = [
            ("Cipher",          "AES-256-GCM (Authenticated Encryption)"),
            ("Key size",        "256 bits (32 bytes)"),
            ("Nonce size",      "96 bits (12 bytes) — fresh random per message"),
            ("GCM tag size",    "128 bits (16 bytes) — covers ciphertext + AAD"),
            ("HMAC",            "HMAC-SHA256 — independent integrity over metadata"),
            ("KDF",             "PBKDF2-HMAC-SHA256"),
            ("KDF iterations",  "310,000 (NIST SP 800-132, 2023)"),
            ("Salt size",       "256 bits (32 bytes) per session"),
            ("Key domains",     "2 independent keys (AES key ≠ HMAC key)"),
            ("Protocol ver.",   "v1"),
            ("Forward secrecy", "⚠ Not implemented — single session key"),
            ("Short fingerprint", keys.fingerprint),
            ("Full fingerprint",  keys.full_fingerprint),
        ]

        for label, value in rows:
            row = ctk.CTkFrame(scroll, fg_color=SURFACE_2, corner_radius=8)
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(row, text=label, width=160,
                         font=("SF Pro Text", 11, "bold"),
                         text_color=ACCENT_TEAL, anchor="w").pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(row, text=value,
                         font=FONT_MONO,
                         text_color=TEXT_PRIMARY, anchor="w",
                         wraplength=320).pack(side="left", padx=8, pady=8)

        # Security risks section
        ctk.CTkLabel(scroll, text="⚠  SECURITY RISKS",
                     font=("SF Pro Display", 13, "bold"),
                     text_color=WARNING).pack(pady=(16, 4), anchor="w", padx=8)

        risks = [
            "RAM exposure: keys live in memory; ptrace can dump them (use HSM in production)",
            "Key storage: written to JSON on disk — protect file with chmod 600",
            "No forward secrecy: compromise of passphrase decrypts entire history",
            "No MITM protection: fingerprints must be verified out-of-band",
            "Python is not constant-time: hmac.compare_digest() mitigates timing attacks",
        ]
        for r in risks:
            rf = ctk.CTkFrame(scroll, fg_color="#1A0A00", corner_radius=6)
            rf.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(rf, text=f"• {r}", font=FONT_MONO,
                         text_color="#FFA726", anchor="w",
                         wraplength=490, justify="left").pack(padx=12, pady=6)


# ─── Message Bubble Widget ─────────────────────────────────────────────────────
class MessageBubble(ctk.CTkFrame):
    def __init__(self, parent, dec_msg, enc_msg: EncryptedMessage,
                 is_alice: bool, show_raw: bool = False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.dec_msg  = dec_msg
        self.enc_msg  = enc_msg
        self.is_alice = is_alice
        self.show_raw = show_raw
        self._raw_visible = False

        self._build()

    def _build(self):
        is_alice = self.is_alice
        bubble_color  = ALICE_BUBBLE  if is_alice else BOB_BUBBLE
        accent_color  = ALICE_ACCENT  if is_alice else BOB_ACCENT
        name          = "Alice" if is_alice else "Bob"
        anchor_side   = "e"    if is_alice else "w"
        pack_side     = "right" if is_alice else "left"

        ts = datetime.fromtimestamp(self.dec_msg.timestamp).strftime("%H:%M:%S")
        integrity = self.dec_msg.integrity_ok

        # Outer row
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=2)

        # Bubble container
        container = ctk.CTkFrame(row, fg_color="transparent")
        container.pack(side=pack_side, anchor=anchor_side)

        # Sender name + fingerprint
        meta_frame = ctk.CTkFrame(container, fg_color="transparent")
        meta_frame.pack(fill="x", padx=4)
        ctk.CTkLabel(meta_frame, text=name,
                     font=("SF Pro Display", 10, "bold"),
                     text_color=accent_color).pack(side=pack_side)

        # Main bubble
        bubble = ctk.CTkFrame(container, fg_color=bubble_color,
                              corner_radius=16, border_width=1,
                              border_color=accent_color)
        bubble.pack(padx=4, pady=2)

        # Message text
        ctk.CTkLabel(bubble, text=self.dec_msg.plaintext,
                     font=("SF Pro Text", 13),
                     text_color=TEXT_PRIMARY,
                     wraplength=380, justify="left",
                     anchor="w").pack(padx=14, pady=(10, 4), anchor="w")

        # Footer: timestamp + integrity badge
        footer = ctk.CTkFrame(bubble, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 8))

        # Integrity indicator
        if integrity:
            badge_text  = "🔒 HMAC ✓"
            badge_color = SUCCESS
        else:
            badge_text  = "⚠ HMAC FAIL"
            badge_color = DANGER

        ctk.CTkLabel(footer, text=badge_text,
                     font=FONT_MONO,
                     text_color=badge_color).pack(side="left")

        ctk.CTkLabel(footer, text=ts,
                     font=("SF Pro Text", 10),
                     text_color=TEXT_DIM).pack(side="right")

        # Fingerprint
        fp_frame = ctk.CTkFrame(container, fg_color="transparent")
        fp_frame.pack(fill="x", padx=4)
        ctk.CTkLabel(fp_frame,
                     text=f"🔑 {self.dec_msg.fingerprint}",
                     font=FONT_MONO,
                     text_color=TEXT_DIM).pack(side=pack_side)

        # Toggle encrypted view button
        self._raw_btn = ctk.CTkButton(
            container,
            text="[ view ciphertext ]",
            command=self._toggle_raw,
            fg_color="transparent", hover_color=SURFACE_3,
            text_color=TEXT_DIM, font=FONT_MONO,
            height=20, corner_radius=4,
        )
        self._raw_btn.pack(side=pack_side, padx=4)

        # Raw ciphertext frame (hidden by default)
        self._raw_frame = ctk.CTkFrame(container, fg_color=SURFACE,
                                       corner_radius=8, border_width=1,
                                       border_color=TEXT_DIM)
        raw_text = (
            f"NONCE:  {self.enc_msg.nonce_b64[:32]}…\n"
            f"CIPHER: {self.enc_msg.ciphertext_b64[:48]}…\n"
            f"HMAC:   {self.enc_msg.hmac_b64[:48]}…"
        )
        ctk.CTkLabel(self._raw_frame, text=raw_text,
                     font=FONT_MONO,
                     text_color="#00FF88",
                     justify="left").pack(padx=10, pady=8)

    def _toggle_raw(self):
        self._raw_visible = not self._raw_visible
        if self._raw_visible:
            self._raw_frame.pack(padx=4, pady=2)
            self._raw_btn.configure(text="[ hide ciphertext ]")
        else:
            self._raw_frame.pack_forget()
            self._raw_btn.configure(text="[ view ciphertext ]")


# ─── Main Application ──────────────────────────────────────────────────────────
class SecureChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("SecureChat  ·  AES-256-GCM End-to-End Encrypted")
        self.geometry("820x700")
        self.configure(fg_color=DARK_BG)
        self.minsize(700, 550)

        self.keys: Optional[SessionKeys] = None
        self.chat_log = ChatLog("chat_log.json")
        self.current_sender = "Alice"
        self.bubble_count   = 0

        self._build_ui()
        self.after(300, self._request_passphrase)

    # ── UI Construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        self._build_body()
        self._build_input_area()
        self._build_status_bar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Left: logo + title
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left", padx=20)
        ctk.CTkLabel(left, text="🔐", font=("", 24)).pack(side="left", padx=(0, 8))
        title_col = ctk.CTkFrame(left, fg_color="transparent")
        title_col.pack(side="left")
        ctk.CTkLabel(title_col, text="SecureChat",
                     font=("SF Pro Display", 18, "bold"),
                     text_color=ACCENT_CYAN).pack(anchor="w")
        ctk.CTkLabel(title_col, text="AES-256-GCM · HMAC-SHA256 · PBKDF2",
                     font=FONT_MONO, text_color=TEXT_DIM).pack(anchor="w")

        # Right: buttons
        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right", padx=16)

        for text, cmd, color in [
            ("ℹ Info",     self._show_info,    SURFACE_3),
            ("📤 Export",  self._export_log,   SURFACE_3),
            ("🔁 Rotate",  self._rotate_keys,  SURFACE_3),
            ("🗑 Clear",   self._clear_chat,   "#2A1010"),
        ]:
            ctk.CTkButton(right, text=text, command=cmd,
                          fg_color=color, hover_color=SURFACE_2,
                          text_color=TEXT_PRIMARY,
                          font=("SF Pro Text", 11),
                          height=32, width=80,
                          corner_radius=8).pack(side="left", padx=3)

    def _build_body(self):
        # Sidebar + chat area
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # Left sidebar
        sidebar = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=0, width=160)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="PARTICIPANTS",
                     font=("SF Pro Text", 10, "bold"),
                     text_color=TEXT_DIM).pack(pady=(16, 8))

        for name, color, initial in [("Alice", ALICE_ACCENT, "A"), ("Bob", BOB_ACCENT, "B")]:
            card = ctk.CTkFrame(sidebar, fg_color=SURFACE_2, corner_radius=10)
            card.pack(fill="x", padx=10, pady=4)

            # Avatar circle (simulated)
            av = ctk.CTkFrame(card, fg_color=color, corner_radius=20,
                              width=36, height=36)
            av.pack(pady=(10, 4))
            av.pack_propagate(False)
            ctk.CTkLabel(av, text=initial, font=("SF Pro Display", 14, "bold"),
                         text_color="#000").pack(expand=True)

            ctk.CTkLabel(card, text=name,
                         font=("SF Pro Text", 12, "bold"),
                         text_color=color).pack()
            ctk.CTkLabel(card, text="● Online",
                         font=("SF Pro Text", 9),
                         text_color=SUCCESS).pack(pady=(0, 10))

        # Sender switcher
        ctk.CTkLabel(sidebar, text="SEND AS",
                     font=("SF Pro Text", 10, "bold"),
                     text_color=TEXT_DIM).pack(pady=(20, 6))

        self.sender_var = ctk.StringVar(value="Alice")
        for name in ["Alice", "Bob"]:
            ctk.CTkRadioButton(
                sidebar, text=name, variable=self.sender_var, value=name,
                fg_color=ALICE_ACCENT if name == "Alice" else BOB_ACCENT,
                text_color=TEXT_PRIMARY, font=("SF Pro Text", 12),
            ).pack(padx=16, pady=3, anchor="w")

        # Stats
        self.stats_label = ctk.CTkLabel(sidebar, text="",
                                         font=FONT_MONO,
                                         text_color=TEXT_DIM,
                                         wraplength=140, justify="left")
        self.stats_label.pack(pady=(20, 0), padx=10, anchor="w")

        # Chat area
        chat_outer = ctk.CTkFrame(body, fg_color=DARK_BG, corner_radius=0)
        chat_outer.pack(side="left", fill="both", expand=True)

        self.chat_scroll = ctk.CTkScrollableFrame(
            chat_outer, fg_color=DARK_BG, corner_radius=0,
            scrollbar_button_color=SURFACE_3,
        )
        self.chat_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # Welcome message
        self.welcome_frame = ctk.CTkFrame(self.chat_scroll,
                                           fg_color=SURFACE_2, corner_radius=12)
        self.welcome_frame.pack(pady=24, padx=40)
        ctk.CTkLabel(self.welcome_frame,
            text="🔐  End-to-End Encrypted Chat\n\n"
                 "All messages are encrypted with AES-256-GCM before leaving your device.\n"
                 "Each message has a unique nonce and is integrity-verified with HMAC-SHA256.\n\n"
                 "Click the [ view ciphertext ] button on any message to inspect the raw encrypted data.",
            font=("SF Pro Text", 12), text_color=TEXT_SECONDARY,
            justify="center", wraplength=480).pack(padx=24, pady=20)

    def _build_input_area(self):
        input_frame = ctk.CTkFrame(self, fg_color=SURFACE,
                                    corner_radius=0, height=100)
        input_frame.pack(fill="x", side="bottom")
        input_frame.pack_propagate(False)

        inner = ctk.CTkFrame(input_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        self.input_box = ctk.CTkTextbox(
            inner, height=52,
            fg_color=SURFACE_2, text_color=TEXT_PRIMARY,
            font=("SF Pro Text", 13),
            border_color=ACCENT_CYAN, border_width=1,
            corner_radius=12,
        )
        self.input_box.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.input_box.bind("<Return>",    self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)  # allow newline

        btn_col = ctk.CTkFrame(inner, fg_color="transparent")
        btn_col.pack(side="right")

        self.send_btn = ctk.CTkButton(
            btn_col, text="Send 🔒", command=self._send_message,
            fg_color=ACCENT_TEAL, hover_color="#007A72",
            text_color="#000", font=("SF Pro Display", 13, "bold"),
            height=52, width=100, corner_radius=12,
        )
        self.send_btn.pack()

        # Bob auto-reply toggle
        self.auto_reply_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            input_frame, text="Bob auto-replies",
            variable=self.auto_reply_var,
            fg_color=BOB_ACCENT, text_color=TEXT_SECONDARY,
            font=("SF Pro Text", 10),
        ).pack(side="right", padx=16, pady=(0, 8))

    def _build_status_bar(self):
        self.status_bar = ctk.CTkFrame(self, fg_color="#080C14",
                                        corner_radius=0, height=24)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar, text="⏳ Waiting for passphrase...",
            font=FONT_MONO, text_color=TEXT_DIM,
        )
        self.status_label.pack(side="left", padx=12)

        self.key_status = ctk.CTkLabel(
            self.status_bar, text="",
            font=FONT_MONO, text_color=TEXT_DIM,
        )
        self.key_status.pack(side="right", padx=12)

    # ── Actions ────────────────────────────────────────────────────────────────
    def _request_passphrase(self):
        dlg = PassphraseDialog(self)
        self.wait_window(dlg)

        if not dlg.result:
            self.status_label.configure(
                text="⚠ No passphrase entered — encryption disabled.",
                text_color=DANGER)
            messagebox.showwarning("No Passphrase",
                "Running without encryption. Please restart to set up a session key.")
            return

        self._derive_keys_async(dlg.result)

    def _derive_keys_async(self, passphrase: str):
        self.status_label.configure(
            text="⚙ Deriving keys via PBKDF2 (310k iterations)…",
            text_color=WARNING)
        self.send_btn.configure(state="disabled")

        def worker():
            start = time.time()
            keys = derive_keys(passphrase)
            elapsed = time.time() - start
            self.after(0, lambda: self._on_keys_ready(keys, elapsed))

        threading.Thread(target=worker, daemon=True).start()

    def _on_keys_ready(self, keys: SessionKeys, elapsed: float):
        self.keys = keys
        self.send_btn.configure(state="normal")
        self.status_label.configure(
            text=f"✅ Session active — AES-256-GCM  |  HMAC-SHA256  |  {elapsed:.1f}s KDF",
            text_color=SUCCESS)
        self.key_status.configure(
            text=f"🔑 {keys.fingerprint}",
            text_color=ACCENT_CYAN)
        self._update_stats()
        self._load_history()

    def _on_enter(self, event):
        if not event.state & 0x1:  # Shift not held
            self._send_message()
            return "break"

    def _send_message(self):
        if not self.keys:
            messagebox.showwarning("No Keys", "Set up a passphrase first.")
            return

        text = self.input_box.get("1.0", "end").strip()
        if not text:
            return

        self.input_box.delete("1.0", "end")
        sender = self.sender_var.get()

        enc  = encrypt_message(text, sender, self.keys)
        dec  = decrypt_message(enc, self.keys)
        self.chat_log.append(enc)

        self._add_bubble(dec, enc)
        self._update_stats()

        # Simulated Bob auto-reply
        if self.auto_reply_var.get() and sender == "Alice":
            self.after(random.randint(800, 2000), self._bob_reply)

    def _bob_reply(self):
        if not self.keys:
            return
        reply = random.choice(BOB_REPLIES)
        enc = encrypt_message(reply, "Bob", self.keys)
        dec = decrypt_message(enc, self.keys)
        self.chat_log.append(enc)
        self._add_bubble(dec, enc)
        self._update_stats()

    def _add_bubble(self, dec_msg, enc_msg: EncryptedMessage):
        is_alice = dec_msg.sender == "Alice"
        bubble = MessageBubble(
            self.chat_scroll, dec_msg, enc_msg, is_alice
        )
        bubble.pack(fill="x", padx=4, pady=2)
        self.bubble_count += 1

        # Animate in
        bubble.configure(fg_color="transparent")
        self.after(50, lambda: self._scroll_bottom())

    def _scroll_bottom(self):
        self.chat_scroll._parent_canvas.yview_moveto(1.0)

    def _load_history(self):
        msgs = self.chat_log.messages
        if not msgs:
            return

        # Remove welcome frame
        self.welcome_frame.pack_forget()

        for enc in msgs:
            try:
                dec = decrypt_message(enc, self.keys)
                is_alice = dec.sender == "Alice"
                bubble = MessageBubble(self.chat_scroll, dec, enc, is_alice)
                bubble.pack(fill="x", padx=4, pady=2)
                self.bubble_count += 1
            except Exception:
                pass

        self.after(100, self._scroll_bottom)
        self._update_stats()

    def _update_stats(self):
        total = len(self.chat_log.messages)
        alice = sum(1 for m in self.chat_log.messages if m.sender == "Alice")
        bob   = total - alice
        self.stats_label.configure(
            text=f"Messages: {total}\nAlice: {alice}\nBob: {bob}\n\nLog: chat_log.json"
        )

    def _show_info(self):
        if not self.keys:
            messagebox.showinfo("No Session", "Start a session first.")
            return
        InfoPanel(self, self.keys)

    def _export_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
            title="Export Encrypted Chat Log",
            initialfile="securechat_export.json",
        )
        if path:
            self.chat_log.export(path)
            messagebox.showinfo("Exported",
                f"Encrypted chat log saved to:\n{path}\n\n"
                "Note: messages remain encrypted in the export file.")

    def _rotate_keys(self):
        if messagebox.askyesno("Rotate Keys",
            "Derive a NEW session key from a new passphrase?\n\n"
            "⚠ Existing message history will still be readable with the OLD key only."):
            self._request_passphrase()

    def _clear_chat(self):
        if messagebox.askyesno("Clear Chat",
            "Delete ALL messages from the local log?\nThis cannot be undone."):
            self.chat_log.clear()
            for w in self.chat_scroll.winfo_children():
                w.destroy()
            self.bubble_count = 0
            self._update_stats()
            self.status_label.configure(
                text="🗑 Chat cleared.", text_color=TEXT_SECONDARY)


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = SecureChatApp()
    app.mainloop()
