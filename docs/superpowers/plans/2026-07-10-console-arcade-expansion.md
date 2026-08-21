# Console GG Arcade Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Expand Console GG from seven games to a ten-game retro arcade with a compact catalog, shared records, real-time terminal infrastructure, Snake real-time play, Block Dropper, Campo Minato, Battaglia Navale, and focused Blackjack/Dungeon upgrades.

**Architecture:** Keep game rules in testable modules and add two shared boundaries: `catalog.py`/`shell.py` for the arcade front end and `terminal.py`/`realtime.py` for nonblocking timed games. Existing `play()` entry points and standalone launchers remain supported; each game records its own statistics.

**Tech Stack:** Python standard library only, ANSI terminal output, Windows `msvcrt` with POSIX best-effort fallback, `unittest`, injected clocks/random sources for deterministic tests.

## Global Constraints

- No mandatory third-party dependencies.
- Preserve `python main.py` and all existing direct launchers.
- Preserve existing 2048 and Wordle stats keys/public functions.
- Keep rank-only Blackjack cards, standard push ties, and 3:2 natural Blackjack payout.
- Do not copy asciiart.eu source code, artwork, layouts, or strings.
- Real-time tests must use fake clocks and must not sleep.
- Rendering must remain readable at fixed widths and respect `NO_COLOR`.
- Every task follows RED, GREEN, REFACTOR and ends with focused tests.

---

### Task 1: Arcade Catalog And Shell

**Files:**
- Create: `console_gg/catalog.py`
- Create: `console_gg/shell.py`
- Modify: `main.py`
- Modify: `console_gg/stats.py`
- Test: `tests/test_catalog.py`
- Test: `tests/test_shell.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- `GameSpec(id: str, title: str, category: str, description: str, module: str, controls: str, stats_key: str)`.
- `GAME_CATALOG: tuple[GameSpec, ...]` contains the ten final game entries in stable numeric order.
- `catalog.render_catalog(catalog) -> str` renders one compact grouped screen.
- `shell.parse_command(raw: str, game_count: int) -> tuple[str, int | None]` returns `("play", index)`, `("help", None)`, `("records", None)`, or `("quit", None)`.
- `shell.run(launch, input_fn=safe_input) -> None` owns the menu loop and one post-game acknowledgement.
- `stats.summary_for(game_id, stats) -> str` returns one primary record metric without changing existing 2048/Wordle APIs.

- [x] Write failing tests for catalog order, grouped rendering, command parsing, help/records routing, and compatibility with existing game names.
- [x] Run `python -m unittest tests.test_catalog tests.test_shell -v` and confirm failure because the new modules/functions are absent.
- [x] Implement `GameSpec`, the ten-entry registry, compact rendering, shell routing, and records summaries.
- [x] Run the focused tests and then `python -m unittest tests.test_main_menu tests.test_stats -v`.
- [x] Refactor `main.py` to delegate to the shell while retaining a three-tuple `GAMES` projection for old tests.

### Task 2: Terminal Input And Fixed-Step Runner

**Files:**
- Create: `console_gg/terminal.py`
- Create: `console_gg/realtime.py`
- Modify: `console_gg/ui.py`
- Test: `tests/test_terminal.py`
- Test: `tests/test_realtime.py`

**Interfaces:**
- `KeyEvent(name: str, text: str = "")` represents semantic input.
- `normalize_key(raw: str) -> KeyEvent | None` handles WASD, arrows, Space, pause, quit, and Windows extended codes.
- `TerminalSession` exposes `poll() -> list[KeyEvent]`, `size() -> tuple[int, int]`, `present(frame: str) -> None`, `flush_input() -> None`, and restores cursor state on exit.
- `run_realtime(initial_state, handle_events, tick, render, finished, *, clock, sleeper, input_source, output, tick_period) -> state` uses bounded catch-up and injected dependencies.

- [x] Write fake-clock tests for event polling, semantic key normalization, one/two tick catch-up, late-frame dropping, pause behavior, and cleanup after exceptions.
- [x] Run `python -m unittest tests.test_terminal tests.test_realtime -v` and confirm RED.
- [x] Implement platform adapters, cursor-safe presentation, terminal sizing, and the fixed-step runner without calling `clear_screen()` per tick.
- [x] Run focused tests and compile the new modules.
- [x] Refactor only after tests pass; keep `ui.py` limited to generic static helpers.

### Task 3: Real-Time Snake

**Files:**
- Modify: `console_gg/games/snake.py`
- Modify: `play_snake.py`
- Modify: `console_gg/stats.py`
- Test: `tests/test_snake.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Preserve `SnakeState`, `move_snake`, `normalize_direction`, `turn_direction`, and existing behavior tests.
- Add `SnakeConfig(width: int, height: int, tick_ms: int, label: str)`.
- Add `handle_events(state, events) -> state`, `tick(state, randomizer) -> state`, and `render_realtime(state, message) -> str`.

- [x] Add failing tests for automatic ticks, at-most-two-turn buffering, speed/size presets, pause/quit events, and best-score recording.
- [x] Run `python -m unittest tests.test_snake -v` and confirm the new tests fail before production changes.
- [x] Integrate Snake with `TerminalSession` and `run_realtime`, preserving the line-input step fallback.
- [x] Run all Snake and stats tests with `NO_COLOR=1` behavior covered.
- [x] Refactor rendering to fit Compact 16x10 and Standard 24x14 boards without flicker.

### Task 4: Block Dropper

**Files:**
- Create: `console_gg/games/block_dropper.py`
- Create: `play_block_dropper.py`
- Modify: `console_gg/catalog.py`
- Modify: `console_gg/stats.py`
- Test: `tests/test_block_dropper.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- `Piece(kind: str, cells: tuple[tuple[int, int], ...])`.
- `BlockDropperState` stores board, active piece, next piece, score, level, lines, gravity, and game status.
- `new_state(piece_source=None) -> BlockDropperState`.
- Pure functions: `move_piece`, `rotate_piece`, `soft_drop`, `hard_drop`, `lock_piece`, `clear_lines`, `tick`, `handle_events`, `render_game`.

- [x] Add failing tests for deterministic seven-piece bag order, rotation/collision, line clear scoring, soft/hard drop scoring, ghost position, and game over.
- [x] Run `python -m unittest tests.test_block_dropper -v` and confirm RED.
- [x] Implement the 10x20 board, kick list, gravity/level rules, next preview, ghost piece, and real-time controls.
- [x] Add stats and standalone launcher, then run focused tests and a non-interactive render smoke test.
- [x] Refactor duplicate board helpers only after green.

### Task 5: Campo Minato

**Files:**
- Create: `console_gg/games/minesweeper.py`
- Create: `play_minesweeper.py`
- Modify: `console_gg/catalog.py`
- Modify: `console_gg/stats.py`
- Test: `tests/test_minesweeper.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- `Difficulty(name: str, width: int, height: int, mines: int)`.
- `MinesweeperState` stores seeded mines, revealed cells, flags, cursor, actions, elapsed time, and outcome.
- `new_state(difficulty, seed=None) -> MinesweeperState`.
- Pure functions: `reveal`, `toggle_flag`, `move_cursor`, `neighbor_count`, `check_outcome`, `parse_command`, `render_game`.

- [x] Add failing tests for first-click safety, neighbor counts, iterative flood-fill, flags, cursor movement, win/loss, and `B4`/`F B4` fallback parsing.
- [x] Run `python -m unittest tests.test_minesweeper -v` and confirm RED.
- [x] Implement Facile 9x9/10, Medio 16x16/40, and Difficile 30x16/99 with stable cell rendering.
- [x] Add TTY single-key loop, line-input fallback, records per difficulty, launcher, and catalog entry.
- [x] Run focused tests plus rendering checks under `NO_COLOR=1`.

### Task 6: Battaglia Navale

**Files:**
- Create: `console_gg/games/battleship.py`
- Create: `play_battleship.py`
- Modify: `console_gg/catalog.py`
- Modify: `console_gg/stats.py`
- Test: `tests/test_battleship.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- `Ship(name: str, length: int, cells: tuple[tuple[int, int], ...], hits: frozenset[tuple[int, int]])`.
- `BattleshipState` stores player/enemy fleets, shots, cursor, turn, outcome, seed, and statistics.
- `place_fleet(seed, fleet_spec) -> tuple[Ship, ...]`.
- Pure functions: `fire`, `is_sunk`, `choose_computer_shot`, `move_target`, `render_boards`, `parse_coordinate`.

- [x] Add failing tests for non-overlapping 5/4/3/3/2 fleets, hit/miss/sunk resolution, public board projection, deterministic hunt/target AI, and coordinate parsing.
- [x] Run `python -m unittest tests.test_battleship -v` and confirm RED.
- [x] Implement dual-board rendering, reroll-before-first-shot, cursor/Space controls, fallback coordinates, and seeded cabinet AI.
- [x] Add stats and launcher, then run focused tests and a deterministic full-game smoke test.
- [x] Refactor board projection helpers only after green.

### Task 7: Blackjack And Dungeon Upgrades

**Files:**
- Modify: `console_gg/games/blackjack.py`
- Modify: `console_gg/games/dungeon.py`
- Modify: `console_gg/stats.py`
- Test: `tests/test_blackjack.py`
- Test: `tests/test_dungeon.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Blackjack adds `Shoe`, `can_double_down`, `double_down`, and round delta rendering while preserving `round_result` and `settle_chips`.
- Dungeon extends `Boss` with an intent/phase state and adds `next_boss_intent`, `find_path`, and `choose_portal_boon`.

- [x] Add failing tests for four-deck shoe reuse/reshuffle, legal double down, one-card auto-stand, payout delta, boss intents, phase transition, BFS pursuit, boon values, and records.
- [x] Run `python -m unittest tests.test_blackjack tests.test_dungeon -v` and confirm RED for the new behaviors.
- [x] Implement the smallest rule changes compatible with the existing rank-only cards, standard pushes, endless dungeon progression, secret doors, armor, shrines, and carried gear.
- [x] Run focused tests and verify old Blackjack/Dungeon tests remain green.
- [x] Refactor render helpers to show intent, phase, cards remaining, and round deltas clearly.

### Task 8: Integration, Documentation, And Regression

**Files:**
- Modify: `README.md`
- Modify: all relevant `play_*.py` launchers
- Modify: `console_gg/catalog.py`, `console_gg/shell.py`, `console_gg/stats.py`
- Test: `tests/test_main_menu.py`, `tests/test_catalog.py`, `tests/test_shell.py`

- [x] Add failing integration tests for all ten catalog entries, direct launcher preservation, records/help routing, and one post-game acknowledgement.
- [x] Run `python -m unittest discover -s tests -p "test*.py" -v` to establish the final RED/green target after integration wiring.
- [x] Update README controls, game list, stats path, terminal fallback behavior, and Alien Attack deferral.
- [x] Run `python -m unittest discover -s tests -p "test*.py" -v` and require zero failures.
- [x] Run `python -m compileall -q .`.
- [x] Run `git diff --check -- console-gg` and inspect changed files for accidental artifacts.

## Review Gates

After each task, record the focused test command and result, inspect the changed
files, and run a task-scoped review before proceeding. At the end, run a whole-
branch review for cross-game input conflicts, stats schema compatibility,
terminal cleanup, menu launch routing, and unimplemented catalog entries.
