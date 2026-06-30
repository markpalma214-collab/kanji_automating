"""
ui/drill_page.py — "AI Drill" page.

Generates a fresh multiple-choice JLPT drill from a random (optionally
adaptive) sample of the user's own kanji. Lets the student answer, then
grades it and records right/wrong per kanji into LearningStats.
"""

import tkinter as tk

from ui_common import (
    CONTENT_BG, CARD_BG, TEXT_DARK, TEXT_MUTED, SUCCESS, ERROR, FONT_FAMILY,
    section_label, card_frame, AccentButton,
)
from async_utils import run_async
from ai.client import AIError


def build_page(app):
    page = tk.Frame(app.content, bg=CONTENT_BG)

    header = tk.Frame(page, bg=CONTENT_BG)
    header.pack(fill="x", pady=(0, 16))
    section_label(header, "AI Drill").pack(side="left")

    count_var = tk.StringVar(value="8")
    tk.Label(header, text="Questions to base on (5-10 kanji):", font=(FONT_FAMILY, 10),
             bg=CONTENT_BG, fg=TEXT_MUTED).pack(side="left", padx=(24, 6))
    tk.Spinbox(header, from_=5, to=10, width=4, textvariable=count_var,
               font=(FONT_FAMILY, 11)).pack(side="left")

    generate_btn = AccentButton(header, "Generate Drill", command=lambda: on_generate())
    generate_btn.pack(side="right")

    status_label = tk.Label(page, text="Click \u201cGenerate Drill\u201d to start.",
                             font=(FONT_FAMILY, 10), bg=CONTENT_BG, fg=TEXT_MUTED, anchor="w")
    status_label.pack(fill="x", pady=(0, 10))

    # Scrollable container for the question cards
    canvas_frame = tk.Frame(page, bg=CONTENT_BG)
    canvas_frame.pack(fill="both", expand=True)
    canvas = tk.Canvas(canvas_frame, bg=CONTENT_BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    questions_holder = tk.Frame(canvas, bg=CONTENT_BG)
    questions_holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=questions_holder, anchor="nw", width=900)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    state = {"questions": [], "answer_vars": {}, "checked": False}

    def clear_questions():
        for child in questions_holder.winfo_children():
            child.destroy()
        state["answer_vars"] = {}
        state["checked"] = False

    def ensure_ready():
        if app.ai_client is None:
            status_label.config(text=f"\u26a0 AI not available: {app.ai_status}", fg=ERROR)
            return False
        return True

    def on_generate():
        if not ensure_ready():
            return
        try:
            count = int(count_var.get())
        except ValueError:
            count = 8
        clear_questions()
        generate_btn.config(state="disabled", text="Generating\u2026")
        status_label.config(text="Asking the AI for a fresh drill\u2026", fg=TEXT_MUTED)

        def work():
            return app.drill_generator.generate(count)

        def success(result):
            questions, kanji_used = result
            state["questions"] = questions
            render_questions(questions)
            generate_btn.config(state="normal", text="Generate Drill")
            used = ", ".join(k["kanji"] for k in kanji_used)
            status_label.config(text=f"Drill ready \u2014 based on: {used}", fg=SUCCESS)

        def error(exc):
            generate_btn.config(state="normal", text="Generate Drill")
            message = str(exc) if isinstance(exc, AIError) else f"Unexpected error: {exc}"
            status_label.config(text=f"\u26a0 {message}", fg=ERROR)

        run_async(app, work, success, error)

    def render_questions(questions):
        for i, q in enumerate(questions, start=1):
            card = card_frame(questions_holder)
            card.pack(fill="x", pady=(0, 14), padx=4)

            tk.Label(card, text=f"Q{i}. [{q.get('type', '?')}]", font=(FONT_FAMILY, 10, "bold"),
                     bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
            tk.Label(card, text=q.get("question", ""), font=(FONT_FAMILY, 13),
                     bg=CARD_BG, fg=TEXT_DARK, wraplength=820, justify="left").pack(anchor="w", pady=(2, 10))

            var = tk.StringVar(value="")
            state["answer_vars"][i - 1] = var
            for choice in q.get("choices", []):
                tk.Radiobutton(
                    card, text=choice, variable=var, value=choice, font=(FONT_FAMILY, 11),
                    bg=CARD_BG, fg=TEXT_DARK, selectcolor=CARD_BG, anchor="w", justify="left",
                    wraplength=780,
                ).pack(anchor="w")

            feedback = tk.Label(card, text="", font=(FONT_FAMILY, 10), bg=CARD_BG,
                                 fg=TEXT_MUTED, wraplength=820, justify="left")
            feedback.pack(anchor="w", pady=(8, 0))
            q["_feedback_label"] = feedback

        check_row = tk.Frame(questions_holder, bg=CONTENT_BG)
        check_row.pack(fill="x", pady=(4, 30))
        AccentButton(check_row, "Check Answers", command=check_answers).pack(anchor="e")

    def check_answers():
        if state["checked"]:
            return
        state["checked"] = True
        correct_count = 0
        for i, q in enumerate(state["questions"]):
            chosen = state["answer_vars"][i].get()
            correct = q.get("correct_answer", "")
            is_correct = chosen == correct
            if is_correct:
                correct_count += 1

            kanji_id = q.get("kanji_id")
            if kanji_id is not None and app.stats is not None:
                app.stats.record(kanji_id, is_correct)

            label = q["_feedback_label"]
            if not chosen:
                label.config(text=f"No answer selected. Correct answer: {correct}\n{q.get('explanation', '')}", fg=ERROR)
            elif is_correct:
                label.config(text=f"\u2713 Correct! {q.get('explanation', '')}", fg=SUCCESS)
            else:
                label.config(text=f"\u2717 You chose \u201c{chosen}\u201d. Correct answer: {correct}\n{q.get('explanation', '')}", fg=ERROR)

        status_label.config(
            text=f"Score: {correct_count}/{len(state['questions'])}",
            fg=SUCCESS if correct_count == len(state["questions"]) else TEXT_MUTED,
        )

    return page
