"""
ai/prompts.py — every prompt template used by the AI features lives here,
so prompt wording can be tuned in one place without touching generator or
UI logic.

All prompts instruct the AI to use ONLY the vocabulary supplied (drawn from
the user's own kanji.json), and to respond with strict JSON so it can be
parsed reliably.
"""


def _vocab_block(kanji_list, with_id=False):
    lines = []
    for k in kanji_list:
        prefix = f'[id={k["id"]}] ' if with_id else ""
        lines.append(
            f'- {prefix}{k["kanji"]} ({k["hiragana"]}) = "{k["meaning"]}" '
            f'[JLPT {k.get("level", "?")}]'
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- Feature 1
def build_drill_prompt(kanji_list, difficulty_hints=None):
    vocab_block = _vocab_block(kanji_list, with_id=True)
    hint_block = ""
    if difficulty_hints:
        hint_lines = [
            f'- kanji id {kid}: make related questions {hint}'
            for kid, hint in difficulty_hints.items() if hint != "normal"
        ]
        if hint_lines:
            hint_block = "\nDifficulty adjustments based on the learner's history:\n" + "\n".join(hint_lines)

    return f"""You are a Japanese JLPT exam writer.

Using ONLY the following kanji as the focus of the questions (minimal connecting
grammar/particles are fine, but do not introduce other kanji as a question's answer
focus):
{vocab_block}
{hint_block}

Generate a fresh, varied multiple-choice drill with 6 to 10 questions. Mix these
question types across the set:
- "reading": ask for the correct hiragana reading of a kanji
- "meaning": ask for the correct English meaning of a kanji/word
- "fill_blank": a short Japanese sentence with a blank, the student picks the
  correct kanji/word to fill it
- "sentence_comprehension": a short Japanese sentence or mini-situation, followed
  by a comprehension question about it

Each question must have exactly 4 answer choices with only one correct answer.
Vary the wording, sentences, and scenarios every time, even if asked again with
the same kanji list — never reuse a previous phrasing.

Respond ONLY with JSON, no markdown fences, no extra commentary, in this exact
structure:
{{
  "questions": [
    {{
      "type": "reading" | "meaning" | "fill_blank" | "sentence_comprehension",
      "kanji_id": <id of the primary kanji this question targets, from the list above>,
      "question": "...",
      "choices": ["...", "...", "...", "..."],
      "correct_answer": "...",
      "explanation": "..."
    }}
  ]
}}"""


# ---------------------------------------------------------------- Feature 2
def build_reading_prompt(vocab, level, num_paragraphs):
    vocab_block = _vocab_block(vocab)
    return f"""You are writing a JLPT {level} textbook reading passage.

Vocabulary to use as naturally as possible (incorporate as many as you reasonably
can without forcing it):
{vocab_block}

Write {num_paragraphs} paragraph(s) of natural, coherent Japanese text appropriate
for a JLPT {level} learner. Rules:
- Only use grammar patterns appropriate for JLPT {level} or easier.
- Avoid introducing vocabulary beyond the list above whenever possible; if a
  connecting word is unavoidable, keep it simple and common.
- The passage should read like something from an actual Japanese textbook, not
  a list of disconnected sentences.

After the passage, provide a natural English translation, then explain any
grammar points in the passage that a {level} learner might find difficult.

Respond ONLY with JSON, no markdown fences, in this exact structure:
{{
  "japanese": "...",
  "translation": "...",
  "grammar_notes": [
    {{"point": "...", "explanation": "..."}}
  ]
}}"""


# ---------------------------------------------------------------- Feature 3
def build_story_prompt(vocab, level, chapter_num, char_min, char_max, previous_text):
    vocab_block = _vocab_block(vocab)
    continuity = (
        f'This is chapter {chapter_num}. Continue directly from the previous '
        f'chapter below — keep the same characters, setting, and plot thread:\n'
        f'"""{previous_text}"""'
        if previous_text else
        f'This is chapter {chapter_num}, the very beginning of a new story. '
        f'Introduce a simple setting and a main character.'
    )

    return f"""You are writing a serialized Japanese graded reader for JLPT {level}
learners.

Vocabulary to use as naturally as possible in this chapter:
{vocab_block}

{continuity}

The Japanese text of this chapter must be approximately {char_min}-{char_max}
Japanese characters long (count characters, not words — do not go far outside
this range). Write in natural Japanese using only grammar appropriate for
JLPT {level} or easier. Do not introduce vocabulary far beyond the list above.
End the chapter at a small narrative beat so it can continue next time.

Respond ONLY with JSON, no markdown fences, in this exact structure:
{{
  "japanese": "...",
  "translation": "...",
  "chapter_title": "..."
}}"""


# ---------------------------------------------------------------- Feature 5
def build_tutor_start_prompt(vocab, level):
    vocab_block = _vocab_block(vocab)
    level_txt = f" appropriate for a JLPT {level} learner" if level else ""
    return f"""You are a warm, encouraging Japanese conversation tutor{level_txt}.

Try to naturally use, and gently encourage the student to use, this vocabulary:
{vocab_block}

Start a short conversation in simple Japanese (you may add a brief English gloss
in parentheses if a word is likely unfamiliar) by asking the student an opening
question that invites them to respond using some of this vocabulary.

Respond ONLY with JSON, no markdown fences:
{{ "tutor_message": "..." }}"""


def build_tutor_turn_prompt(vocab, history):
    vocab_block = _vocab_block(vocab)
    history_block = "\n".join(f'{h["role"]}: {h["text"]}' for h in history)
    return f"""You are a warm, encouraging Japanese conversation tutor. Continue
this conversation. Encourage use of this vocabulary where natural:
{vocab_block}

Conversation so far:
{history_block}

The most recent message is from the student. If it contains a Japanese grammar
or vocabulary mistake, gently explain the mistake, give the correction, and
invite them to try again. If it's correct, briefly affirm it. Either way,
continue the conversation naturally with a follow-up question in simple
Japanese.

Respond ONLY with JSON, no markdown fences:
{{
  "tutor_message": "...",
  "had_mistake": true/false,
  "correction": "explanation of the mistake and the fix, or null if none"
}}"""
