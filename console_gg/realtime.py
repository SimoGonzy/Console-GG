"""Fixed-step runtime shared by the terminal arcade's real-time games."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from console_gg.terminal import TerminalScreen, poll_keys


State = TypeVar("State")


class FixedStep:
    """Accumulate elapsed time into bounded, deterministic simulation ticks."""

    def __init__(self, period: float, start: float = 0.0, max_catch_up: int = 2) -> None:
        if period <= 0:
            raise ValueError("period must be positive")
        if max_catch_up < 1:
            raise ValueError("max_catch_up must be at least 1")
        self.period = period
        self.max_catch_up = max_catch_up
        self._last = start
        self._elapsed = 0.0

    def consume(self, now: float) -> int:
        """Return due ticks, capping backlog and discarding a stalled remainder."""
        self._elapsed += max(0.0, now - self._last)
        self._last = now
        due = int(self._elapsed / self.period)
        if due > self.max_catch_up:
            self._elapsed = 0.0
            return self.max_catch_up
        self._elapsed -= due * self.period
        return due

    def rebase(self, now: float) -> None:
        """Discard pending elapsed time and restart timing from ``now``."""
        self._last = now
        self._elapsed = 0.0


def run_realtime(
    initial_state: State,
    handle_events: Callable[[State, list[str]], State],
    tick: Callable[[State], State],
    render: Callable[[State], str],
    is_finished: Callable[[State], bool],
    tick_period: float,
    *,
    input_source: Callable[[], list[str]] = poll_keys,
    screen: TerminalScreen | None = None,
    clock: Callable[[], float] = time.perf_counter,
    sleeper: Callable[[float], None] = time.sleep,
    minimum_size: tuple[int, int] = (1, 1),
    render_final: bool = False,
    idle_render_period: float | None = None,
    render_key: Callable[[State], object] | None = None,
) -> State:
    """Run an input-driven fixed-step loop and return the final game state."""
    active_screen = screen if screen is not None else TerminalScreen()
    step = FixedStep(tick_period)
    state = initial_state
    needs_rebase = True
    rendered_key: object | None = None
    last_render_at: float | None = None
    has_rendered = False

    with active_screen:
        while not is_finished(state):
            columns, rows = active_screen.size()
            if columns < minimum_size[0] or rows < minimum_size[1]:
                needs_rebase = True
                has_rendered = False
                rendered_key = None
                active_screen.render(_render_resize_message(minimum_size, (columns, rows)))
                sleeper(tick_period)
                continue

            state = handle_events(state, input_source())
            if is_finished(state):
                _render_final_frame(active_screen, render, state, render_final)
                break

            if needs_rebase:
                step.rebase(clock())
                needs_rebase = False
                due_ticks = 0
            else:
                due_ticks = step.consume(clock())

            for _ in range(due_ticks):
                state = tick(state)
                if is_finished(state):
                    break

            now = clock()
            current_render_key = render_key(state) if render_key is not None else state
            should_render = (
                not has_rendered
                or current_render_key != rendered_key
                or (
                    idle_render_period is not None
                    and (
                        last_render_at is None
                        or now - last_render_at >= idle_render_period
                    )
                )
            )
            if should_render:
                active_screen.render(render(state))
                rendered_key = current_render_key
                last_render_at = now
                has_rendered = True
            if is_finished(state):
                _finish_screen(active_screen)
                break
            sleeper(tick_period)

    return state


def _render_resize_message(
    minimum_size: tuple[int, int],
    actual_size: tuple[int, int],
) -> str:
    needed_columns, needed_rows = minimum_size
    columns, rows = actual_size
    return (
        "Allarga il terminale.\n"
        f"Serve {needed_columns}x{needed_rows}.\n"
        f"Ora {columns}x{rows}."
    )


def _render_final_frame(
    screen: TerminalScreen,
    render: Callable[[State], str],
    state: State,
    render_final: bool,
) -> None:
    if render_final:
        screen.render(render(state))
        _finish_screen(screen)


def _finish_screen(screen: TerminalScreen) -> None:
    finish = getattr(screen, "finish", None)
    if callable(finish):
        finish()
