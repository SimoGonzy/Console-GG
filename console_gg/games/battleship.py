"""Battaglia Navale rules and terminal play modes for Console GG."""

from __future__ import annotations

from dataclasses import dataclass, replace
import random
import time
from typing import Any

from console_gg.stats import load_stats, record_metric, record_outcome, save_stats
from console_gg.terminal import TerminalScreen, poll_keys, supports_realtime
from console_gg.ui import ANSI_RE, clear_screen, color, pause, safe_input


Position = tuple[int, int]
BOARD_SIZE = 10
FLEET_LENGTHS = (5, 4, 3, 3, 2)
_COLUMN_LABELS = tuple(chr(ord("A") + index) for index in range(BOARD_SIZE))
_MOVE_OFFSETS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}


@dataclass(frozen=True)
class Ship:
    cells: tuple[Position, ...]
    hits: frozenset[Position] = frozenset()


@dataclass(frozen=True)
class FleetBoard:
    ships: tuple[Ship, ...]
    misses: frozenset[Position] = frozenset()


@dataclass(frozen=True)
class BattleState:
    player_board: FleetBoard
    enemy_board: FleetBoard
    target: Position
    player_shots: frozenset[Position]
    enemy_shots: tuple[Position, ...]
    turn: str
    game_over: bool
    player_won: bool
    quit_requested: bool
    shots_taken: int


def place_fleet(randomizer: Any | None = None) -> FleetBoard:
    """Place the standard fleet with deterministic injected randomness."""
    rng = randomizer if randomizer is not None else random.Random()
    occupied: set[Position] = set()
    ships: list[Ship] = []

    for length in FLEET_LENGTHS:
        candidates: list[tuple[Position, bool]] = []
        for horizontal in (True, False):
            limit_x = BOARD_SIZE - length if horizontal else BOARD_SIZE - 1
            limit_y = BOARD_SIZE - 1 if horizontal else BOARD_SIZE - length
            for y in range(limit_y + 1):
                for x in range(limit_x + 1):
                    cells = _ship_cells((x, y), length, horizontal)
                    if occupied.isdisjoint(cells):
                        candidates.append(((x, y), horizontal))

        origin, horizontal = _choose(rng, candidates)
        cells = _ship_cells(origin, length, horizontal)
        occupied.update(cells)
        ships.append(Ship(cells=cells))

    return FleetBoard(ships=tuple(ships))


def fire(board: FleetBoard, position: Position) -> tuple[FleetBoard, str]:
    """Fire at one cell and return the new board plus one exact outcome token."""
    if not _in_bounds(position) or _shot_already(board, position):
        return board, "repeat"

    for index, ship in enumerate(board.ships):
        if position not in ship.cells:
            continue
        hits = frozenset(set(ship.hits) | {position})
        updated_ship = replace(ship, hits=hits)
        ships = list(board.ships)
        ships[index] = updated_ship
        status = "sunk" if len(updated_ship.hits) == len(updated_ship.cells) else "hit"
        return replace(board, ships=tuple(ships)), status

    return replace(board, misses=frozenset(set(board.misses) | {position})), "miss"


def all_sunk(board: FleetBoard) -> bool:
    """Return whether every ship on the fleet board has been sunk."""
    return all(len(ship.hits) == len(ship.cells) for ship in board.ships)


def public_board(board: FleetBoard) -> FleetBoard:
    """Hide intact enemy hulls while preserving revealed hit and sunk information."""
    projected = []
    for ship in board.ships:
        if len(ship.hits) == len(ship.cells):
            projected.append(ship)
        else:
            projected.append(Ship(cells=tuple(), hits=ship.hits))
    return FleetBoard(ships=tuple(projected), misses=board.misses)


def parse_coordinate(raw: str) -> Position | None:
    """Parse fallback coordinates like C7 for the 10x10 board."""
    if not isinstance(raw, str):
        return None
    value = raw.strip().upper()
    if len(value) < 2 or len(value) > 3:
        return None
    column, row_text = value[:1], value[1:]
    if column not in _COLUMN_LABELS or not row_text.isdigit():
        return None
    row = int(row_text)
    if row < 1 or row > BOARD_SIZE:
        return None
    return (_COLUMN_LABELS.index(column), row - 1)


def move_target(state: BattleState, direction: str) -> BattleState:
    """Move the firing cursor one cell while clamping to the board."""
    offset = _MOVE_OFFSETS.get(direction.lower()) if isinstance(direction, str) else None
    if offset is None or state.game_over or state.quit_requested:
        return state
    x = min(max(0, state.target[0] + offset[0]), BOARD_SIZE - 1)
    y = min(max(0, state.target[1] + offset[1]), BOARD_SIZE - 1)
    return replace(state, target=(x, y))


def choose_cabinet_shot(
    state: BattleState,
    randomizer: Any | None = None,
) -> Position:
    """Pick one deterministic cabinet shot using hunt and target phases."""
    rng = randomizer if randomizer is not None else random.Random()
    shots = set(state.enemy_shots)
    target_ship = _latest_unsunk_player_ship(state)

    if target_ship is not None:
        target_hits = [shot for shot in state.enemy_shots if shot in target_ship.hits]
        aligned = _aligned_candidates(target_hits, shots)
        if aligned:
            return _choose(rng, aligned)
        neighbors = _neighbor_candidates(target_hits, shots)
        if neighbors:
            return _choose(rng, neighbors)

    checkerboard = [
        position
        for position in _all_positions()
        if position not in shots and (position[0] + position[1]) % 2 == 0
    ]
    if checkerboard:
        return _choose(rng, checkerboard)
    return _choose(rng, [position for position in _all_positions() if position not in shots])


def take_player_turn(
    state: BattleState,
    position: Position,
    randomizer: Any | None = None,
) -> BattleState:
    """Resolve exactly one player shot and, if needed, exactly one cabinet reply."""
    updated, _ = _take_player_turn_with_message(state, position, randomizer)
    return updated


def render_game(state: BattleState, terminal_columns: int = 72) -> str:
    """Render player and enemy boards side by side when possible, otherwise stacked."""
    player_lines = ["TUA FLOTTA", *_render_board(state.player_board, reveal_ships=True)]
    enemy_lines = [
        "CABINATO",
        *_render_board(
            public_board(state.enemy_board),
            reveal_ships=False,
            target=state.target if not state.game_over else None,
        ),
    ]
    status = _status_line(state)
    controls = _controls_line(realtime=supports_realtime())
    lines = [status, controls, ""]

    if terminal_columns >= 72:
        left_width = max(_visible_width(line) for line in player_lines)
        right_width = max(_visible_width(line) for line in enemy_lines)
        row_count = max(len(player_lines), len(enemy_lines))
        for index in range(row_count):
            left = player_lines[index] if index < len(player_lines) else ""
            right = enemy_lines[index] if index < len(enemy_lines) else ""
            lines.append(_pad_visible(left, left_width) + "    " + _pad_visible(right, right_width))
    else:
        lines.extend(player_lines)
        lines.append("")
        lines.extend(enemy_lines)

    return "\n".join(lines)


def play() -> None:
    """Choose semantic TTY play when available, otherwise accept typed coordinates."""
    if supports_realtime():
        _play_tty_mode()
        return
    _play_step_mode()


def main() -> None:
    """Run the standalone launcher and own the only acknowledgement prompt."""
    play()
    pause()


def _new_battle(randomizer: Any | None = None) -> BattleState:
    rng = randomizer if randomizer is not None else random.Random()
    return BattleState(
        player_board=place_fleet(rng),
        enemy_board=place_fleet(rng),
        target=(0, 0),
        player_shots=frozenset(),
        enemy_shots=tuple(),
        turn="player",
        game_over=False,
        player_won=False,
        quit_requested=False,
        shots_taken=0,
    )


def _take_player_turn_with_message(
    state: BattleState,
    position: Position,
    randomizer: Any | None = None,
) -> tuple[BattleState, str]:
    if state.game_over or state.quit_requested or not _in_bounds(position):
        return state, "Turno non valido."

    enemy_board, outcome = fire(state.enemy_board, position)
    if outcome == "repeat":
        return replace(state, enemy_board=enemy_board, target=position), "Coordinata gia usata."

    updated = replace(
        state,
        enemy_board=enemy_board,
        player_shots=frozenset(set(state.player_shots) | {position}),
        target=position,
        shots_taken=state.shots_taken + 1,
    )
    if all_sunk(enemy_board):
        return replace(updated, game_over=True, player_won=True), "Flotta nemica affondata."

    cabinet_shot = choose_cabinet_shot(updated, randomizer)
    player_board, cabinet_outcome = fire(updated.player_board, cabinet_shot)
    finished = replace(
        updated,
        player_board=player_board,
        enemy_shots=updated.enemy_shots + (cabinet_shot,),
        game_over=all_sunk(player_board),
        player_won=False if all_sunk(player_board) else updated.player_won,
        turn="player",
    )
    message = f"Tu: {outcome}. Cabinato: {cabinet_outcome} {_format_coordinate(cabinet_shot)}."
    if finished.game_over:
        message = "La tua flotta e stata affondata."
    return finished, message


def _play_step_mode() -> None:
    rng = random.Random()
    stats = load_stats()
    state = _new_battle(rng)
    message = "Inserisci C7 per sparare, R per cambiare flotta, Q per uscire."

    while True:
        clear_screen()
        print(render_game(state))
        if state.game_over:
            _record_completed_game(state, stats)
            print("Hai vinto!" if state.player_won else "Hai perso.")
            return

        raw = safe_input(f"{message}\nComando > ", default="q")
        command = raw.strip().lower()
        if command in {"q", "quit", "exit"}:
            print("Partita interrotta.")
            return
        if command == "r" and state.shots_taken == 0:
            state = replace(state, player_board=place_fleet(rng))
            message = "Flotta rimescolata."
            continue

        target = parse_coordinate(raw)
        if target is None:
            message = "Coordinata non valida. Usa C7, R o Q."
            continue
        state, message = _take_player_turn_with_message(state, target, rng)


def _play_tty_mode() -> None:
    rng = random.Random()
    stats = load_stats()
    state = _new_battle(rng)
    message = "WASD/Frecce muovi  SPAZIO fuoco  R cambia flotta  Q esci"

    with TerminalScreen() as screen:
        while True:
            columns, _ = screen.size()
            screen.render(render_game(state, terminal_columns=columns) + "\n\n" + message)
            if state.game_over or state.quit_requested:
                screen.finish()
                break

            keys = poll_keys()
            if not keys:
                time.sleep(0.05)
                continue
            state, message = _handle_keys(state, keys, rng)

    if state.quit_requested:
        print("Partita interrotta.")
        return
    _record_completed_game(state, stats)
    print("Hai vinto!" if state.player_won else "Hai perso.")


def _handle_keys(
    state: BattleState,
    keys: list[str],
    randomizer: Any | None = None,
) -> tuple[BattleState, str]:
    current = state
    message = "Bersaglio pronto."
    for key in keys:
        normalized = key.lower().strip() if isinstance(key, str) else ""
        if normalized in {"q", "quit", "exit"}:
            return replace(current, quit_requested=True), "Partita interrotta."
        if normalized == "r" and current.shots_taken == 0:
            return replace(current, player_board=place_fleet(randomizer)), "Flotta rimescolata."
        if normalized in {"w", "up"}:
            current = move_target(current, "up")
            continue
        if normalized in {"a", "left"}:
            current = move_target(current, "left")
            continue
        if normalized in {"s", "down"}:
            current = move_target(current, "down")
            continue
        if normalized in {"d", "right"}:
            current = move_target(current, "right")
            continue
        if key == " " or normalized in {"space", "enter"}:
            return _take_player_turn_with_message(current, current.target, randomizer)
    return current, message


def _record_completed_game(
    state: BattleState,
    stats: dict | None = None,
    *,
    hits: int | None = None,
) -> None:
    """Persist wins, losses, and shot metrics while ignoring quits and live games."""
    if state.quit_requested or not state.game_over:
        return

    game_stats = stats if stats is not None else load_stats()
    record_outcome(game_stats, "battleship", won=state.player_won)
    battleship_stats = game_stats.setdefault("battleship", {})
    total_hits = hits if hits is not None else sum(len(ship.hits) for ship in state.enemy_board.ships)
    battleship_stats["total_shots"] = battleship_stats.get("total_shots", 0) + state.shots_taken
    battleship_stats["total_hits"] = battleship_stats.get("total_hits", 0) + total_hits
    battleship_stats["hit_accuracy"] = round(
        (battleship_stats["total_hits"] / battleship_stats["total_shots"]) * 100
    ) if battleship_stats["total_shots"] else 0
    if state.player_won:
        record_metric(game_stats, "battleship", "fewest_shots", state.shots_taken, lower_is_better=True)
    save_stats(game_stats)


def _ship_cells(origin: Position, length: int, horizontal: bool) -> tuple[Position, ...]:
    x, y = origin
    if horizontal:
        return tuple((x + offset, y) for offset in range(length))
    return tuple((x, y + offset) for offset in range(length))


def _ship_for_position(board: FleetBoard, position: Position) -> Ship | None:
    for ship in board.ships:
        if position in ship.cells or position in ship.hits:
            return ship
    return None


def _shot_already(board: FleetBoard, position: Position) -> bool:
    return position in board.misses or any(position in ship.hits for ship in board.ships)


def _in_bounds(position: Position) -> bool:
    try:
        x, y = position
    except (TypeError, ValueError):
        return False
    return isinstance(x, int) and isinstance(y, int) and 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


def _all_positions() -> tuple[Position, ...]:
    return tuple((x, y) for y in range(BOARD_SIZE) for x in range(BOARD_SIZE))


def _latest_unsunk_player_ship(state: BattleState) -> Ship | None:
    for shot in reversed(state.enemy_shots):
        ship = _ship_for_position(state.player_board, shot)
        if ship is not None and shot in ship.hits and len(ship.hits) < len(ship.cells):
            return ship
    return None


def _aligned_candidates(target_hits: list[Position], shots: set[Position]) -> list[Position]:
    if len(target_hits) < 2:
        return []
    xs = {x for x, _ in target_hits}
    ys = {y for _, y in target_hits}
    if len(xs) == 1:
        x = target_hits[-1][0]
        step = 1 if target_hits[-1][1] >= target_hits[-2][1] else -1
        forward = (x, target_hits[-1][1] + step)
        backward = (x, target_hits[0][1] - step)
    elif len(ys) == 1:
        y = target_hits[-1][1]
        step = 1 if target_hits[-1][0] >= target_hits[-2][0] else -1
        forward = (target_hits[-1][0] + step, y)
        backward = (target_hits[0][0] - step, y)
    else:
        return []
    return [position for position in (forward, backward) if _in_bounds(position) and position not in shots]


def _neighbor_candidates(target_hits: list[Position], shots: set[Position]) -> list[Position]:
    candidates: list[Position] = []
    for hit in reversed(target_hits):
        x, y = hit
        for position in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
            if _in_bounds(position) and position not in shots and position not in candidates:
                candidates.append(position)
    return candidates


def _render_board(
    board: FleetBoard,
    *,
    reveal_ships: bool,
    target: Position | None = None,
) -> list[str]:
    header = "   " + "".join(f" {label}" for label in _COLUMN_LABELS)
    lines = [header]
    for y in range(BOARD_SIZE):
        cells = "".join(_render_cell(board, (x, y), reveal_ships, target) for x in range(BOARD_SIZE))
        lines.append(f"{y + 1:>2} {cells}")
    return lines


def _render_cell(
    board: FleetBoard,
    position: Position,
    reveal_ships: bool,
    target: Position | None,
) -> str:
    ship = _ship_for_position(board, position)
    if position in board.misses:
        token = color("o", "cyan")
    elif ship is not None and position in ship.hits and len(ship.hits) == len(ship.cells or ship.hits):
        token = color("X", "red")
    elif ship is not None and position in ship.hits:
        token = color("x", "yellow")
    elif reveal_ships and ship is not None and position in ship.cells:
        token = color("@", "green")
    else:
        token = "."
    prefix = ">" if target == position else " "
    return prefix + token


def _status_line(state: BattleState) -> str:
    target_text = _format_coordinate(state.target)
    if state.quit_requested:
        outcome = color("INTERROTTA", "yellow")
    elif state.game_over and state.player_won:
        outcome = color("VITTORIA", "green")
    elif state.game_over:
        outcome = color("SCONFITTA", "red")
    else:
        outcome = color("IN CORSO", "yellow")
    return f"Colpi {state.shots_taken:02d}  Bersaglio {target_text}  {outcome}"


def _controls_line(*, realtime: bool) -> str:
    if realtime:
        return "WASD/Frecce muovi  SPAZIO fuoco  R cambia flotta  Q esci"
    return "Coordinate C7 + INVIO  R cambia flotta  Q esci"


def _format_coordinate(position: Position) -> str:
    return f"{_COLUMN_LABELS[position[0]]}{position[1] + 1}"


def _choose(randomizer: Any, options: list[Any]) -> Any:
    if hasattr(randomizer, "choice"):
        return randomizer.choice(options)
    index = randomizer.randrange(len(options))
    return options[index]


def _visible_width(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def _pad_visible(text: str, width: int) -> str:
    return text + " " * max(0, width - _visible_width(text))


if __name__ == "__main__":
    main()
