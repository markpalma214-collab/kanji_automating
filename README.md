# Kanji Database — 

A Tkinter desktop app for building and studying a personal kanji database,
now extended with Groq-powered (Llama 3.3) drills, reading practice, story mode, and
conversation practice. The kanji database (`kanji.json`) remains the single
source of truth — the AI only ever *reads* from it and never invents kanji
that aren't in your collection.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and put your real key in GROQ_API_KEY=...
python kanji_app.py
```

Get a Groq API key at https://console.groq.com/keys

If no key is configured, the original kanji-database features (Add, Search,
Browse, Manage) still work normally — the four AI pages will just show a
message explaining the AI isn't available, instead of crashing the app.

**AI provider:** this app uses [Groq](https://groq.com)'s hosted inference
API with `llama-3.3-70b-versatile` by default — a strong multilingual
instruction-tuned model that handles Japanese generation/comprehension well,
served at Groq's characteristic low latency.

## Project structure

```
kanji_app.py              Main app entry point. KanjiDB is unchanged from
                           the original; KanjiApp now also builds 4 new
                           nav pages and initializes the AI layer.
ui_common.py               Shared style constants + widget helpers (colors,
                           fonts, AccentButton, styled_entry, make_tree...),
                           used by both the original pages and the new ones.
stats.py                   LearningStats — tracks correct/wrong answers per
                           kanji id (stats.json) and exposes weighted
                           sampling + difficulty hints for adaptive drills.
async_utils.py             run_async() — runs a blocking call (an AI
                           request) on a background thread and marshals the
                           result back to the Tk main thread, so the UI
                           never freezes.

ai/                         All Groq integration, isolated from the UI.
  config.py                  Loads GROQ_API_KEY from .env or the real
                             environment. Never hardcoded.
  client.py                   AIClient — thin Groq SDK wrapper, JSON-mode
                             generation, centralized error handling
                             (raises AIError, never a raw exception).
                             GeminiClient/GeminiError remain as backward-
                             compatible aliases for AIClient/AIError.
  prompts.py                   All prompt templates in one place.
  drill.py                      Feature 1: AI Drill Generator.
  reading.py                    Feature 2: AI Reading Generator.
  story.py                      Feature 3: Story Mode (persists
                             story_state.json per JLPT level).
  tutor.py                       Feature 5: Conversation Practice.

ui/                          One file per new page, built the same way as
                             the original pages (Frame + grid + AccentButton).
  drill_page.py
  reading_page.py
  story_page.py
  conversation_page.py
```

## Feature 4: Adaptive Learning

`stats.py` records every drill answer (`LearningStats.record(kanji_id, correct)`)
in `stats.json`, separate from your kanji database. Two things use this:

- `DrillGenerator` calls `stats.weighted_sample()` so kanji you get wrong
  more often are more likely to be picked for the next drill.
- `stats.difficulty_hint()` tells the AI, per kanji, whether to make
  related questions easier (struggling) or harder (mastered) — this is
  woven into the drill prompt automatically.

## Data files created at runtime

- `kanji.json` — your kanji database (already existed).
- `stats.json` — per-kanji correct/wrong counts for adaptive difficulty.
- `story_state.json` — saved story chapters per JLPT level.

None of these ever leave your machine except for the vocabulary text sent
to the Groq API when you actively use an AI page.

## Extending further

- Add a new AI feature: create `ai/your_feature.py` + a prompt builder in
  `ai/prompts.py`, then a page in `ui/your_feature_page.py` that calls it
  through `async_utils.run_async`. Wire it into `KanjiApp._build_pages`
  and the sidebar nav list in `kanji_app.py`.
- Swap the model: change `AIClient.DEFAULT_MODEL` or pass
  `model_name=` when constructing `AIClient()`. Any Groq-hosted chat
  model that supports JSON mode will work.
