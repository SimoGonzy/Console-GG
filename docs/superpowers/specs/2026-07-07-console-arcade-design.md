# Console GG Retro Arcade Design

## Goal

Build a small Python console arcade with four games: 2048, Blackjack, Dungeon, and Wordle.
The project should be fun to open when bored, with a retro terminal style that feels consistent across all games.

## Selected Approach

Use both a shared launcher and individual game entry points:

- `python main.py` opens the retro arcade menu.
- `python play_2048.py`, `python play_blackjack.py`, `python play_dungeon.py`, and `python play_wordle.py` start a single game directly.

## Architecture

The project uses a small package named `console_gg`.

- `console_gg/ui.py` owns the shared retro console style: ANSI colors, framed panels, title screens, menus, prompts, pauses, and table rendering.
- `console_gg/games/*.py` owns one game each, with pure logic functions plus a `play()` loop for terminal interaction.
- Root scripts are thin wrappers around the package modules.
- Tests focus on pure logic, not interactive input.

## Console Style

The style should feel like a compact terminal arcade:

- ASCII borders and title blocks.
- Bright cyan, magenta, yellow, green, red, and dim gray ANSI colors.
- Clear status panels for score, health, chips, attempts, or inventory.
- Inputs shown as concise command prompts.
- Invalid input handled without crashing.
- No mandatory third-party dependencies.
- Respect `NO_COLOR` by disabling ANSI colors.

## Game Requirements

### 2048

- 4x4 board.
- WASD movement.
- Tile merging follows normal 2048 rules.
- Score increases by merged tile values.
- New tiles spawn after valid moves.
- Win at 2048, lose when no moves remain.

### Blackjack

- Player starts with a chip balance.
- Support hit, stand, and quit.
- Dealer hits until at least 17.
- Aces count as 11 or 1 to avoid busting where possible.
- Round results update chips.

### Dungeon

- ASCII grid dungeon.
- Player, exit, walls, monsters, potions, and treasure.
- WASD movement.
- Moving into monsters triggers simple combat.
- Reaching the exit wins if the player survives.

### Wordle

- Five-letter words.
- Six attempts.
- Duplicate letters evaluated correctly.
- Feedback categories: correct, present, absent.
- Display previous guesses with colored feedback.

## Testing

Use only Python's standard `unittest` runner:

```powershell
python -m unittest discover -s tests -p "test*.py" -v
```

Tests should cover each game's core rules and the shared UI helpers.
