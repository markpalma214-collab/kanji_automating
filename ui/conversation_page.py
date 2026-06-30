"""
ui/conversation_page.py — "Conversation Practice" page.

A chat-style interface where the AI plays a Japanese tutor, encouraging use
of vocabulary from the user's database and gently correcting mistakes.
"""

import tkinter as tk
from tkinter import ttk

from ui_common import (
    CONTENT_BG, CARD_BG, TEXT_MUTED, SUCCESS, ERROR, FONT_FAMILY,
    section_label, styled_entry, AccentButton, scrollable_text,
)
from async_utils import run_async
from ai.client import AIError


def build_page(app):
    page = tk.Frame(app.content, bg=CONTENT_BG)

    header = tk.Frame(page, bg=CONTENT_BG)
    header.pack(fill="x", pady=(0, 16))
    section_label(header, "Conversation Practice").pack(side="left")

    controls = tk.Frame(page, bg=CONTENT_BG)
    controls.pack(fill="x", pady=(0, 12))

    tk.Label(controls, text="Level:", font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED).pack(side="left")
    level_var = tk.StringVar(value="N5")
    ttk.Combobox(controls, textvariable=level_var, state="readonly",
                 values=["N5", "N4", "N3", "N2", "N1"], width=8).pack(side="left", padx=(6, 20))

    start_btn = AccentButton(controls, "Start Conversation", command=lambda: on_start())
    start_btn.pack(side="left")

    status_label = tk.Label(page, text="Pick a level and start a conversation.",
                             font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED, anchor="w")
    status_label.pack(fill="x", pady=(0, 10))

    chat_frame, chat_text = scrollable_text(page, height=18)
    chat_frame.pack(fill="both", expand=True)
    chat_text.config(state="disabled")
    chat_text.tag_configure("tutor", font=(FONT_FAMILY, 12), foreground="#1b1b2f")
    chat_text.tag_configure("user", font=(FONT_FAMILY, 12, "italic"), foreground="#2d6cdf")
    chat_text.tag_configure("correction", font=(FONT_FAMILY, 11), foreground=ERROR)
    chat_text.tag_configure("label", font=(FONT_FAMILY, 10, "bold"))

    input_row = tk.Frame(page, bg=CONTENT_BG)
    input_row.pack(fill="x", pady=(10, 0))
    user_entry = styled_entry(input_row)
    user_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    send_btn = AccentButton(input_row, "Send", command=lambda: on_send())
    send_btn.pack(side="left")
    send_btn.config(state="disabled")
    user_entry.config(state="disabled")

    def ensure_ready():
        if app.ai_client is None:
            status_label.config(text=f"\u26a0 AI not available: {app.ai_status}", fg=ERROR)
            return False
        return True

    def append_message(role, text):
        chat_text.config(state="normal")
        label = "Tutor" if role == "tutor" else "You"
        tag = "tutor" if role == "tutor" else "user"
        chat_text.insert("end", f"{label}: ", "label")
        chat_text.insert("end", text + "\n\n", tag)
        chat_text.config(state="disabled")
        chat_text.see("end")

    def append_correction(text):
        chat_text.config(state="normal")
        chat_text.insert("end", "\u26a0 Correction: ", "label")
        chat_text.insert("end", text + "\n\n", "correction")
        chat_text.config(state="disabled")
        chat_text.see("end")

    def on_start():
        if not ensure_ready():
            return
        level = level_var.get()
        start_btn.config(state="disabled", text="Starting\u2026")
        status_label.config(text="Asking the AI to start the conversation\u2026", fg=TEXT_MUTED)
        chat_text.config(state="normal")
        chat_text.delete("1.0", "end")
        chat_text.config(state="disabled")

        def work():
            return app.conversation_tutor.start(level=level)

        def success(data):
            append_message("tutor", data.get("tutor_message", ""))
            start_btn.config(state="normal", text="Restart Conversation")
            send_btn.config(state="normal")
            user_entry.config(state="normal")
            user_entry.focus()
            status_label.config(text="Conversation started \u2014 reply in Japanese (or do your best!).", fg=SUCCESS)

        def error(exc):
            start_btn.config(state="normal", text="Start Conversation")
            message = str(exc) if isinstance(exc, AIError) else f"Unexpected error: {exc}"
            status_label.config(text=f"\u26a0 {message}", fg=ERROR)

        run_async(app, work, success, error)

    def on_send():
        text = user_entry.get().strip()
        if not text:
            return
        append_message("user", text)
        user_entry.delete(0, "end")
        send_btn.config(state="disabled")
        status_label.config(text="Tutor is thinking\u2026", fg=TEXT_MUTED)

        def work():
            return app.conversation_tutor.respond(text)

        def success(data):
            if data.get("had_mistake") and data.get("correction"):
                append_correction(data["correction"])
            append_message("tutor", data.get("tutor_message", ""))
            send_btn.config(state="normal")
            status_label.config(text="Your turn \u2014 keep practicing!", fg=SUCCESS)

        def error(exc):
            send_btn.config(state="normal")
            message = str(exc) if isinstance(exc, AIError) else f"Unexpected error: {exc}"
            status_label.config(text=f"\u26a0 {message}", fg=ERROR)

        run_async(app, work, success, error)

    user_entry.bind("<Return>", lambda e: on_send())
    return page
