"""
stats.py — tracks per-kanji correct/wrong answer counts and uses them to
bias future selection toward weak kanji (Feature 4: Adaptive Learning).

Stored separately from kanji.json (in stats.json) so the core database
schema never has to change.
"""

import json
import os
import random

STATS_FILE = "stats.json"


class LearningStats:
    def __init__(self, filepath: str = STATS_FILE):
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            self._save({})

    # -- low level -------------------------------------------------
    def _load(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # -- recording ---------------------------------------------------
    def record(self, kanji_id, correct: bool):
        data = self._load()
        key = str(kanji_id)
        entry = data.setdefault(key, {"correct": 0, "wrong": 0})
        if correct:
            entry["correct"] += 1
        else:
            entry["wrong"] += 1
        self._save(data)

    def get(self, kanji_id):
        return self._load().get(str(kanji_id), {"correct": 0, "wrong": 0})

    def mastery_score(self, kanji_id) -> float:
        """0.0 = always wrong, 1.0 = always right, 0.5 = no data yet."""
        s = self.get(kanji_id)
        total = s["correct"] + s["wrong"]
        if total == 0:
            return 0.5
        return s["correct"] / total

    def difficulty_hint(self, kanji_id) -> str:
        """Used to tell the AI whether to make a question easier or harder."""
        s = self.get(kanji_id)
        total = s["correct"] + s["wrong"]
        if total < 2:
            return "normal"
        score = s["correct"] / total
        if score < 0.5:
            return "easier"   # user struggles -> simpler question, more repetition
        if score > 0.85:
            return "harder"   # user has mastered it -> push difficulty up
        return "normal"

    # -- weighted sampling --------------------------------------------
    def weighted_sample(self, kanji_list, k):
        """
        Sample k kanji from kanji_list, weighted so that low-mastery items
        (struggled-with words) are more likely to be picked, and
        high-mastery items are deprioritized but never fully excluded.
        """
        if not kanji_list:
            return []
        k = min(k, len(kanji_list))
        pool = list(kanji_list)
        weights = [(1.1 - self.mastery_score(item["id"])) ** 2 for item in pool]

        chosen = []
        for _ in range(k):
            total_w = sum(weights)
            if total_w <= 0:
                idx = random.randrange(len(pool))
            else:
                r = random.uniform(0, total_w)
                upto = 0.0
                idx = len(pool) - 1
                for i, w in enumerate(weights):
                    upto += w
                    if upto >= r:
                        idx = i
                        break
            chosen.append(pool.pop(idx))
            weights.pop(idx)
        return chosen
