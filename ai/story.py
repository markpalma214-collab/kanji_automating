"""
ai/story.py — Feature 3: Story Mode.

Maintains a continuing, per-JLPT-level story. Each new chapter is generated
from a fresh vocabulary sample at that level, given the previous chapter's
text for continuity, and chapters gradually grow longer. Chapter history is
persisted to story_state.json so progress survives app restarts.
"""

import json
import os
import random

from .client import AIClient, AIError
from . import prompts

STORY_FILE = "story_state.json"


class StoryGenerator:
    def __init__(self, db, client: AIClient, filepath: str = STORY_FILE):
        self.db = db
        self.client = client
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            self._save({})

    # -- persistence -----------------------------------------------
    def _load(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_chapters(self, level):
        return self._load().get(str(level), [])

    def reset(self, level):
        data = self._load()
        data[str(level)] = []
        self._save(data)

    # -- generation ----------------------------------------------------
    LENGTH_RANGES = {
        1: (250, 350), 2: (250, 350),       # short
        3: (500, 700), 4: (500, 700),       # medium
    }
    LONG_RANGE = (900, 1200)                 # chapter 5+

    def _char_range_for_chapter(self, chapter_num):
        return self.LENGTH_RANGES.get(chapter_num, self.LONG_RANGE)

    def next_chapter(self, level):
        """Blocking call — run via async_utils.run_async. Only sends the
        kanji that belong to the selected JLPT level (never the whole
        database) to keep requests small and quota-efficient."""
        pool = [k for k in self.db.get_all() if str(k.get("level")) == str(level)]
        if not pool:
            raise AIError(f"No kanji found for level {level}. Add some first.")

        # A small, level-only sample is enough context for one chapter and
        # keeps the prompt (and quota usage) minimal.
        vocab = random.sample(pool, min(8, len(pool)))
        chapters = self.get_chapters(level)
        chapter_num = len(chapters) + 1
        char_min, char_max = self._char_range_for_chapter(chapter_num)

        previous_text = chapters[-1]["japanese"] if chapters else None

        prompt = prompts.build_story_prompt(vocab, level, chapter_num, char_min, char_max, previous_text)
        data = self.client.generate_json(prompt, context="story")
        if not data.get("japanese"):
            raise AIError("⚠ Something went wrong while generating the story.\nPlease try again.")

        data["chapter"] = chapter_num
        all_data = self._load()
        level_chapters = all_data.setdefault(str(level), [])
        level_chapters.append(data)
        self._save(all_data)
        return data
