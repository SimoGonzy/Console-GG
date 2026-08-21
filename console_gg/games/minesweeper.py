"""Campo Minato rules plus terminal play modes for Console GG."""

from __future__ import annotations

from dataclasses import dataclass, replace
import random
import time
from typing import Any

from console_gg.realtime import run_realtime
from console_gg.stats import load_stats, record_metric, record_outcome, save_stats
from console_gg.terminal import supports_realtime
from console_gg.ui import ANSI_RE, clear_screen, color, frame, pause, safe_input


Position = tuple[int, int]
PRESETS = {"facile": (9, 9, 10), "medio": (16, 16, 40), "difficile": (30, 16, 99)}
NUMBER_COLORS = {1: "cyan", 2: "green", 3: "red", 4: "magenta", 5: "yellow", 6: "cyan", 7: "white", 8: "dim"}


@dataclass(frozen=True)
class MineState:
    """Immutable state for one Campo Minato board."""

    width: int
    height: int
    mine_count: int
    mines: frozenset[Position]
    revealed: frozenset[Position]
    flags: frozenset[Position]
    cursor: Position
    started_at: float | None
    elapsed_ms: int
    alive: bool
    won: bool
    quit_requested: bool
    mines_placed: bool


def new_state(difficulty: str = "difficile") -> MineState:
    """Create a blank board for one of the supported difficulty presets."""
    try:
        width, height, mine_count = PRESETS[difficulty.lower()]
    except (AttributeError, KeyError) as error:
        raise ValueError(f"unknown difficulty: {difficulty}") from error
    return MineState(
        width=width,
        height=height,
        mine_count=mine_count,
        mines=frozenset(),
        revealed=frozenset(),
        flags=frozenset(),
        cursor=(0, 0),
        started_at=None,
        elapsed_ms=0,
        alive=True,
        won=False,
        quit_requested=False,
        mines_placed=False,
    )


def place_mines(
    state: MineState,
    first_click: Position,
    randomizer: Any | None = None,
) -> MineState:
    """Place the preset mine count while protecting the first-click neighborhood."""
    if state.mines_placed or not _in_bounds(state, first_click):
        return state

    protected = {first_click, *_neighbors(state, first_click)}
    candidates = [position for position in _all_positions(state) if position not in protected]
    if len(candidates) < state.mine_count:
        candidates = [position for position in _all_positions(state) if position != first_click]
    if len(candidates) < state.mine_count:
        raise ValueError("board does not have enough cells for its mine count")

    rng = randomizer if randomizer is not None else random
    mines = frozenset(rng.sample(candidates, state.mine_count))
    return replace(state, mines=mines, mines_placed=True)


def neighbor_count(state: MineState, position: Position) -> int:
    """Return the number of mines touching one in-bounds cell."""
    if not _in_bounds(state, position):
        return 0
    return sum(neighbor in state.mines for neighbor in _neighbors(state, position))


def reveal_cell(
    state: MineState,
    position: Position,
    randomizer: Any | None = None,
) -> MineState:
    """Reveal a cell, flood-filling safe zeroes without mutating the source state."""
    if _is_terminal(state) or not _in_bounds(state, position) or position in state.flags:
        return state

    prepared = place_mines(state, position, randomizer)
    if position in prepared.revealed:
        return prepared
    started = prepared.started_at if prepared.started_at is not None else time.monotonic()
    prepared = replace(prepared, started_at=started)

    if position in prepared.mines:
        revealed = prepared.revealed | {position}
        return replace(
            prepared,
            revealed=frozenset(revealed),
            alive=False,
            elapsed_ms=_elapsed_ms(prepared),
        )

    revealed = set(prepared.revealed)
    pending = [position]
    while pending:
        current = pending.pop()
        if current in revealed or current in prepared.mines or current in prepared.flags:
            continue
        revealed.add(current)
        if neighbor_count(prepared, current) == 0:
            pending.extend(neighbor for neighbor in _neighbors(prepared, current) if neighbor not in revealed)

    revealed_state = replace(prepared, revealed=frozenset(revealed))
    if has_won(revealed_state):
        return replace(revealed_state, won=True, elapsed_ms=_elapsed_ms(revealed_state))
    return revealed_state


def toggle_flag(state: MineState, position: Position) -> MineState:
    """Add or remove one flag, refusing terminal, revealed, and invalid cells."""
    if _is_terminal(state) or not _in_bounds(state, position) or position in state.revealed:
        return state
    flags = set(state.flags)
    if position in flags:
        flags.remove(position)
    else:
        flags.add(position)
    return replace(state, flags=frozenset(flags))


def move_cursor(state: MineState, direction: str) -> MineState:
    """Move the cursor one cell, clamped to the visible board."""
    offsets = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
    offset = offsets.get(direction.lower()) if isinstance(direction, str) else None
    if offset is None or _is_terminal(state):
        return state
    x = min(max(0, state.cursor[0] + offset[0]), state.width - 1)
    y = min(max(0, state.cursor[1] + offset[1]), state.height - 1)
    return replace(state, cursor=(x, y))


def parse_command(raw: str) -> tuple[str, Position] | None:
    """Parse line-input coordinates such as ``B4`` and ``F B4``."""
    if not isinstance(raw, str):
        return None
    pieces = raw.strip().upper().split()
    action = "reveal"
    if len(pieces) == 2 and pieces[0] == "F":
        action = "flag"
        coordinate = pieces[1]
    elif len(pieces) == 1:
        coordinate = pieces[0]
    else:
        return None

    split_at = 0
    while split_at < len(coordinate) and coordinate[split_at].isalpha():
        split_at += 1
    column_text, row_text = coordinate[:split_at], coordinate[split_at:]
    if not column_text or not row_text.isdigit() or int(row_text) < 1:
        return None

    column = 0
    for letter in column_text:
        if not "A" <= letter <= "Z":
            return None
        column = column * 26 + ord(letter) - ord("A") + 1
    return action, (column - 1, int(row_text) - 1)


def has_won(state: MineState) -> bool:
    """Return whether every non-mine cell has been revealed."""
    if not state.mines_placed or not state.alive:
        return False
    safe_cells = set(_all_positions(state)) - set(state.mines)
    return safe_cells.issubset(state.revealed)


def highlighted_candidates(state: MineState) -> frozenset[Position]:
    """Return covered cells around the revealed number under the cursor."""
    if _is_terminal(state) or state.cursor not in state.revealed:
        return frozenset()
    if neighbor_count(state, state.cursor) == 0:
        return frozenset()
    return frozenset(neighbor for neighbor in _neighbors(state, state.cursor) if neighbor not in state.revealed)


def render_game(state: MineState, reveal_mines: bool = False) -> str:
    """Render a compact fixed-cell board with ANSI colors that preserve its layout."""
    row_width = max(2, len(str(state.height)))
    header = " " * (row_width + 1) + "".join(_column_label(x).rjust(2) for x in range(state.width))
    rows = [header]
    exploded = min((position for position in state.revealed if position in state.mines), default=None)
    highlights = highlighted_candidates(state)
    for y in range(state.height):
        cells = "".join(_cell_token(state, (x, y), exploded, reveal_mines, highlights) for x in range(state.width))
        rows.append(f"{y + 1:>{row_width}} {cells}")

    flags_remaining = state.mine_count - len(state.flags)
    status = "VITTORIA" if state.won else "ESPLOSO" if not state.alive else "IN CORSO"
    status_color = "green" if state.won else "red" if not state.alive else "yellow"
    hud = f"Mine {flags_remaining:03d}  Tempo {_elapsed_ms(state) // 1000:04d}s  {color(status, status_color)}"
    controls = "WASD/Frecce muovi  SPAZIO apri  F bandiera  R ricomincia  Q esci"
    body = [hud, controls, "", *rows]
    widest = max(len(ANSI_RE.sub("", line)) for line in body)
    return frame("CAMPO MINATO", body, width=max(62, widest + 3))


def _handle_events(
    state: MineState,
    keys: list[str],
    randomizer: Any | None = None,
) -> MineState:
    """Apply semantic Windows key controls without consuming line-input commands."""
    current = state
    for raw_key in keys:
        key = raw_key.lower() if isinstance(raw_key, str) else ""
        command = key.strip()
        if command in {"q", "quit", "exit"}:
            return replace(current, quit_requested=True)
        if command == "r":
            current = new_state(_difficulty_for_state(current))
            continue
        if command in {"w", "up"}:
            current = move_cursor(current, "up")
        elif command in {"a", "left"}:
            current = move_cursor(current, "left")
        elif command in {"s", "down"}:
            current = move_cursor(current, "down")
        elif command == "d" or command == "right":
            current = move_cursor(current, "right")
        elif command == "f":
            current = toggle_flag(current, current.cursor)
        elif key == " " or command in {"space", "enter"}:
            current = reveal_cell(current, current.cursor, randomizer)
        if _is_terminal(current):
            break
    return current


def _play_realtime() -> None:
    """Run the Windows single-key version through the shared semantic input loop."""
    difficulty = _choose_difficulty()
    rng = random.Random()
    stats = load_stats()
    initial = new_state(difficulty)
    frame_size = _frame_size(initial)
    final = run_realtime(
        initial,
        lambda state, keys: _handle_events(state, keys, rng),
        lambda state: state,
        render_game,
        lambda state: state.quit_requested or _is_terminal(state),
        0.08,
        minimum_size=frame_size,
        render_final=True,
        idle_render_period=0.35,
    )
    if final.quit_requested:
        print("Partita interrotta.")
        return
    _record_completed_game(final, stats)
    print("Campo ripulito!" if final.won else "Hai trovato una mina.")


def _play_step_mode() -> None:
    """Run coordinate commands when the shared Windows key backend is unavailable."""
    difficulty = _choose_difficulty()
    rng = random.Random()
    stats = load_stats()
    state = new_state(difficulty)
    message = "Apri con B4 o marca con F B4."

    while True:
        clear_screen()
        print(render_game(state))
        if _is_terminal(state):
            _record_completed_game(state, stats)
            print("Campo ripulito!" if state.won else "Hai trovato una mina.")
            return

        raw = safe_input(f"{message}\nComando > ", default="q")
        command = raw.strip().lower()
        if command in {"q", "quit", "exit"}:
            print("Partita interrotta.")
            return
        if command == "r":
            state = new_state(difficulty)
            message = "Nuova partita."
            continue

        parsed = parse_command(raw)
        if parsed is None:
            message = "Comando non valido. Usa B4, F B4, R o Q."
            continue
        action, position = parsed
        before = state
        state = reveal_cell(state, position, rng) if action == "reveal" else toggle_flag(state, position)
        message = "Casella aggiornata." if state is not before else "Coordinata fuori campo o casella bloccata."


def play() -> None:
    """Choose single-key Windows play or the complete coordinate fallback."""
    if supports_realtime():
        _play_realtime()
        return
    _play_step_mode()


def main() -> None:
    """Run the standalone game and own its sole acknowledgement prompt."""
    play()
    pause()


def _record_completed_game(state: MineState, stats: dict | None = None) -> None:
    """Persist exactly one completed win or loss, never an abandoned board."""
    if state.quit_requested or not state.mines_placed or (state.alive and not state.won):
        return
    game_stats = stats if stats is not None else load_stats()
    record_outcome(game_stats, "minesweeper", won=state.won)
    if state.won:
        metric = f"best_time_{_difficulty_for_state(state)}"
        record_metric(game_stats, "minesweeper", "best_time", state.elapsed_ms, lower_is_better=True)
        record_metric(game_stats, "minesweeper", metric, state.elapsed_ms, lower_is_better=True)
    save_stats(game_stats)


def _choose_difficulty() -> str:
    raw = safe_input("Difficolta [facile/medio/difficile] (difficile) > ", default="difficile")
    selected = raw.strip().lower()
    return selected if selected in PRESETS else "difficile"


def _frame_size(state: MineState) -> tuple[int, int]:
    rendered = render_game(state)
    return max(len(ANSI_RE.sub("", line)) for line in rendered.splitlines()), len(rendered.splitlines())


def _cell_token(
    state: MineState,
    position: Position,
    exploded: Position | None,
    reveal_mines: bool,
    highlights: frozenset[Position] = frozenset(),
) -> str:
    marker = ">" if position == state.cursor else " "
    if not state.alive and position in state.flags and position not in state.mines:
        token = color("!", "red")
    elif position == exploded:
        token = color("X", "red")
    elif (reveal_mines or not state.alive) and position in state.mines:
        token = color("*", "red")
    elif position in state.flags:
        token = color("F", "orange")
    elif position not in state.revealed:
        token = color("#", "yellow" if position in highlights else "dim")
    else:
        count = neighbor_count(state, position)
        token = "." if count == 0 else color(str(count), NUMBER_COLORS[count])
    return marker + token


def _all_positions(state: MineState) -> tuple[Position, ...]:
    return tuple((x, y) for y in range(state.height) for x in range(state.width))


def _column_label(index: int) -> str:
    value = index + 1
    letters = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _difficulty_for_state(state: MineState) -> str:
    for name, preset in PRESETS.items():
        if (state.width, state.height, state.mine_count) == preset:
            return name
    return "difficile"


def _elapsed_ms(state: MineState) -> int:
    if state.started_at is None or _is_terminal(state):
        return state.elapsed_ms
    return state.elapsed_ms + max(0, int((time.monotonic() - state.started_at) * 1000))


def _in_bounds(state: MineState, position: Position) -> bool:
    try:
        x, y = position
    except (TypeError, ValueError):
        return False
    return isinstance(x, int) and isinstance(y, int) and 0 <= x < state.width and 0 <= y < state.height


def _is_terminal(state: MineState) -> bool:
    return state.quit_requested or not state.alive or state.won


def _neighbors(state: MineState, position: Position) -> tuple[Position, ...]:
    x, y = position
    return tuple(
        (neighbor_x, neighbor_y)
        for neighbor_y in range(y - 1, y + 2)
        for neighbor_x in range(x - 1, x + 2)
        if (neighbor_x, neighbor_y) != position and _in_bounds(state, (neighbor_x, neighbor_y))
    )


if __name__ == "__main__":
    main()
