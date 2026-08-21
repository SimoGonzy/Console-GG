"""Pure Block Dropper rules and terminal play loops."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
import random
from typing import Any

from console_gg.realtime import run_realtime
from console_gg.stats import load_stats, record_metric, record_outcome, save_stats
from console_gg.terminal import supports_realtime
from console_gg.ui import clear_screen, pause, safe_input


Position = tuple[int, int]
Board = tuple[tuple[str, ...], ...]

BOARD_WIDTH = 10
BOARD_HEIGHT = 20
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
PIECE_KINDS = ("I", "O", "T", "S", "Z", "J", "L")
SPAWN_ORIGIN = (3, 0)
KICK_OFFSETS = ((0, 0), (-1, 0), (1, 0), (0, -1))
EMPTY = "."
REALTIME_FRAME_WIDTH = 50
REALTIME_INTERVAL = 0.05
INITIAL_GRAVITY_PERIOD = 0.70
MIN_GRAVITY_PERIOD = 0.08
GRAVITY_LEVEL_STEP = 0.03


_SHAPES: dict[str, tuple[tuple[Position, ...], ...]] = {
    "I": (
        ((0, 1), (1, 1), (2, 1), (3, 1)),
        ((2, 0), (2, 1), (2, 2), (2, 3)),
        ((0, 2), (1, 2), (2, 2), (3, 2)),
        ((1, 0), (1, 1), (1, 2), (1, 3)),
    ),
    "O": (
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
    ),
    "T": (
        ((1, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (1, 2)),
        ((1, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "S": (
        ((1, 0), (2, 0), (0, 1), (1, 1)),
        ((1, 0), (1, 1), (2, 1), (2, 2)),
        ((1, 1), (2, 1), (0, 2), (1, 2)),
        ((0, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "Z": (
        ((0, 0), (1, 0), (1, 1), (2, 1)),
        ((2, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (1, 2), (2, 2)),
        ((1, 0), (0, 1), (1, 1), (0, 2)),
    ),
    "J": (
        ((0, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (2, 2)),
        ((1, 0), (1, 1), (0, 2), (1, 2)),
    ),
    "L": (
        ((2, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (1, 2), (2, 2)),
        ((0, 1), (1, 1), (2, 1), (0, 2)),
        ((0, 0), (1, 0), (1, 1), (1, 2)),
    ),
}


@dataclass(frozen=True)
class BlockState:
    board: Board
    active_piece: str
    rotation: int
    origin: Position
    next_piece: str
    bag: tuple[str, ...]
    score: int
    lines: int
    level: int
    game_over: bool
    paused: bool
    quit_requested: bool


@dataclass(frozen=True)
class _RealtimeBlock:
    state: BlockState
    gravity_elapsed: float = 0.0


def piece_cells(kind: str, rotation: int, origin: Position) -> tuple[Position, ...]:
    """Return the four occupied board cells for a tetromino placement."""
    try:
        shape = _SHAPES[kind][rotation % 4]
    except KeyError as error:
        raise ValueError(f"unknown tetromino: {kind}") from error
    origin_x, origin_y = origin
    return tuple((origin_x + x, origin_y + y) for x, y in shape)


def _empty_board() -> Board:
    row = (EMPTY,) * BOARD_WIDTH
    return (row,) * BOARD_HEIGHT


def _new_bag(randomizer: Any = None) -> tuple[str, ...]:
    pieces = list(PIECE_KINDS)
    rng = randomizer if randomizer is not None else random
    rng.shuffle(pieces)
    return tuple(pieces)


def _provided_pieces(piece_source: Iterable[str] | Callable[[], str]) -> tuple[str, ...]:
    if callable(piece_source):
        pieces = tuple(piece_source() for _ in PIECE_KINDS)
    else:
        pieces = tuple(piece_source)
    if len(pieces) < 2:
        raise ValueError("piece_source must provide at least two tetrominoes")
    if any(piece not in _SHAPES for piece in pieces):
        raise ValueError("piece_source contains an unknown tetromino")
    return pieces


def new_state(
    piece_source: Iterable[str] | Callable[[], str] | None = None,
    randomizer: Any = None,
) -> BlockState:
    """Create a new immutable game with an injectable piece sequence."""
    pieces = _new_bag(randomizer) if piece_source is None else _provided_pieces(piece_source)
    return BlockState(
        board=_empty_board(),
        active_piece=pieces[0],
        rotation=0,
        origin=SPAWN_ORIGIN,
        next_piece=pieces[1],
        bag=pieces[2:],
        score=0,
        lines=0,
        level=1,
        game_over=False,
        paused=False,
        quit_requested=False,
    )


def _can_place(board: Board, kind: str, rotation: int, origin: Position) -> bool:
    for x, y in piece_cells(kind, rotation, origin):
        if x < 0 or x >= BOARD_WIDTH or y >= BOARD_HEIGHT:
            return False
        if y >= 0 and board[y][x] != EMPTY:
            return False
    return True


def move_piece(state: BlockState, dx: int, dy: int) -> BlockState:
    """Move the active piece when legal, scoring positive manual drops."""
    if state.game_over or state.paused or state.quit_requested:
        return state
    if (dx, dy) not in {(-1, 0), (1, 0), (0, -1), (0, 1)}:
        return state
    candidate = (state.origin[0] + dx, state.origin[1] + dy)
    if not _can_place(state.board, state.active_piece, state.rotation, candidate):
        return state
    drop_points = max(0, dy) if dx == 0 else 0
    return replace(state, origin=candidate, score=state.score + drop_points)


def rotate_piece(state: BlockState) -> BlockState:
    """Rotate clockwise using the game's small deterministic kick order."""
    if state.game_over or state.paused or state.quit_requested:
        return state
    next_rotation = (state.rotation + 1) % 4
    for kick_x, kick_y in KICK_OFFSETS:
        kicked_origin = (state.origin[0] + kick_x, state.origin[1] + kick_y)
        if _can_place(state.board, state.active_piece, next_rotation, kicked_origin):
            return replace(state, rotation=next_rotation, origin=kicked_origin)
    return state


def clear_full_lines(board: Board) -> tuple[Board, int]:
    """Remove complete rows and return a height-preserving board and count."""
    remaining = tuple(row for row in board if any(cell == EMPTY for cell in row))
    count = len(board) - len(remaining)
    empty_rows = ((_empty_board()[0]),) * count
    return empty_rows + remaining, count


def line_score(count: int, level: int) -> int:
    """Return exact line-clear points at the level before the clear."""
    return LINE_SCORES.get(count, 0) * level


def gravity_period(level: int) -> float:
    """Return the decreasing gravity interval for a one-based level."""
    normalized_level = max(1, level)
    period = INITIAL_GRAVITY_PERIOD - (normalized_level - 1) * GRAVITY_LEVEL_STEP
    return max(MIN_GRAVITY_PERIOD, round(period, 2))


def _draw_queued_piece(bag: tuple[str, ...], randomizer: Any = None) -> tuple[str, tuple[str, ...]]:
    available = bag if bag else _new_bag(randomizer)
    return available[0], available[1:]


def _lock_piece(state: BlockState, randomizer: Any = None) -> BlockState:
    rows = [list(row) for row in state.board]
    topped_out = False
    for x, y in piece_cells(state.active_piece, state.rotation, state.origin):
        if y < 0:
            topped_out = True
        else:
            rows[y][x] = state.active_piece

    cleared_board, cleared_count = clear_full_lines(tuple(tuple(row) for row in rows))
    next_in_queue, remaining_bag = _draw_queued_piece(state.bag, randomizer)
    total_lines = state.lines + cleared_count
    spawned = replace(
        state,
        board=cleared_board,
        active_piece=state.next_piece,
        rotation=0,
        origin=SPAWN_ORIGIN,
        next_piece=next_in_queue,
        bag=remaining_bag,
        score=state.score + line_score(cleared_count, state.level),
        lines=total_lines,
        level=1 + total_lines // 10,
    )
    spawn_blocked = not _can_place(
        spawned.board,
        spawned.active_piece,
        spawned.rotation,
        spawned.origin,
    )
    return replace(spawned, game_over=topped_out or spawn_blocked)


def ghost_origin(state: BlockState) -> Position:
    """Return the lowest legal origin for the current active piece."""
    origin_x, origin_y = state.origin
    while _can_place(
        state.board,
        state.active_piece,
        state.rotation,
        (origin_x, origin_y + 1),
    ):
        origin_y += 1
    return origin_x, origin_y


def hard_drop(state: BlockState, randomizer: Any = None) -> BlockState:
    """Drop to the ghost position, award distance points, and lock immediately."""
    if state.game_over or state.paused or state.quit_requested:
        return state
    landing = ghost_origin(state)
    distance = landing[1] - state.origin[1]
    dropped = replace(state, origin=landing, score=state.score + distance * 2)
    return _lock_piece(dropped, randomizer)


def tick(state: BlockState, randomizer: Any = None) -> BlockState:
    """Advance gravity once, locking and spawning when downward motion is blocked."""
    if state.game_over or state.paused or state.quit_requested:
        return state
    candidate = (state.origin[0], state.origin[1] + 1)
    if _can_place(state.board, state.active_piece, state.rotation, candidate):
        return replace(state, origin=candidate)
    return _lock_piece(state, randomizer)


def _cell_tokens(state: BlockState) -> list[list[str]]:
    tokens = [
        ["[]" if cell != EMPTY else "  " for cell in row]
        for row in state.board
    ]
    ghost_cells = set(piece_cells(state.active_piece, state.rotation, ghost_origin(state)))
    active_cells = set(piece_cells(state.active_piece, state.rotation, state.origin))
    for x, y in ghost_cells - active_cells:
        if 0 <= y < BOARD_HEIGHT and state.board[y][x] == EMPTY:
            tokens[y][x] = "::"
    for x, y in active_cells:
        if 0 <= y < BOARD_HEIGHT:
            tokens[y][x] = "##"
    return tokens


def _preview_rows(kind: str) -> tuple[str, ...]:
    cells = set(piece_cells(kind, 0, (0, 0)))
    return tuple("".join("##" if (x, y) in cells else "  " for x in range(4)) for y in range(4))


def _fixed_line(text: str) -> str:
    return text[:REALTIME_FRAME_WIDTH].ljust(REALTIME_FRAME_WIDTH)


def render_game(state: BlockState) -> str:
    """Render a fixed-width two-character board, ghost, queue, and score HUD."""
    status = "GAME OVER" if state.game_over else "PAUSED" if state.paused else "PLAYING"
    lines = [
        _fixed_line(
            f"BLOCK DROPPER  Score {state.score:06d} Level {state.level:02d} "
            f"Lines {state.lines:03d}"
        ),
        _fixed_line("A/D Move W Rotate S Drop SPACE Slam P Pause Q Quit"),
    ]
    preview = _preview_rows(state.next_piece)
    tokens = _cell_tokens(state)
    lines.append(
        _fixed_line(
            "+" + "--" * BOARD_WIDTH + "+" + f"  Next [{state.next_piece}] {status}"
        )
    )
    for y, row in enumerate(tokens):
        side = ""
        if 1 <= y < 5:
            side = "  " + preview[y - 1]
        lines.append(_fixed_line("|" + "".join(row) + "|" + side))
    lines.append(_fixed_line("+" + "--" * BOARD_WIDTH + "+"))
    return "\n".join(lines)


def _handle_events(
    state: BlockState,
    keys: list[str],
    randomizer: Any = None,
) -> BlockState:
    """Apply one batch of semantic realtime controls without gravity."""
    current = state
    for key in keys:
        normalized = key.lower()
        if normalized.strip() in {"q", "quit", "exit"}:
            return replace(current, quit_requested=True)
        if normalized.strip() == "p":
            current = replace(current, paused=not current.paused)
            continue
        if current.paused or current.game_over:
            continue
        command = normalized.strip()
        if command in {"a", "left"}:
            current = move_piece(current, -1, 0)
        elif command in {"d", "right"}:
            current = move_piece(current, 1, 0)
        elif command in {"w", "up"}:
            current = rotate_piece(current)
        elif command in {"s", "down"}:
            dropped = move_piece(current, 0, 1)
            current = tick(current, randomizer) if dropped is current else dropped
        elif normalized == " " or command in {"space", "hard"}:
            current = hard_drop(current, randomizer)
            break
    return current


def _tick_realtime(state: BlockState, randomizer: Any = None) -> BlockState:
    return tick(state, randomizer)


def _handle_realtime_events(
    session: _RealtimeBlock,
    keys: list[str],
    randomizer: Any = None,
) -> _RealtimeBlock:
    return replace(
        session,
        state=_handle_events(session.state, keys, randomizer),
    )


def _advance_realtime(
    session: _RealtimeBlock,
    randomizer: Any = None,
) -> _RealtimeBlock:
    """Accumulate simulation time and apply level-aware gravity when due."""
    state = session.state
    if state.game_over or state.paused or state.quit_requested:
        return session

    elapsed = session.gravity_elapsed + REALTIME_INTERVAL
    while elapsed + 1e-9 >= gravity_period(state.level):
        period = gravity_period(state.level)
        state = tick(state, randomizer)
        elapsed -= period
        if state.game_over or state.paused or state.quit_requested:
            break
    return _RealtimeBlock(state=state, gravity_elapsed=round(max(0.0, elapsed), 10))


def _record_completed_game(state: BlockState, stats: dict | None = None) -> None:
    """Persist game-over records while leaving abandoned games untouched."""
    if not state.game_over or state.quit_requested:
        return
    game_stats = stats if stats is not None else load_stats()
    record_outcome(game_stats, "block_dropper", won=False)
    record_metric(game_stats, "block_dropper", "best_score", state.score)
    record_metric(game_stats, "block_dropper", "best_level", state.level)
    record_metric(game_stats, "block_dropper", "best_lines", state.lines)
    save_stats(game_stats)


def _run_realtime_with_dynamic_gravity(
    initial: BlockState,
    randomizer: Any = None,
) -> BlockState:
    """Run one responsive realtime context with game-owned dynamic gravity."""
    frame_size = (REALTIME_FRAME_WIDTH, len(render_game(initial).splitlines()))
    final = run_realtime(
        _RealtimeBlock(initial),
        lambda session, keys: _handle_realtime_events(session, keys, randomizer),
        lambda session: _advance_realtime(session, randomizer),
        lambda session: render_game(session.state),
        lambda session: session.state.game_over or session.state.quit_requested,
        REALTIME_INTERVAL,
        minimum_size=frame_size,
        render_key=lambda session: session.state,
    )
    return final.state


def _play_realtime() -> None:
    rng = random.Random()
    stats = load_stats()
    initial = new_state(randomizer=rng)
    final = _run_realtime_with_dynamic_gravity(initial, rng)
    print(render_game(final))
    if final.quit_requested:
        print("Partita interrotta.")
        return
    _record_completed_game(final, stats)
    print("Game over.")


def _play_step_mode() -> None:
    """Offer a complete Enter-driven fallback when key polling is unavailable."""
    rng = random.Random()
    stats = load_stats()
    state = new_state(randomizer=rng)
    while True:
        clear_screen()
        print(render_game(state))
        if state.game_over:
            _record_completed_game(state, stats)
            print("Game over.")
            return

        command = safe_input("Comando [A/D/W/S/space/P/Q, INVIO=scendi] > ", default="q")
        normalized = command.strip().lower()
        if normalized in {"q", "quit", "exit"}:
            print("Partita interrotta.")
            return

        state = _handle_events(state, [command], rng)
        manual_drop = command == " " or normalized in {"s", "down", "space", "hard"}
        if not state.paused and not manual_drop:
            state = tick(state, rng)


def play() -> None:
    """Play with realtime input when available, otherwise use line input."""
    if supports_realtime():
        _play_realtime()
        return
    _play_step_mode()


def main() -> None:
    play()
    pause()


if __name__ == "__main__":
    main()
