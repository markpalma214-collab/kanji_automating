"""
ai/drill.py — Feature 1: AI Drill Generator.

Picks 5-10 kanji from the user's database (optionally weighted by their
learning stats), sends only those to the AI, and gets back a fresh set of
JLPT-style multiple-choice questions.
"""

import random

from .client import AIClient, AIError
from . import prompts


class DrillGenerator:
    def __init__(self, db, client: AIClient, stats=None):
        self.db = db
        self.client = client
        self.stats = stats  # optional stats.LearningStats, enables Feature 4

    def pick_kanji(self, count=8):
        all_kanji = self.db.get_all()
        if not all_kanji:
            return []
        count = max(5, min(count, 10, len(all_kanji)))
        if self.stats:
            return self.stats.weighted_sample(all_kanji, count)
        return random.sample(all_kanji, count)

    def generate(self, count=8):
        """Blocking call — run this inside async_utils.run_async, not on the
        Tk main thread."""
        kanji_list = self.pick_kanji(count)
        if not kanji_list:
            raise AIError("No kanji in the database yet. Add some kanji first.")

        difficulty_hints = None
        if self.stats:
            difficulty_hints = {k["id"]: self.stats.difficulty_hint(k["id"]) for k in kanji_list}

        prompt = prompts.build_drill_prompt(kanji_list, difficulty_hints)
        data = self.client.generate_json(prompt)
        questions = data.get("questions") or []
        if not questions:
            raise AIError("The AI did not return any questions. Try again.")
        return questions, kanji_list
