"""Snake game logic and terminal loop."""

from __future__ import annotations

from dataclasses import dataclass, replace
import random

from console_gg.realtime import run_realtime
from console_gg.stats import load_stats, record_metric, record_outcome, save_stats
from console_gg.terminal import supports_realtime
from console_gg.ui import clear_screen, color, frame, pause, read_key, safe_input


Position = tuple[int, int]

DEFAULT_WIDTH = 20
DEFAULT_HEIGHT = 12
SPEEDS = {"relax": 0.250, "arcade": 0.160, "turbo": 0.095}
BOARD_SIZES = {"compact": (16, 10), "standard": (24, 14)}
REALTIME_FRAME_WIDTH = 48
HEAD = "O"
BODY = "o"
FOOD = "*"
EMPTY = "."

DIRECTIONS: dict[str, Position] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

OPPOSITES = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}

KEY_DIRECTIONS = {
    "w": "up",
    "a": "left",
    "s": "down",
    "d": "right",
    "h": "up",
    "p": "down",
    "k": "left",
    "m": "right",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
}


@dataclass(frozen=True)
class SnakeState:
    width: int
    height: int
    snake: tuple[Position, ...]
    direction: str
    food: Position | None
    score: int = 0
    alive: bool = True
    won: bool = False


@dataclass(frozen=True)
class _RealtimeSnake:
    state: SnakeState
    queued: tuple[str, ...] = ()
    paused: bool = False
    quit: bool = False


def normalize_direction(key: str) -> str | None:
    """Normalize WASD, Windows arrow codes, and direction names."""
    if not key:
        return None
    return KEY_DIRECTIONS.get(key.strip().lower())


def turn_direction(current_direction: str, requested_direction: str | None) -> str:
    """Return a legal direction, ignoring immediate reversals."""
    if requested_direction is None or requested_direction not in DIRECTIONS:
        return current_direction
    if OPPOSITES[current_direction] == requested_direction:
        return current_direction
    return requested_direction


def queue_turns(
    current: str,
    queued: tuple[str, ...],
    requested: list[str],
) -> tuple[str, ...]:
    """Append at most two legal future turns to a Snake turn queue."""
    turns: tuple[str, ...] = ()
    future_direction = current

    for key in (*queued, *requested):
        direction = normalize_direction(key) or key.lower()
        if direction not in DIRECTIONS or len(turns) == 2:
            continue
        if direction == future_direction or direction == OPPOSITES[future_direction]:
            continue
        turns += (direction,)
        future_direction = direction
    return turns


def spawn_food(
    occupied: set[Position],
    width: int,
    height: int,
    randomizer: random.Random | None = None,
) -> Position | None:
    """Return a random empty food position, or None when the grid is full."""
    rng = randomizer or random
    open_cells = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in occupied
    ]
    if not open_cells:
        return None
    return rng.choice(open_cells)


def new_state(
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    randomizer: random.Random | None = None,
) -> SnakeState:
    """Create a playable initial Snake state."""
    head = (max(0, width // 2), max(0, height // 2))
    body = tuple((max(0, head[0] - offset), head[1]) for offset in range(min(3, width)))
    occupied = set(body)
    food = spawn_food(occupied, width, height, randomizer)
    return SnakeState(width=width, height=height, snake=body, direction="right", food=food, won=food is None)


def move_snake(
    state: SnakeState,
    requested_direction: str | None = None,
    randomizer: random.Random | None = None,
) -> SnakeState:
    """Advance the snake by one step and return the next immutable state."""
    if not state.alive or state.won:
        return state

    normalized_request = normalize_direction(requested_direction or "") or requested_direction
    direction = turn_direction(state.direction, normalized_request)
    delta_x, delta_y = DIRECTIONS[direction]
    head_x, head_y = state.snake[0]
    new_head = (head_x + delta_x, head_y + delta_y)
    growing = state.food is not None and new_head == state.food

    if _out_of_bounds(new_head, state.width, state.height):
        return replace(state, alive=False)

    body_to_check = state.snake if growing else state.snake[:-1]
    if new_head in body_to_check:
        return replace(state, direction=direction, alive=False)

    if growing:
        next_snake = (new_head,) + state.snake
        next_food = spawn_food(set(next_snake), state.width, state.height, randomizer)
        return SnakeState(
            width=state.width,
            height=state.height,
            snake=next_snake,
            direction=direction,
            food=next_food,
            score=state.score + 1,
            alive=True,
            won=next_food is None,
        )

    next_snake = (new_head,) + state.snake[:-1]
    return SnakeState(
        width=state.width,
        height=state.height,
        snake=next_snake,
        direction=direction,
        food=state.food,
        score=state.score,
        alive=True,
        won=False,
    )


def render_grid(state: SnakeState) -> str:
    """Render the snake grid as retro ASCII."""
    head = state.snake[0]
    body = set(state.snake[1:])
    rows = ["+" + "-" * state.width + "+"]
    for y in range(state.height):
        cells: list[str] = []
        for x in range(state.width):
            position = (x, y)
            if position == head:
                cells.append(HEAD)
            elif position in body:
                cells.append(BODY)
            elif position == state.food:
                cells.append(FOOD)
            else:
                cells.append(EMPTY)
        rows.append("|" + "".join(cells) + "|")
    rows.append("+" + "-" * state.width + "+")
    return "\n".join(rows)


def play() -> None:
    """Run Snake in real time when supported, otherwise use step play."""
    if supports_realtime():
        _play_realtime()
        return
    _play_step_mode()


def _play_step_mode() -> None:
    """Run the Enter-driven fallback for terminals without nonblocking input."""
    rng = random.Random()
    state = new_state(randomizer=rng)
    message = "Mangia * senza colpire muri o corpo."

    while True:
        clear_screen()
        print(color(_render_screen(state, message), "green"))
        if not state.alive:
            print(color("Game over.", "red"))
            _record_completed_game(state)
            return
        if state.won:
            print(color("Hai riempito tutta la griglia!", "green"))
            _record_completed_game(state)
            return

        key = read_key(color("\nMossa> ", "yellow"), default="")
        if key.strip().lower() in {"q", "quit", "exit"}:
            print(color("Partita interrotta.", "magenta"))
            return

        direction = normalize_direction(key)
        if key.strip() and direction is None:
            message = "Usa W/A/S/D, frecce o Q."
            continue

        before_score = state.score
        state = move_snake(state, direction, randomizer=rng)
        if not state.alive:
            message = "Collisione."
        elif state.score > before_score:
            message = f"Cibo preso. Score {state.score}."
        else:
            message = "Avanti."


def _choose_settings() -> tuple[str, str]:
    """Choose real-time board and speed presets using line input."""
    board = safe_input(
        color("Griglia [compact/standard] (standard) > ", "yellow"),
        default="standard",
    ).strip().lower()
    speed = safe_input(
        color("Velocita [relax/arcade/turbo] (arcade) > ", "yellow"),
        default="arcade",
    ).strip().lower()
    return (
        board if board in BOARD_SIZES else "standard",
        speed if speed in SPEEDS else "arcade",
    )


def _handle_realtime_events(session: _RealtimeSnake, keys: list[str]) -> _RealtimeSnake:
    """Apply one polled input batch without advancing the snake."""
    if session.quit:
        return session

    paused = session.paused
    quit_game = False
    directions: list[str] = []
    for key in keys:
        normalized = key.strip().lower()
        if normalized in {"q", "quit", "exit"}:
            quit_game = True
            break
        if normalized == "p":
            paused = not paused
            continue
        direction = normalize_direction(normalized)
        if direction is not None:
            directions.append(direction)
    return replace(
        session,
        queued=queue_turns(session.state.direction, session.queued, directions),
        paused=paused,
        quit=quit_game,
    )


def _tick_realtime(
    session: _RealtimeSnake,
    randomizer: random.Random | None = None,
) -> _RealtimeSnake:
    """Advance one real-time movement tick and consume one queued turn."""
    if session.paused or session.quit:
        return session
    direction = session.queued[0] if session.queued else None
    queued = session.queued[1:] if session.queued else ()
    return replace(
        session,
        state=move_snake(session.state, direction, randomizer),
        queued=queued,
    )


def _play_realtime() -> None:
    """Run the automatic fixed-step Snake session on compatible terminals."""
    rng = random.Random()
    board_name, speed_name = _choose_settings()
    width, height = BOARD_SIZES[board_name]
    stats = load_stats()
    best_score = stats.get("snake", {}).get("best_score", 0)
    initial = _RealtimeSnake(new_state(width, height, rng))

    def render(session: _RealtimeSnake) -> str:
        return _render_realtime_screen(session, speed_name, best_score)

    initial_frame = render(initial)

    final = run_realtime(
        initial,
        _handle_realtime_events,
        lambda session: _tick_realtime(session, rng),
        render,
        lambda session: session.quit or not session.state.alive or session.state.won,
        SPEEDS[speed_name],
        minimum_size=(REALTIME_FRAME_WIDTH, len(initial_frame.splitlines())),
    )
    if final.quit:
        print(color("Partita interrotta.", "magenta"))
        return

    _record_completed_game(final.state, stats)
    if final.state.won:
        print(color("Hai riempito tutta la griglia!", "green"))
    else:
        print(color("Game over.", "red"))


def _record_completed_game(state: SnakeState, stats: dict | None = None) -> None:
    """Persist completed-game records without treating a quit as an outcome."""
    game_stats = stats if stats is not None else load_stats()
    record_outcome(game_stats, "snake", won=state.won)
    record_metric(game_stats, "snake", "best_score", state.score)
    record_metric(game_stats, "snake", "longest_length", len(state.snake))
    save_stats(game_stats)


def main() -> None:
    play()
    pause()


def _out_of_bounds(position: Position, width: int, height: int) -> bool:
    x, y = position
    return x < 0 or x >= width or y < 0 or y >= height


def _render_screen(state: SnakeState, message: str) -> str:
    lines = [
        f"Score: {state.score}   Direzione: {state.direction}",
        "",
        *render_grid(state).splitlines(),
        "",
        message,
        "",
        "W/A/S/D o frecce: muovi   INVIO: continua   Q: esci",
    ]
    return frame("SNAKE", lines, width=max(48, state.width + 6))


def _render_realtime_screen(session: _RealtimeSnake, speed: str, best_score: int) -> str:
    """Render the fixed real-time board and its compact score HUD."""
    state = session.state
    status = "PAUSA" if session.paused else "IN CORSO"
    lines = [
        f"Score {state.score:04d}  Len {len(state.snake):03d}  {speed.upper():<6}  Best {best_score:04d}",
        f"{status:<8}  WASD/Frecce  P:Pausa  Q:Esci",
        "",
        *render_grid(state).splitlines(),
    ]
    return frame("SNAKE", lines, width=REALTIME_FRAME_WIDTH)


if __name__ == "__main__":
    main()
