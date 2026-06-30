"""
ai/reading.py — Feature 2: AI Reading Generator.

Picks vocabulary from a chosen JLPT level and asks the AI for a textbook-
style reading passage limited to that level's grammar/vocabulary.
"""

import random

from .client import AIClient, AIError
from . import prompts


class ReadingGenerator:
    def __init__(self, db, client: AIClient):
        self.db = db
        self.client = client

    def generate(self, level, num_paragraphs=1):
        """Blocking call — run via async_utils.run_async."""
        pool = [k for k in self.db.get_all() if str(k.get("level")) == str(level)]
        if not pool:
            raise AIError(f"No kanji found for level {level}. Add some first.")

        sample_size = min(len(pool), max(8, num_paragraphs * 5))
        vocab = random.sample(pool, sample_size)

        prompt = prompts.build_reading_prompt(vocab, level, num_paragraphs)
        data = self.client.generate_json(prompt)
        if not data.get("japanese"):
            raise AIError("The AI did not return a passage. Try again.")
        return data, vocab
