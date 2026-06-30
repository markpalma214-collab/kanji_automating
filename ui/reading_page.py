"""
ui/reading_page.py — "Reading Practice" page.

User picks a JLPT level and number of paragraphs; the AI generates a
textbook-style passage using only vocabulary from that level, plus a
translation and grammar notes.
"""

import tkinter as tk
from tkinter import ttk

from ui_common import (
    CONTENT_BG, TEXT_MUTED, SUCCESS, ERROR, FONT_FAMILY,
    section_label, AccentButton, scrollable_text,
)
from async_utils import run_async
from ai.client import AIError


def build_page(app):
    page = tk.Frame(app.content, bg=CONTENT_BG)

    header = tk.Frame(page, bg=CONTENT_BG)
    header.pack(fill="x", pady=(0, 16))
    section_label(header, "Reading Practice").pack(side="left")

    controls = tk.Frame(page, bg=CONTENT_BG)
    controls.pack(fill="x", pady=(0, 12))

    tk.Label(controls, text="Level:", font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED).pack(side="left")
    level_var = tk.StringVar(value="N5")
    ttk.Combobox(controls, textvariable=level_var, state="readonly",
                 values=["N5", "N4", "N3", "N2", "N1"], width=8).pack(side="left", padx=(6, 20))

    tk.Label(controls, text="Paragraphs:", font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED).pack(side="left")
    para_var = tk.StringVar(value="1")
    tk.Spinbox(controls, from_=1, to=5, width=4, textvariable=para_var,
               font=(FONT_FAMILY, 11)).pack(side="left", padx=(6, 20))

    generate_btn = AccentButton(controls, "Generate Reading", command=lambda: on_generate())
    generate_btn.pack(side="left")

    status_label = tk.Label(page, text="Pick a level and generate a passage.",
                             font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED, anchor="w")
    status_label.pack(fill="x", pady=(0, 10))

    text_frame, text_widget = scrollable_text(page, height=24)
    text_frame.pack(fill="both", expand=True)
    text_widget.config(state="disabled")
    text_widget.tag_configure("heading", font=(FONT_FAMILY, 13, "bold"))
    text_widget.tag_configure("japanese", font=(FONT_FAMILY, 14))
    text_widget.tag_configure("body", font=(FONT_FAMILY, 12))

    def ensure_ready():
        if app.ai_client is None:
            status_label.config(text=f"\u26a0 AI not available: {app.ai_status}", fg=ERROR)
            return False
        return True

    def on_generate():
        if not ensure_ready():
            return
        try:
            num_paragraphs = int(para_var.get())
        except ValueError:
            num_paragraphs = 1
        level = level_var.get()

        generate_btn.config(state="disabled", text="Generating\u2026")
        status_label.config(text="Asking the AI for a reading passage\u2026", fg=TEXT_MUTED)

        def work():
            return app.reading_generator.generate(level, num_paragraphs)

        def success(result):
            data, vocab = result
            render_passage(data)
            generate_btn.config(state="normal", text="Generate Reading")
            status_label.config(text=f"Passage ready \u2014 {len(vocab)} vocabulary words used as source material.", fg=SUCCESS)

        def error(exc):
            generate_btn.config(state="normal", text="Generate Reading")
            message = str(exc) if isinstance(exc, AIError) else f"Unexpected error: {exc}"
            status_label.config(text=f"\u26a0 {message}", fg=ERROR)

        run_async(app, work, success, error)

    def render_passage(data):
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")

        text_widget.insert("end", "日本語 (Japanese)\n", "heading")
        text_widget.insert("end", data.get("japanese", "") + "\n\n", "japanese")

        text_widget.insert("end", "English Translation\n", "heading")
        text_widget.insert("end", data.get("translation", "") + "\n\n", "body")

        text_widget.insert("end", "Grammar Notes\n", "heading")
        notes = data.get("grammar_notes", [])
        if not notes:
            text_widget.insert("end", "(none)\n", "body")
        for note in notes:
            point = note.get("point", "")
            explanation = note.get("explanation", "")
            text_widget.insert("end", f"\u2022 {point}: ", "body")
            text_widget.insert("end", f"{explanation}\n", "body")

        text_widget.config(state="disabled")

    return page
