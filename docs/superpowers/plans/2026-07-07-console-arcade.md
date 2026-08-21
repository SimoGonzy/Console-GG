# Console GG Retro Arcade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python console arcade with a launcher plus standalone scripts for 2048, Blackjack, Dungeon, and Wordle.

**Architecture:** A shared `console_gg` package provides UI helpers and each game lives in an isolated module under `console_gg/games`. Root scripts call each module's `main()` function so the games can be launched independently.

**Tech Stack:** Python standard library only, `unittest`, ANSI escape codes with `NO_COLOR` fallback.

## Global Constraints

- No mandatory third-party dependencies.
- Use `python -m unittest discover -s tests -p "test*.py" -v` for verification.
- Keep game logic testable without interactive input.
- Keep terminal styling consistent through `console_gg/ui.py`.
- Do not modify files outside `C:\Users\SimoneGonzato\Documents\GonzatoS\personal-projects\console-gg`.
- Ignore unrelated git changes outside this folder, especially `../sim-exp/index.html`.

---

### Task 1: Shared Arcade Scaffold

**Files:**
- Create: `console_gg/__init__.py`
- Create: `console_gg/ui.py`
- Create: `console_gg/games/__init__.py`
- Create: `main.py`
- Create: `README.md`
- Create: `tests/test_ui.py`

**Interfaces:**
- Produces: `console_gg.ui.frame(title: str, body: str, width: int = 64) -> str`
- Produces: `console_gg.ui.color(text: str, color_name: str) -> str`
- Produces: `console_gg.ui.render_menu(title: str, items: list[tuple[str, str]]) -> str`
- Produces: `console_gg.ui.clear_screen() -> None`
- Produces: `console_gg.ui.pause(message: str = "Premi INVIO per continuare...") -> None`

- [ ] Write tests for `frame`, `color`, and `render_menu`.
- [ ] Run `python -m unittest tests.test_ui -v` and confirm tests fail because helpers do not exist.
- [ ] Implement UI helpers.
- [ ] Add launcher menu in `main.py`.
- [ ] Run `python -m unittest tests.test_ui -v`.

### Task 2: 2048

**Files:**
- Create: `console_gg/games/game_2048.py`
- Create: `play_2048.py`
- Create: `tests/test_2048.py`

**Interfaces:**
- Consumes: `console_gg.ui`
- Produces: `merge_line(line: list[int]) -> tuple[list[int], int]`
- Produces: `move_board(board: list[list[int]], direction: str) -> tuple[list[list[int]], int, bool]`
- Produces: `has_moves(board: list[list[int]]) -> bool`
- Produces: `play() -> None`
- Produces: `main() -> None`

- [ ] Write tests for left/right/up/down moves, merge scoring, and no-move detection.
- [ ] Run `python -m unittest tests.test_2048 -v` and confirm tests fail because the module is missing.
- [ ] Implement pure 2048 logic.
- [ ] Implement terminal play loop using WASD and shared UI.
- [ ] Run `python -m unittest tests.test_2048 -v`.

### Task 3: Blackjack

**Files:**
- Create: `console_gg/games/blackjack.py`
- Create: `play_blackjack.py`
- Create: `tests/test_blackjack.py`

**Interfaces:**
- Consumes: `console_gg.ui`
- Produces: `hand_value(cards: list[tuple[str, str]]) -> int`
- Produces: `round_result(player: list[tuple[str, str]], dealer: list[tuple[str, str]]) -> str`
- Produces: `settle_chips(chips: int, bet: int, result: str) -> int`
- Produces: `play() -> None`
- Produces: `main() -> None`

- [ ] Write tests for ace handling, busts, dealer/player comparison, blackjack, push, and chip settlement.
- [ ] Run `python -m unittest tests.test_blackjack -v` and confirm tests fail because the module is missing.
- [ ] Implement card and round logic.
- [ ] Implement terminal play loop with chips, betting, hit, stand, and quit.
- [ ] Run `python -m unittest tests.test_blackjack -v`.

### Task 4: Dungeon

**Files:**
- Create: `console_gg/games/dungeon.py`
- Create: `play_dungeon.py`
- Create: `tests/test_dungeon.py`

**Interfaces:**
- Consumes: `console_gg.ui`
- Produces: `GameState`
- Produces: `create_dungeon(seed: int | None = None) -> GameState`
- Produces: `move_player(state: GameState, direction: str) -> str`
- Produces: `render_dungeon(state: GameState) -> str`
- Produces: `play() -> None`
- Produces: `main() -> None`

- [ ] Write tests for deterministic dungeon creation, blocked wall movement, potion pickup, treasure pickup, monster combat, and exit victory.
- [ ] Run `python -m unittest tests.test_dungeon -v` and confirm tests fail because the module is missing.
- [ ] Implement `GameState` and map generation.
- [ ] Implement movement, collision, combat, pickups, and win/lose status.
- [ ] Implement terminal play loop using WASD and shared UI.
- [ ] Run `python -m unittest tests.test_dungeon -v`.

### Task 5: Wordle

**Files:**
- Create: `console_gg/games/wordle.py`
- Create: `play_wordle.py`
- Create: `tests/test_wordle.py`

**Interfaces:**
- Consumes: `console_gg.ui`
- Produces: `evaluate_guess(secret: str, guess: str) -> list[str]`
- Produces: `is_valid_guess(guess: str, word_length: int = 5) -> bool`
- Produces: `format_feedback(guess: str, feedback: list[str]) -> str`
- Produces: `play() -> None`
- Produces: `main() -> None`

- [ ] Write tests for exact matches, present letters, absent letters, duplicate letters, and guess validation.
- [ ] Run `python -m unittest tests.test_wordle -v` and confirm tests fail because the module is missing.
- [ ] Implement Wordle evaluation.
- [ ] Implement terminal play loop with six attempts and colored history.
- [ ] Run `python -m unittest tests.test_wordle -v`.

### Task 6: Integration Polish

**Files:**
- Modify: `README.md`
- Modify: `main.py`
- Modify: all root `play_*.py` scripts as needed

**Interfaces:**
- Consumes: all game `main()` functions.
- Produces: a consistent arcade experience from launcher and direct scripts.

- [ ] Run `python -m unittest discover -s tests -p "test*.py" -v`.
- [ ] Run `python main.py` enough to confirm it imports the launcher without crashing.
- [ ] Run `python play_2048.py`, `python play_blackjack.py`, `python play_dungeon.py`, and `python play_wordle.py` enough to confirm each imports and reaches a prompt.
- [ ] Update `README.md` with launch commands and controls.
