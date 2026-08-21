"""Shared retro terminal helpers for Console GG."""

from __future__ import annotations

import os
import re
import time
from collections.abc import Iterable

from console_gg import terminal


RESET = "\033[0m"
ANSI_RE = re.compile(r"\033\[[0-9;]*m")
COLORS = {
    "black": "\033[30m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "gray": "\033[90m",
    "orange": "\033[38;5;208m",
    "pink": "\033[38;5;213m",
    "purple": "\033[38;5;141m"
}


def color(text: str, color_name: str) -> str:
    """Wrap text in an ANSI color code unless NO_COLOR is set."""
    if os.environ.get("NO_COLOR"):
        return text
    code = COLORS.get(color_name)
    if not code:
        return text
    return f"{code}{text}{RESET}"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def safe_input(prompt: str, default: str = "") -> str:
    """Read input, returning default when stdin is closed."""
    try:
        return input(prompt)
    except EOFError:
        print()
        return default


def _read_single_key(prompt: str = "") -> str | None:
    """Return one key without Enter when the terminal backend supports it."""
    return terminal.read_single_key(prompt)


def read_key(prompt: str, default: str = "") -> str:
    """Read one key when possible, falling back to line input."""
    key = _read_single_key(prompt)
    if key is None:
        return safe_input(prompt, default=default)
    return key


def animated_pause(seconds: float = 0.15) -> None:
    if seconds > 0:
        time.sleep(seconds)


def type_line(text: str, color_name: str = "white", delay: float = 0.015) -> None:
    for character in text:
        print(color(character, color_name), end="", flush=True)
        animated_pause(delay)
    print()


def pause(message: str = "Premi INVIO per continuare...") -> None:
    safe_input(color(message, "dim"))


def _fit_line(text: str, width: int) -> str:
    inner_width = max(1, width - 2)
    visible_text = ANSI_RE.sub("", text)
    if len(visible_text) > inner_width - 1:
        clean = visible_text[: inner_width - 1]
        return f"| {clean.ljust(inner_width - 1)}|"
    padding = " " * ((inner_width - 1) - len(visible_text))
    return f"| {text}{padding}|"


def frame(title: str, body: str | Iterable[str], width: int = 64) -> str:
    """Return text wrapped in a simple ASCII arcade frame."""
    safe_width = max(width, 12)
    inner_width = safe_width - 2
    border = "+" + "-" * inner_width + "+"
    title_line = "|" + title[:inner_width].center(inner_width) + "|"
    separator = "+" + "=" * inner_width + "+"
    if isinstance(body, str):
        body_lines = body.splitlines() or [""]
    else:
        body_lines = list(body) or [""]
    rendered = [border, title_line, separator]
    rendered.extend(_fit_line(line, safe_width) for line in body_lines)
    rendered.append(border)
    return "\n".join(rendered)


def render_menu(title: str, items: list[tuple[str, str]]) -> str:
    lines: list[str] = []
    for index, (label, description) in enumerate(items, start=1):
        lines.append(f"[{index}] {label}")
        if description:
            lines.append(f"    {description}")
    return frame(title, lines, width=72)


def prompt_choice(prompt: str, valid_choices: set[str]) -> str:
    lowered = {choice.lower() for choice in valid_choices}
    while True:
        choice = safe_input(color(prompt, "cyan"), default="q").strip().lower()
        if choice in lowered:
            return choice
        print(color("Comando non valido. Riprova.", "red"))


def print_title(title: str, subtitle: str = "") -> None:
    lines = [color(title.upper(), "magenta")]
    if subtitle:
        lines.append(color(subtitle, "cyan"))
    print(frame("CONSOLE GG", lines, width=72))
