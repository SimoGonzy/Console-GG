# Console GG Arcade Expansion Design

## Goal

Turn Console GG from a flat collection of seven games into a cohesive, scalable
retro arcade with ten polished games, a compact catalog, shared records, and a
reusable real-time terminal loop.

The expansion adds three original implementations:

- Block Dropper, a falling-block arcade puzzle.
- Campo Minato, a cursor-driven minesweeper game.
- Battaglia Navale, a player-versus-cabinet naval strategy game.

It also upgrades Snake to true real-time play and gives focused replayability
improvements to Blackjack and Dungeon.

## Design Principles

- Preserve the existing Python standard-library-only constraint.
- Keep every game directly launchable as well as available from `main.py`.
- Use original text, layouts, glyphs, and animations. The referenced website is
  genre-level inspiration only; no source code or ASCII artwork will be copied.
- Keep game rules in pure, deterministic functions wherever possible.
- Optimize the interactive path for Windows terminals while retaining safe
  fallbacks for non-TTY and unsupported terminals.
- Prefer readable, stable screens over decorative density.

## Release Scope

### Included

- A compact category-grouped main catalog.
- Per-game help and a global records screen.
- Shared nonblocking terminal input and fixed-step real-time scheduling.
- True real-time Snake with size and speed presets.
- Block Dropper.
- Campo Minato.
- Battaglia Navale.
- Blackjack double down, persistent shoe, clearer payout feedback, and records.
- Dungeon boss intents, phase changes, obstacle-aware pursuit, portal boons, and
  run records.
- Statistics for all ten games.

### Deferred

- Alien Attack. It will be the first candidate for the next expansion after the
  real-time loop has been proven by Snake and Block Dropper.
- Network leaderboards, accounts, sound, external assets, and dependencies.
- Blackjack insurance, surrender, split hands, displayed suits, or hidden odds
  manipulation. Equal totals remain a push.
- Dungeon save/resume, story campaigns, and additional inventory screens.
- Block Dropper hold-piece mechanics.

## Arcade Shell

The catalog remains a single screen. Categories organize the games without
adding another navigation step.

```text
+----------------------------------------------------------------------+
| CONSOLE GG                                               10 GIOCHI   |
+======================================================================+
| ROMPICAPO   [1] 2048       [2] Wordle      [3] Campo Minato          |
| TAVOLO      [4] Blackjack  [5] Tris        [6] Forza 4               |
|             [7] Battaglia Navale                                    |
| ARCADE      [8] Snake      [9] Block Dropper                         |
| AVVENTURA  [10] Dungeon                                              |
+----------------------------------------------------------------------+
| [1-10] GIOCA       [H] GUIDA       [R] RECORD       [Q] ESCI         |
+----------------------------------------------------------------------+
```

The shell uses line input because two-digit selections and redirected input need
to remain reliable. Games continue to use single-key input where appropriate.

### Modules

- `console_gg/catalog.py` owns an explicit ordered registry of `GameSpec`
  entries. A spec contains a stable id, title, category, short description,
  module path, control summary, and stats key.
- `console_gg/shell.py` owns the main loop, command parsing, compact catalog,
  help view, records view, and lazy game launching.
- `main.py` becomes a thin entry point and temporarily exposes the current
  three-tuple `GAMES` projection for compatibility with existing tests.
- `console_gg/ui.py` remains a generic static rendering module. Only reusable
  visible-width, wrapping, and terminal-size helpers belong there.

Every game keeps `play() -> None` and its standalone launcher. The shell owns
the acknowledgement after a game returns; games render their final state and
return without adding a second menu pause.

The new game modules are `console_gg/games/block_dropper.py`,
`console_gg/games/minesweeper.py`, and `console_gg/games/battleship.py`. Their
standalone entry points are `play_block_dropper.py`, `play_minesweeper.py`, and
`play_battleship.py`.

## Real-Time Terminal Foundation

### `console_gg/terminal.py`

This module owns terminal-specific behavior:

- Semantic key events rather than raw platform key codes.
- Nonblocking Windows input using `msvcrt.kbhit()` and `getwch()`.
- Best-effort POSIX input using standard-library `select` and `termios`.
- Terminal dimensions.
- Cursor hide, cursor restore, cursor-home, and full-frame presentation.
- Input draining and flushing when leaving a real-time game.

Cursor and terminal state are restored in `finally`, including after errors.
Unsupported or non-interactive terminals use each game's existing line-input or
step-mode fallback.

### `console_gg/realtime.py`

This module owns a fixed-step scheduler based on `time.perf_counter()`.

The runner receives injected clock, sleeper, input, output, and randomness in
tests. It performs at most two catch-up ticks after a stall, then drops excess
elapsed time so a delayed terminal does not cause an uncontrollable burst.

Real-time games expose the following conceptual boundary:

```text
handle_events(state, events) -> state
tick(state, random_source) -> state
render(state, viewport) -> str
tick_period(state) -> float
is_finished(state) -> bool
```

Frames are composed completely and written in one operation from cursor-home.
The screen is not cleared with `cls` on every tick, avoiding visible flicker.
When the terminal is too small, simulation pauses and a stable resize message is
shown until the required dimensions are available.

## Game Designs

### Snake

- Preserve the immutable `SnakeState` and pure movement rules.
- Move automatically on a selected speed: Relax at 250 ms, Arcade at 160 ms,
  or Turbo at 95 ms per movement tick.
- Offer Compact at 16 by 10 and Standard at 24 by 14 cells.
- Queue at most two legal turns so fast corner input is retained without
  allowing an immediate reversal.
- Controls: WASD or arrows, `P` pause, `Q` quit.
- Show score, length, speed, and best score in a compact HUD.
- Keep the current step-based loop as the fallback when real-time input is not
  available.

### Block Dropper

- Use a 10 by 20 board and a deterministic injectable seven-piece bag.
- Support left/right movement, rotation with a small deterministic kick list,
  soft drop, hard drop, pause, and quit.
- Implement piece locking, line clearing, next-piece preview, ghost landing
  position, score, levels, and increasing gravity.
- Award 100, 300, 500, or 800 points times the current level for clearing one,
  two, three, or four lines. Soft drop awards one point per cell and hard drop
  awards two. The level increases after every ten cleared lines.
- Controls: `A`/`D` move, `W` or up rotates, `S` soft-drops, Space hard-drops,
  `P` pauses, and `Q` quits.
- Render board cells at a stable two-character width with an original limited
  ANSI palette and a `NO_COLOR` representation.

### Campo Minato

- Offer Facile at 9 by 9 with 10 mines, Medio at 16 by 16 with 40 mines, and
  Difficile at 30 by 16 with 99 mines.
- Place mines only after the first reveal so the opening move is always safe.
- Use an iterative flood-fill for empty regions.
- Primary TTY controls: WASD or arrows move the cursor, Space reveals, `F`
  toggles a flag, `R` restarts, and `Q` quits.
- Line-input fallback accepts coordinates such as `B4` and `F B4`.
- Render hidden cells, flags, exploded mines, incorrect flags, and colored
  neighbor counts distinctly.
- Track wins and best completion time per difficulty.

### Battaglia Navale

- Use two 10 by 10 boards shown side by side when terminal width permits and
  stacked otherwise.
- Use a five-ship fleet with lengths 5, 4, 3, 3, and 2. Ships may touch but may
  not overlap, and each side fires exactly once per turn.
- Auto-place both fleets from an injected random source. Before the first shot,
  the player can reroll their fleet rather than navigating a placement editor.
- Use a deterministic hunt/target cabinet AI: checkerboard search while hunting,
  then adjacent and directional follow-up after a hit.
- TTY controls move a targeting cursor with WASD/arrows and fire with Space.
  The fallback accepts coordinates such as `C7`.
- Clearly distinguish water, miss, hit, sunk ship, current target, and the
  player's own intact ships.
- Track games, wins, best winning shot count, and hit accuracy.

## Existing Game Upgrades

### Blackjack

- Keep rank-only cards and the current deliberate deal/reveal timing.
- Keep standard pushes for tied totals and 3:2 natural blackjack payout.
- Add double down only when the player has two cards and enough chips. It doubles
  the wager, deals one card, and automatically stands.
- Keep one four-deck shuffled shoe across rounds and reshuffle before a round
  when fewer than 52 cards remain.
- Show cards remaining and the round delta, for example `BET 20 -> +30`.
- Track rounds, wins, pushes, best bankroll, and best winning streak.

### Dungeon

- Give each boss a deterministic repeating intent sequence such as Strike,
  Guard, Charge, and Heavy Attack.
- Display the next intent before the player's action so Defend becomes tactical.
- Change the final boss behavior and original portrait at 50 percent health or
  lower.
- Replace direct-axis pursuit with obstacle-aware breadth-first pathfinding.
- After clearing a dungeon, offer one portal boon: maximum health, attack, or
  defense. The fixed rewards are +4 maximum health with four health restored,
  +1 attack, or +1 defense. The choice applies before generating the next level.
- Preserve endless dungeon progression, carried gear, secret-door guarantees,
  and current battle actions.
- Track best score, deepest dungeon, and bosses defeated.

## Statistics And Records

The existing `console_gg_stats.json` path and merge behavior remain compatible.
Existing 2048 and Wordle keys and public functions are preserved.

Every game receives at least `games` and a meaningful record:

- 2048: current existing score, tile, and win records.
- Wordle: current existing streak and guess distribution.
- Blackjack: wins, pushes, bankroll, and streak.
- Dungeon: score, depth, and bosses.
- Tris and Forza 4: wins, losses, and draws.
- Snake: best score and longest length.
- Block Dropper: best score, level, and lines.
- Campo Minato: wins and best time per difficulty.
- Battaglia Navale: wins, fewest shots, and accuracy.

The records screen loads the file each time it opens and displays one primary
metric per game. Game modules still record their own result so standalone
launchers behave identically to shell launches. Quitting a game does not count
as a completed result.

## Error Handling And Compatibility

- Invalid input shows a concise status message and does not mutate game state.
- Empty stdin returns safely to the shell or uses the existing default behavior.
- Corrupt or missing stats files fall back to merged defaults as they do now.
- Random games accept a seed or injected random source for deterministic tests.
- Rendering respects `NO_COLOR` and fixed visible widths.
- Existing launch scripts remain supported.
- Current public logic helpers remain stable unless a test-backed compatibility
  wrapper is provided.

## Testing Strategy

Implementation follows test-driven development. New tests cover:

- Catalog ordering, category rendering, help, records, and shell command parsing.
- Terminal key normalization, cursor cleanup, resize behavior, and input flush.
- Real-time scheduling with fake clocks, late frames, pause, and bounded catch-up.
- Snake turn buffering and real-time integration without real sleeping.
- Block Dropper rotation, collision, locking, line clearing, bag order, scoring,
  ghost position, and game-over detection.
- Campo Minato first-click safety, mine counts, flood-fill, flags, win/loss,
  command parsing, and rendering.
- Battaglia Navale placement, shots, sunk ships, public board projection, cabinet
  hunt/target behavior, fallback parsing, and rendering.
- Blackjack action legality, double down, shoe lifecycle, settlement, records,
  and unchanged push behavior.
- Dungeon boss intents, phase transition, pathfinding, boon selection,
  progression, and records.
- Backward compatibility for the existing 101 tests.

Final verification runs:

```powershell
python -m unittest discover -s tests -p "test*.py" -v
python -m compileall -q .
```

## Implementation Sequence

1. Catalog, shell, and compatibility layer.
2. Terminal and real-time infrastructure.
3. Real-time Snake upgrade.
4. Block Dropper.
5. Campo Minato.
6. Battaglia Navale.
7. Blackjack and Dungeon upgrades.
8. Complete records integration, README, launchers, and full regression pass.

Independent game modules use disjoint file ownership so subagents can implement
them in parallel after shared interfaces are established.
