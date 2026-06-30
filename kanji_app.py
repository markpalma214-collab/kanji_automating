"""
Kanji Database — Tkinter Edition (AI-powered)
A desktop app for building and browsing your personal kanji study database,
now extended with AI-powered (Groq) drills, reading practice, story mode, and
conversation practice.

Run with:  python kanji_app.py

Setup for AI features:
  pip install -r requirements.txt
  cp .env.example .env   # then put your real GROQ_API_KEY in .env
"""

import json
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox

from ui_common import (
    SIDEBAR_BG, SIDEBAR_FG, SIDEBAR_HOVER, ACCENT, CONTENT_BG, CARD_BG,
    TEXT_DARK, TEXT_MUTED, SUCCESS, ERROR, FONT_FAMILY,
    styled_entry, section_label, field_label, AccentButton, make_tree,
)
from stats import LearningStats
from ai.client import AIClient, AIError
from ai.drill import DrillGenerator
from ai.reading import ReadingGenerator
from ai.story import StoryGenerator
from ai.tutor import ConversationTutor
from ui import drill_page, reading_page, story_page, conversation_page

DB_FILE = "kanji.json"


# ========================================================================
# DATA LAYER  (unchanged from the original app — the AI layer only reads
# from this; it never modifies the kanji database)
# ========================================================================
class KanjiDB:
    """Handles all reading/writing/searching of kanji.json"""

    def __init__(self, filepath=DB_FILE):
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            self._save({"kanji": []})

    # -- low level -------------------------------------------------
    def _load(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # -- core operations ---------------------------------------------
    def add_kanji(self, kanji, hiragana, meaning, level):
        data = self._load()

        for item in data["kanji"]:
            if item["kanji"] == kanji:
                return False, f'"{kanji}" already exists (duplicate not allowed).', None

        new_id = len(data["kanji"]) + 1
        entry = {
            "id": new_id,
            "kanji": kanji,
            "hiragana": hiragana,
            "meaning": meaning,
            "level": level,
            "frequency": 0,
        }
        data["kanji"].append(entry)
        self._save(data)
        return True, f'"{kanji}" added successfully with id {new_id}.', new_id

    def search_by_level(self, target_level, limit=10):
        data = self._load()
        matches = [item for item in data["kanji"] if str(item["level"]) == str(target_level)]
        if not matches:
            return []
        sample_size = min(limit, len(matches))
        return random.sample(matches, sample_size)

    def search_by_id(self, target_id):
        data = self._load()
        for item in data["kanji"]:
            if item["id"] == target_id:
                return item
        return None

    def get_all(self):
        return self._load()["kanji"]

    def count(self):
        return len(self.get_all())

    def add_column(self, column_name, default_value=""):
        data = self._load()
        for item in data["kanji"]:
            item.setdefault(column_name, default_value)
        self._save(data)
        return len(data["kanji"])

    def add_frequency(self, kanji, frequency):
        data = self._load()
        found = False
        for item in data["kanji"]:
            if item["kanji"] == kanji:
                item["frequency"] = frequency
                found = True
        if found:
            self._save(data)
        return found

    def recompute_ids(self):
        data = self._load()
        for index, item in enumerate(data["kanji"], start=1):
            item["id"] = index
        self._save(data)
        return len(data["kanji"])

    def delete_kanji(self, kanji):
        data = self._load()
        before = len(data["kanji"])
        data["kanji"] = [item for item in data["kanji"] if item["kanji"] != kanji]
        after = len(data["kanji"])
        if after < before:
            for index, item in enumerate(data["kanji"], start=1):
                item["id"] = index
            self._save(data)
            return True
        return False


# ========================================================================
# MAIN APPLICATION
# ========================================================================
class KanjiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = KanjiDB()
        self.stats = LearningStats()

        # -- AI layer initialization ---------------------------------
        # Never crash the app if the API key is missing or the SDK isn't
        # installed: the core kanji database features must keep working.
        # Each AI page checks `self.ai_client` and shows a friendly
        # message instead of erroring out.
        self.ai_client = None
        self.ai_status = "Not initialized"
        try:
            self.ai_client = AIClient()
            self.ai_status = "Ready"
        except AIError as e:
            self.ai_status = str(e)

        self.drill_generator = DrillGenerator(self.db, self.ai_client, self.stats) if self.ai_client else None
        self.reading_generator = ReadingGenerator(self.db, self.ai_client) if self.ai_client else None
        self.story_generator = StoryGenerator(self.db, self.ai_client) if self.ai_client else None
        self.conversation_tutor = ConversationTutor(self.db, self.ai_client) if self.ai_client else None

        self.title("漢字データベース — Kanji Database (AI)")
        self.geometry("1040x700")
        self.minsize(900, 600)
        self.configure(bg=CONTENT_BG)

        self._build_layout()
        self._build_sidebar()
        self.pages = {}
        self._build_pages()
        self.show_page("add")

        if self.ai_client is None:
            self.set_status(f"AI features unavailable: {self.ai_status}", ok=False)

    # ------------------------------------------------------------
    def _build_layout(self):
        self.sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self, bg=CONTENT_BG)
        self.content.pack(side="right", fill="both", expand=True)

        self.status_bar = tk.Label(
            self, text="Ready", font=(FONT_FAMILY, 9), bg=SIDEBAR_BG,
            fg="#9a9ab0", anchor="w", padx=12, pady=4
        )
        self.status_bar.pack(side="bottom", fill="x")

    def set_status(self, text, ok=True):
        self.status_bar.config(text=text, fg=(SUCCESS if ok else "#ff7675"))

    # ------------------------------------------------------------
    def _build_sidebar(self):
        tk.Label(
            self.sidebar, text="漢字\nDatabase", font=(FONT_FAMILY, 18, "bold"),
            bg=SIDEBAR_BG, fg="white", pady=24, justify="center"
        ).pack(fill="x")

        tk.Frame(self.sidebar, bg=SIDEBAR_HOVER, height=1).pack(fill="x", padx=16, pady=(0, 6))

        nav_items = [
            ("➕  Add Kanji", "add"),
            ("🔍  Search by Level", "level"),
            ("🆔  Search by ID", "id"),
            ("📚  Browse All", "browse"),
            ("🛠  Manage Data", "manage"),
            ("🧠  AI Drill", "ai_drill"),
            ("📖  Reading Practice", "ai_reading"),
            ("📜  Story Mode", "ai_story"),
            ("💬  Conversation", "ai_chat"),
        ]
        self.nav_buttons = {}
        for label, key in nav_items:
            btn = tk.Button(
                self.sidebar, text=label, anchor="w", font=(FONT_FAMILY, 12),
                bg=SIDEBAR_BG, fg=SIDEBAR_FG, relief="flat", bd=0,
                padx=20, pady=12, cursor="hand2",
                command=lambda k=key: self.show_page(k)
            )
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=SIDEBAR_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.config(
                bg=ACCENT if self.nav_buttons.get("active") == b else SIDEBAR_BG))
            self.nav_buttons[key] = btn

        tk.Frame(self.sidebar, bg=SIDEBAR_BG).pack(fill="both", expand=True)

        self.count_label = tk.Label(
            self.sidebar, text="", font=(FONT_FAMILY, 10), bg=SIDEBAR_BG,
            fg="#9a9ab0", pady=16
        )
        self.count_label.pack(fill="x")
        self._refresh_count()

    def _refresh_count(self):
        self.count_label.config(text=f"Total kanji: {self.db.count()}")

    def _highlight_nav(self, key):
        for k, btn in self.nav_buttons.items():
            if k == "active":
                continue
            btn.config(bg=ACCENT if k == key else SIDEBAR_BG)
        self.nav_buttons["active"] = self.nav_buttons[key]

    # ------------------------------------------------------------
    def show_page(self, key):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True, padx=36, pady=28)
        self._highlight_nav(key)
        if key == "browse":
            self._populate_browse_tree()

    # ------------------------------------------------------------
    def _build_pages(self):
        self.pages["add"] = self._build_add_page()
        self.pages["level"] = self._build_level_page()
        self.pages["id"] = self._build_id_page()
        self.pages["browse"] = self._build_browse_page()
        self.pages["manage"] = self._build_manage_page()
        # AI-powered pages live in ui/*.py — kept separate from the core
        # database UI so they can be developed/extended independently.
        self.pages["ai_drill"] = drill_page.build_page(self)
        self.pages["ai_reading"] = reading_page.build_page(self)
        self.pages["ai_story"] = story_page.build_page(self)
        self.pages["ai_chat"] = conversation_page.build_page(self)

    # ---------------- ADD PAGE -----------------------------------
    def _build_add_page(self):
        page = tk.Frame(self.content, bg=CONTENT_BG)
        section_label(page, "Add a New Kanji").pack(anchor="w", pady=(0, 20))

        card = tk.Frame(page, bg=CARD_BG, padx=28, pady=24,
                         highlightbackground="#e3ddc9", highlightthickness=1)
        card.pack(fill="x")

        fields = {}
        grid = tk.Frame(card, bg=CARD_BG)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        def add_row(r, label, widget_key, widget):
            field_label(grid, label).grid(row=r, column=0, sticky="w", pady=8, padx=(0, 14))
            widget.grid(row=r, column=1, sticky="ew", pady=8)
            fields[widget_key] = widget

        kanji_entry = styled_entry(grid)
        add_row(0, "Kanji character", "kanji", kanji_entry)

        hira_entry = styled_entry(grid)
        add_row(1, "Hiragana reading", "hiragana", hira_entry)

        meaning_entry = styled_entry(grid)
        add_row(2, "Meaning", "meaning", meaning_entry)

        level_var = tk.StringVar(value="N5")
        level_combo = ttk.Combobox(
            grid, textvariable=level_var, state="readonly",
            values=["N5", "N4", "N3", "N2", "N1"], font=(FONT_FAMILY, 12)
        )
        add_row(3, "JLPT Level", "level", level_combo)

        result_label = tk.Label(card, text="", font=(FONT_FAMILY, 10),
                                 bg=CARD_BG, fg=TEXT_MUTED, anchor="w", justify="left")
        result_label.pack(fill="x", pady=(14, 0))

        def submit():
            kanji = kanji_entry.get().strip()
            hira = hira_entry.get().strip()
            meaning = meaning_entry.get().strip()
            level = level_var.get()

            if not kanji or not hira or not meaning:
                result_label.config(text="⚠ Please fill in kanji, hiragana, and meaning.", fg=ERROR)
                return

            ok, msg, _id = self.db.add_kanji(kanji, hira, meaning, level)
            result_label.config(text=("✔ " if ok else "⚠ ") + msg, fg=(SUCCESS if ok else ERROR))
            self.set_status(msg, ok)
            if ok:
                kanji_entry.delete(0, "end")
                hira_entry.delete(0, "end")
                meaning_entry.delete(0, "end")
                kanji_entry.focus()
                self._refresh_count()

        AccentButton(card, "Add Kanji", command=submit).pack(anchor="e", pady=(18, 0))
        kanji_entry.bind("<Return>", lambda e: submit())

        return page

    # ---------------- SEARCH BY LEVEL PAGE ------------------------
    def _build_level_page(self):
        page = tk.Frame(self.content, bg=CONTENT_BG)
        section_label(page, "Search by JLPT Level").pack(anchor="w", pady=(0, 20))

        controls = tk.Frame(page, bg=CONTENT_BG)
        controls.pack(fill="x", pady=(0, 16))

        level_var = tk.StringVar(value="N5")
        ttk.Combobox(
            controls, textvariable=level_var, state="readonly",
            values=["N5", "N4", "N3", "N2", "N1"], font=(FONT_FAMILY, 12), width=10
        ).pack(side="left", padx=(0, 12))

        columns = ("id", "kanji", "hiragana", "meaning", "level", "frequency")
        headers = ("ID", "Kanji", "Hiragana", "Meaning", "Level", "Frequency")
        widths = (50, 80, 130, 260, 80, 90)
        tree = make_tree(page, columns, headers, widths)

        def search():
            results = self.db.search_by_level(level_var.get(), limit=10)
            tree.delete(*tree.get_children())
            if not results:
                self.set_status(f"No kanji found for level {level_var.get()}.", ok=False)
                return
            for item in results:
                tree.insert("", "end", values=(
                    item.get("id", ""), item["kanji"], item["hiragana"],
                    item["meaning"], item.get("level", ""), item.get("frequency", "")
                ))
            self.set_status(f"Found {len(results)} kanji for level {level_var.get()} (random sample).")

        AccentButton(controls, "Search", command=search).pack(side="left")
        return page

    # ---------------- SEARCH BY ID PAGE ----------------------------
    def _build_id_page(self):
        page = tk.Frame(self.content, bg=CONTENT_BG)
        section_label(page, "Search by ID").pack(anchor="w", pady=(0, 20))

        controls = tk.Frame(page, bg=CONTENT_BG)
        controls.pack(fill="x", pady=(0, 16))

        id_entry = styled_entry(controls, width=10)
        id_entry.pack(side="left", padx=(0, 12))

        card = tk.Frame(page, bg=CARD_BG, padx=28, pady=24,
                         highlightbackground="#e3ddc9", highlightthickness=1)
        card.pack(fill="x")

        result_var = tk.StringVar(value="Enter an ID and press Search.")
        result_label = tk.Label(
            card, textvariable=result_var, font=(FONT_FAMILY, 14),
            bg=CARD_BG, fg=TEXT_DARK, justify="left", anchor="w"
        )
        result_label.pack(fill="x")

        def search():
            raw = id_entry.get().strip()
            if not raw.isdigit():
                result_var.set("⚠ Please enter a valid numeric ID.")
                return
            item = self.db.search_by_id(int(raw))
            if not item:
                result_var.set(f"No kanji found with id {raw}.")
                self.set_status(f"No kanji found with id {raw}.", ok=False)
                return
            result_var.set(
                f"Kanji: {item['kanji']}\n"
                f"Hiragana: {item['hiragana']}\n"
                f"Meaning: {item['meaning']}\n"
                f"Level: {item.get('level', '-')}\n"
                f"Frequency: {item.get('frequency', 0)}\n"
                f"ID: {item['id']}"
            )
            self.set_status(f"Found kanji id {raw}.")

        AccentButton(controls, "Search", command=search).pack(side="left")
        id_entry.bind("<Return>", lambda e: search())
        return page

    # ---------------- BROWSE ALL PAGE ------------------------------
    def _build_browse_page(self):
        page = tk.Frame(self.content, bg=CONTENT_BG)
        header = tk.Frame(page, bg=CONTENT_BG)
        header.pack(fill="x", pady=(0, 16))
        section_label(header, "Browse All Kanji").pack(side="left")
        AccentButton(header, "Refresh", command=lambda: self._populate_browse_tree()).pack(side="right")

        columns = ("id", "kanji", "hiragana", "meaning", "level", "frequency")
        headers = ("ID", "Kanji", "Hiragana", "Meaning", "Level", "Frequency")
        widths = (50, 80, 130, 260, 80, 90)
        self.browse_tree = make_tree(page, columns, headers, widths)
        return page

    def _populate_browse_tree(self):
        self.browse_tree.delete(*self.browse_tree.get_children())
        for item in self.db.get_all():
            self.browse_tree.insert("", "end", values=(
                item.get("id", ""), item["kanji"], item["hiragana"],
                item["meaning"], item.get("level", ""), item.get("frequency", "")
            ))
        self._refresh_count()
        self.set_status(f"Loaded {self.db.count()} kanji.")

    # ---------------- MANAGE DATA PAGE -----------------------------
    def _build_manage_page(self):
        page = tk.Frame(self.content, bg=CONTENT_BG)
        section_label(page, "Manage Data").pack(anchor="w", pady=(0, 20))

        wrapper = tk.Frame(page, bg=CONTENT_BG)
        wrapper.pack(fill="both", expand=True)
        wrapper.columnconfigure(0, weight=1)
        wrapper.columnconfigure(1, weight=1)

        # -- Add Frequency card --
        freq_card = tk.Frame(wrapper, bg=CARD_BG, padx=22, pady=20,
                              highlightbackground="#e3ddc9", highlightthickness=1)
        freq_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))

        tk.Label(freq_card, text="Set Frequency", font=(FONT_FAMILY, 13, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w", pady=(0, 10))
        field_label(freq_card, "Kanji character").pack(anchor="w")
        freq_kanji_entry = styled_entry(freq_card)
        freq_kanji_entry.pack(fill="x", pady=(2, 10))
        field_label(freq_card, "Frequency (number)").pack(anchor="w")
        freq_value_entry = styled_entry(freq_card)
        freq_value_entry.pack(fill="x", pady=(2, 10))

        def do_add_frequency():
            kanji = freq_kanji_entry.get().strip()
            freq = freq_value_entry.get().strip()
            if not kanji or not freq.isdigit():
                self.set_status("Enter a kanji and a numeric frequency.", ok=False)
                return
            ok = self.db.add_frequency(kanji, int(freq))
            if ok:
                self.set_status(f'Frequency for "{kanji}" set to {freq}.')
                freq_kanji_entry.delete(0, "end")
                freq_value_entry.delete(0, "end")
            else:
                self.set_status(f'"{kanji}" not found.', ok=False)

        AccentButton(freq_card, "Update Frequency", command=do_add_frequency).pack(anchor="e")

        # -- Add Column card --
        col_card = tk.Frame(wrapper, bg=CARD_BG, padx=22, pady=20,
                             highlightbackground="#e3ddc9", highlightthickness=1)
        col_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=(0, 12))

        tk.Label(col_card, text="Add Column", font=(FONT_FAMILY, 13, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w", pady=(0, 10))
        field_label(col_card, "New column name").pack(anchor="w")
        col_name_entry = styled_entry(col_card)
        col_name_entry.pack(fill="x", pady=(2, 10))
        field_label(col_card, "Default value (optional)").pack(anchor="w")
        col_default_entry = styled_entry(col_card)
        col_default_entry.pack(fill="x", pady=(2, 10))

        def do_add_column():
            name = col_name_entry.get().strip()
            default = col_default_entry.get().strip()
            if not name:
                self.set_status("Enter a column name.", ok=False)
                return
            count = self.db.add_column(name, default)
            self.set_status(f'Column "{name}" added to {count} entries.')
            col_name_entry.delete(0, "end")
            col_default_entry.delete(0, "end")

        AccentButton(col_card, "Add Column", command=do_add_column).pack(anchor="e")

        # -- Recompute IDs / Delete card --
        util_card = tk.Frame(wrapper, bg=CARD_BG, padx=22, pady=20,
                              highlightbackground="#e3ddc9", highlightthickness=1)
        util_card.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        tk.Label(util_card, text="Recompute IDs", font=(FONT_FAMILY, 13, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w", pady=(0, 10))
        tk.Label(util_card, text="Re-numbers every entry's id sequentially (1, 2, 3...).",
                 font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED, wraplength=280,
                 justify="left").pack(anchor="w", pady=(0, 10))

        def do_recompute():
            count = self.db.recompute_ids()
            self.set_status(f"IDs recomputed for {count} entries.")

        AccentButton(util_card, "Recompute IDs", command=do_recompute).pack(anchor="e")

        del_card = tk.Frame(wrapper, bg=CARD_BG, padx=22, pady=20,
                             highlightbackground="#e3ddc9", highlightthickness=1)
        del_card.grid(row=1, column=1, sticky="nsew", padx=(12, 0))

        tk.Label(del_card, text="Delete a Kanji", font=(FONT_FAMILY, 13, "bold"),
                 bg=CARD_BG, fg=TEXT_DARK).pack(anchor="w", pady=(0, 10))
        field_label(del_card, "Kanji character").pack(anchor="w")
        del_entry = styled_entry(del_card)
        del_entry.pack(fill="x", pady=(2, 10))

        def do_delete():
            kanji = del_entry.get().strip()
            if not kanji:
                self.set_status("Enter a kanji to delete.", ok=False)
                return
            if not messagebox.askyesno("Confirm delete", f'Delete "{kanji}" permanently?'):
                return
            ok = self.db.delete_kanji(kanji)
            if ok:
                self.set_status(f'"{kanji}" deleted.')
                del_entry.delete(0, "end")
                self._refresh_count()
            else:
                self.set_status(f'"{kanji}" not found.', ok=False)

        AccentButton(del_card, "Delete", command=do_delete, bg=ERROR).pack(anchor="e")

        wrapper.rowconfigure(0, weight=0)
        wrapper.rowconfigure(1, weight=0)
        return page


# ========================================================================
if __name__ == "__main__":
    app = KanjiApp()
    app.mainloop()
