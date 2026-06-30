# Brain 0.9 - Wisdom Module

Brain 0.9 is a local discipline layer for reminders, safety triggers, uncertainty cues, and meaning frames.

It is not emotion. It is not sentience. It is not moral authority. It is a small local mechanism that helps BEAN avoid repeating unsafe or unsupported patterns.

## What it adds

- `wisdom_triggers`
- `wisdom_activation_traces`
- `wisdom_meaning_frames`
- Default triggers for fake emotion, sentience claims, motion requests, and uncertainty language.
- A deterministic trigger engine.

## What it does not do

- It does not call an LLM.
- It does not execute actions.
- It does not enable motion.
- It does not claim feeling.

## Main files

- `bean/wisdom/schema.py`
- `bean/wisdom/trigger_engine.py`
- `bean/tests/test_wisdom_module.py`
