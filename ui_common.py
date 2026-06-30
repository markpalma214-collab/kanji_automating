"""
ui_common.py — shared style constants and widget helpers.

Extracted from the original kanji_app.py so that both the main app and the
new AI pages (ui/*.py) can use the same look-and-feel without a circular
import between kanji_app.py and the ui/ package.
"""

import tkinter as tk
from tkinter import ttk

# ----------------------------------------------------------------------
# Color palette — inspired by washi paper + hanko ink-stamp red
# ----------------------------------------------------------------------
SIDEBAR_BG    = "#1b1b2f"
SIDEBAR_FG    = "#e8e8e8"
SIDEBAR_HOVER = "#2a2a45"
ACCENT        = "#c0392b"   # hanko red
ACCENT_DARK   = "#922b21"
CONTENT_BG    = "#f7f3e9"   # washi paper cream
CARD_BG       = "#ffffff"
TEXT_DARK     = "#1b1b2f"
TEXT_MUTED    = "#6b6b6b"
SUCCESS       = "#27ae60"
ERROR         = "#c0392b"
INFO          = "#2d6cdf"

FONT_FAMILY = "Yu Gothic UI"   # falls back gracefully on non-Windows systems


def styled_entry(parent, **kw):
    return tk.Entry(
        parent, font=(FONT_FAMILY, 12), bg=CARD_BG, fg=TEXT_DARK,
        relief="flat", highlightthickness=1, highlightbackground="#d8d2c2",
        highlightcolor=ACCENT, insertbackground=TEXT_DARK, **kw
    )


def section_label(parent, text):
    return tk.Label(
        parent, text=text, font=(FONT_FAMILY, 20, "bold"),
        bg=CONTENT_BG, fg=TEXT_DARK, anchor="w"
    )


def field_label(parent, text):
    return tk.Label(
        parent, text=text, font=(FONT_FAMILY, 11), bg=CONTENT_BG,
        fg=TEXT_MUTED, anchor="w"
    )


def card_frame(parent, **kw):
    return tk.Frame(
        parent, bg=CARD_BG, padx=22, pady=20,
        highlightbackground="#e3ddc9", highlightthickness=1, **kw
    )


class AccentButton(tk.Button):
    """A flat, hover-aware button styled like a hanko stamp."""
    def __init__(self, parent, text, command=None, bg=ACCENT, fg="white", **kw):
        super().__init__(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=ACCENT_DARK, activeforeground="white",
            font=(FONT_FAMILY, 11, "bold"), relief="flat", bd=0,
            padx=18, pady=8, cursor="hand2", **kw
        )
        self._bg = bg
        self.bind("<Enter>", lambda e: self.config(bg=ACCENT_DARK))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))


def make_tree(parent, columns, headers, widths):
    """Shared Treeview builder (same styling as the original browse/search tables)."""
    frame = tk.Frame(parent, bg=CONTENT_BG)
    frame.pack(fill="both", expand=True)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Kanji.Treeview", background=CARD_BG, fieldbackground=CARD_BG,
        foreground=TEXT_DARK, rowheight=32, font=(FONT_FAMILY, 11), borderwidth=0
    )
    style.configure(
        "Kanji.Treeview.Heading", background=SIDEBAR_BG, foreground="white",
        font=(FONT_FAMILY, 11, "bold"), relief="flat"
    )
    style.map("Kanji.Treeview", background=[("selected", ACCENT)],
              foreground=[("selected", "white")])

    tree = ttk.Treeview(frame, columns=columns, show="headings", style="Kanji.Treeview")
    for col, head, w in zip(columns, headers, widths):
        tree.heading(col, text=head)
        tree.column(col, width=w, anchor="w")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return tree


def scrollable_text(parent, height=14, **kw):
    """A read-only-friendly Text widget with a scrollbar, styled to match the app."""
    frame = tk.Frame(parent, bg=CONTENT_BG)
    text = tk.Text(
        frame, wrap="word", font=(FONT_FAMILY, 12), bg=CARD_BG, fg=TEXT_DARK,
        relief="flat", highlightthickness=1, highlightbackground="#e3ddc9",
        height=height, padx=14, pady=12, **kw
    )
    vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=vsb.set)
    text.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return frame, text
