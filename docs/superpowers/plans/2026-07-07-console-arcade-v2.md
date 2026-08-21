# Console GG V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Console GG with smoother controls, richer Blackjack pacing, an ambitious dungeon adventure, and Italian Wordle helpers.

**Architecture:** Add small reusable input/animation helpers in `console_gg.ui`, keep each game module self-contained, and expand Dungeon around testable dataclasses and pure state transitions. Interactive loops remain thin wrappers over deterministic logic.

**Tech Stack:** Python standard library only, `unittest`, ANSI escape codes, optional Windows `msvcrt` single-key input.

## Global Constraints

- No mandatory third-party dependencies.
- Preserve `python main.py` and every `python play_*.py` entry point.
- Keep pure logic testable without terminal input.
- Run `python -m unittest discover -s tests -p "test*.py" -v` before completion.

---

### Task 1: Shared Input and Animation

- [ ] Add tests for single-key fallback and delay-skipped animation helpers.
- [ ] Implement `read_key`, `animated_pause`, and `type_line` in `console_gg.ui`.

### Task 2: 2048 Fluid Controls

- [ ] Add tests for key normalization.
- [ ] Use single-key input when available, prompt fallback otherwise.
- [ ] Update on-screen controls.

### Task 3: Blackjack House Edge and Animation

- [ ] Add tests for dealer winning normal ties while blackjack ties still push.
- [ ] Add tests for animation-safe card dealing helpers.
- [ ] Add deal/reveal pacing in the interactive loop.

### Task 4: Wordle Italiano

- [ ] Add tests for Italian word bank and keyboard-state aggregation.
- [ ] Replace the word bank with Italian words.
- [ ] Render a keyboard panel for correct, present, available, and excluded letters.

### Task 5: Dungeon Adventure V2

- [ ] Add tests for multi-room generation, visibility, item pickups, boss aggro, monster pursuit, and boss battle actions.
- [ ] Expand `GameState` with explored tiles, inventory, equipment, rooms, enemies, and boss state.
- [ ] Generate connected rooms and corridors.
- [ ] Implement exploration, fog of war, item pickup, roaming monsters, boss chase, and turn-based boss battle.
- [ ] Update the terminal screen with legend, inventory, and battle panels.

### Task 6: Documentation and Verification

- [ ] Update `README.md` controls and feature notes.
- [ ] Run full tests, py_compile, and smoke tests for all entry points.
