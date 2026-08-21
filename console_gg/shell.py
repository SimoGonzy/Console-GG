"""Compact catalog and line-input navigation for Console GG."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Iterable

from console_gg.catalog import GAME_CATALOG, GameSpec
from console_gg.stats import format_arcade_records, load_stats
from console_gg.ui import clear_screen, color, pause, safe_input


SCREEN_WIDTH = 72


def _box(lines: Iterable[str]) -> str:
    inner_width = SCREEN_WIDTH - 2
    border = "+" + "-" * inner_width + "+"
    rendered = [border]
    for line in lines:
        rendered.append("|" + line[:inner_width].ljust(inner_width) + "|")
    rendered.append(border)
    return "\n".join(rendered)


def render_catalog(catalog: Iterable[GameSpec] = GAME_CATALOG) -> str:
    """Render the ten-game catalog as one fixed-width grouped screen."""
    games = tuple(catalog)
    lines = [
        "CONSOLE GG".ljust(57) + f"{len(games)} GIOCHI",
        "=" * (SCREEN_WIDTH - 2),
    ]
    groups: list[tuple[str, list[tuple[int, GameSpec]]]] = []
    for index, game in enumerate(games, start=1):
        if not groups or groups[-1][0] != game.category:
            groups.append((game.category, []))
        groups[-1][1].append((index, game))

    for category, entries in groups:
        for start in range(0, len(entries), 3):
            row = entries[start : start + 3]
            prefix = category if start == 0 else ""
            choices = "  ".join(f"[{index}] {game.title}" for index, game in row)
            lines.append(f"{prefix:<12}{choices}")
    lines.extend(
        [
            "=" * (SCREEN_WIDTH - 2),
            "[1-10] GIOCA       [H] GUIDA       [R] RECORD       [Q] ESCI",
        ]
    )
    return _box(lines)


def render_help(catalog: Iterable[GameSpec] = GAME_CATALOG) -> str:
    """Render a compact list of controls for every catalog game."""
    return _box(["GUIDA"] + [f"{game.title}: {game.controls}" for game in catalog])


def render_records(stats: dict[str, Any], catalog: Iterable[GameSpec] = GAME_CATALOG) -> str:
    """Render one primary record for every catalog game."""
    return _box(["RECORD"] + format_arcade_records(stats, catalog))


def parse_command(raw: str, game_count: int) -> tuple[str, int | None]:
    """Parse one shell command into a stable action tuple."""
    choice = raw.strip().lower()
    if choice in {"q", "quit", "exit"}:
        return "quit", None
    if choice in {"h", "help", "guida"}:
        return "help", None
    if choice in {"r", "record", "records"}:
        return "records", None
    if choice.isdigit() and 1 <= int(choice) <= game_count:
        return "play", int(choice) - 1
    return "invalid", None


def run(
    launch: Callable[[GameSpec], None],
    input_fn: Callable[..., str] = safe_input,
) -> None:
    """Run the catalog loop with injectable input and launch boundaries."""
    while True:
        clear_screen()
        print(color(render_catalog(), "cyan"))
        raw_choice = _read_command(input_fn)
        action, index = parse_command(raw_choice, len(GAME_CATALOG))

        if action == "quit":
            print(color("Alla prossima partita.", "magenta"))
            return
        if action == "help":
            _show_help()
            continue
        if action == "records":
            _show_records()
            continue
        if action == "play" and index is not None:
            launch(GAME_CATALOG[index])
            pause()
            continue

        print(color("Scelta non valida.", "red"))
        pause()


def run_shell() -> None:
    """Run the catalog loop and lazily launch selected games."""
    run(_play_game)


def _show_help() -> None:
    clear_screen()
    print(color(render_help(), "cyan"))
    pause()


def _show_records() -> None:
    clear_screen()
    print(color(render_records(load_stats()), "cyan"))
    pause()


def _launch(game: GameSpec) -> None:
    _play_game(game)
    pause()


def _play_game(game: GameSpec) -> None:
    try:
        module = import_module(game.module)
    except ModuleNotFoundError as error:
        if error.name != game.module:
            raise
        print(color(f"{game.title} non e ancora disponibile.", "yellow"))
        return

    module.play()


def _read_command(input_fn: Callable[..., str]) -> str:
    prompt = color("\nComando > ", "yellow")
    try:
        return input_fn(prompt, default="q")
    except TypeError:
        return input_fn(prompt)
