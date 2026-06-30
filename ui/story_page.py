"""
ui/story_page.py — "Story Mode" page.

Generates a continuing story for a chosen JLPT level. Each chapter builds
on the previous one and gradually grows longer, using only vocabulary from
that level in the user's database. Progress is persisted by StoryGenerator.
"""

import tkinter as tk
from tkinter import ttk, messagebox

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
    section_label(header, "Story Mode").pack(side="left")

    controls = tk.Frame(page, bg=CONTENT_BG)
    controls.pack(fill="x", pady=(0, 12))

    tk.Label(controls, text="Level:", font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED).pack(side="left")
    level_var = tk.StringVar(value="N5")
    level_combo = ttk.Combobox(controls, textvariable=level_var, state="readonly",
                                values=["N5", "N4", "N3", "N2", "N1"], width=8)
    level_combo.pack(side="left", padx=(6, 20))

    next_btn = AccentButton(controls, "Next Chapter", command=lambda: on_next_chapter())
    next_btn.pack(side="left")

    reset_btn = AccentButton(controls, "Reset Story", command=lambda: on_reset(), bg=ERROR)
    reset_btn.pack(side="left", padx=(10, 0))

    status_label = tk.Label(page, text="Pick a level and generate the first chapter.",
                             font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED, anchor="w")
    status_label.pack(fill="x", pady=(0, 10))

    text_frame, text_widget = scrollable_text(page, height=24)
    text_frame.pack(fill="both", expand=True)
    text_widget.config(state="disabled")
    text_widget.tag_configure("heading", font=(FONT_FAMILY, 14, "bold"))
    text_widget.tag_configure("japanese", font=(FONT_FAMILY, 14))
    text_widget.tag_configure("body", font=(FONT_FAMILY, 12))

    state = {"busy": False}

    def ensure_ready():
        if app.ai_client is None:
            status_label.config(text=f"\u26a0 AI not available: {app.ai_status}", fg=ERROR)
            return False
        return True

    def load_existing_for_level(*_):
        level = level_var.get()
        chapters = app.story_generator.get_chapters(level)
        render_all_chapters(chapters)
        if chapters:
            status_label.config(text=f"Loaded {len(chapters)} existing chapter(s) for {level}.", fg=TEXT_MUTED)
        else:
            status_label.config(text=f"No chapters yet for {level}. Click \u201cNext Chapter\u201d to begin.", fg=TEXT_MUTED)

    level_combo.bind("<<ComboboxSelected>>", load_existing_for_level)

    def on_next_chapter():
        # Ignore repeated clicks while a request is already in flight.
        if state["busy"]:
            return
        if not ensure_ready():
            return

        level = level_var.get()
        state["busy"] = True
        next_btn.config(state="disabled", text="Writing\u2026")
        reset_btn.config(state="disabled")
        level_combo.config(state="disabled")
        status_label.config(text="The AI is writing your next chapter\u2026", fg=TEXT_MUTED)

        def work():
            return app.story_generator.next_chapter(level)

        def finish_busy():
            state["busy"] = False
            next_btn.config(state="normal", text="Next Chapter")
            reset_btn.config(state="normal")
            level_combo.config(state="readonly")

        def success(chapter):
            finish_busy()
            append_chapter(chapter)
            status_label.config(text=f"Chapter {chapter.get('chapter', '?')} added.", fg=SUCCESS)

        def error(exc):
            finish_busy()
            # AIError messages are already friendly and safe to show
            # directly; never surface a raw exception/traceback to the user.
            message = str(exc) if isinstance(exc, AIError) else \
                "⚠ Something went wrong while generating the story.\nPlease try again."
            status_label.config(text=message, fg=ERROR)

        run_async(app, work, success, error)

    def on_reset():
        if state["busy"]:
            return
        level = level_var.get()
        if not messagebox.askyesno("Reset story", f"Delete all chapters for {level}?"):
            return
        app.story_generator.reset(level)
        render_all_chapters([])
        status_label.config(text=f"Story for {level} reset.", fg=SUCCESS)

    def render_all_chapters(chapters):
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.config(state="disabled")
        for chapter in chapters:
            append_chapter(chapter, save=False)

    def append_chapter(chapter, save=True):
        text_widget.config(state="normal")
        title = chapter.get("chapter_title") or f"Chapter {chapter.get('chapter', '?')}"
        text_widget.insert("end", f"\u7b2c{chapter.get('chapter', '?')}\u7ae0 \u2014 {title}\n", "heading")
        text_widget.insert("end", chapter.get("japanese", "") + "\n\n", "japanese")
        text_widget.insert("end", "Translation: ", "heading")
        text_widget.insert("end", chapter.get("translation", "") + "\n\n", "body")
        text_widget.config(state="disabled")
        text_widget.see("end")

    load_existing_for_level()
    return page
