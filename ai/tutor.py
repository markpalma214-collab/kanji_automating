"""
ai/tutor.py — Feature 5: Conversation Practice.

The AI acts as a Japanese tutor, holding a running conversation that
encourages use of vocabulary drawn from the user's database. Mistakes are
explained, corrected, and the student is invited to try again.
"""

import random

from .client import AIClient, AIError
from . import prompts


class ConversationTutor:
    def __init__(self, db, client: AIClient):
        self.db = db
        self.client = client
        self.history = []       # [{"role": "tutor"|"user", "text": "..."}]
        self.vocab_focus = []

    def start(self, level=None, vocab_count=10):
        """Blocking call — run via async_utils.run_async."""
        pool = self.db.get_all()
        if level:
            pool = [k for k in pool if str(k.get("level")) == str(level)]
        if not pool:
            raise AIError("No kanji available to build a conversation around.")

        self.vocab_focus = random.sample(pool, min(vocab_count, len(pool)))
        self.history = []

        prompt = prompts.build_tutor_start_prompt(self.vocab_focus, level)
        data = self.client.generate_json(prompt)
        message = data.get("tutor_message")
        if not message:
            raise AIError("The AI did not return an opening message. Try again.")
        self.history.append({"role": "tutor", "text": message})
        return data

    def respond(self, user_text):
        """Blocking call — run via async_utils.run_async."""
        if not self.vocab_focus:
            raise AIError("Start a conversation before sending a message.")

        self.history.append({"role": "user", "text": user_text})
        prompt = prompts.build_tutor_turn_prompt(self.vocab_focus, self.history)
        data = self.client.generate_json(prompt)
        message = data.get("tutor_message")
        if not message:
            raise AIError("The AI did not return a reply. Try again.")
        self.history.append({"role": "tutor", "text": message})
        return data
