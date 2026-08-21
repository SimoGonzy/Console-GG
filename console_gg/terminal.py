"""Nonblocking input and ANSI screen support for real-time terminal games."""

from __future__ import annotations

import os
import re
import select
import shutil
import sys
from collections.abc import Callable
from typing import TextIO


_EXTENDED_KEYS = {"H": "up", "P": "down", "K": "left", "M": "right"}
_ANSI_KEYS = {"A": "up", "B": "down", "C": "right", "D": "left"}
_ARROW_NAMES = {"up", "down", "left", "right"}
_FALLBACK_SIZE = (80, 24)
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_POSIX_INPUT_BUFFER = ""
_POSIX_ORIGINAL_ATTRS: list[int | list[bytes]] | None = None
_POSIX_RAW_DEPTH = 0


def normalize_key(raw: str, extended: bool = False) -> str:
    """Translate raw console input into a stable semantic key name."""
    if extended and raw in _EXTENDED_KEYS:
        return _EXTENDED_KEYS[raw]
    lowered = raw.lower()
    if lowered in _ARROW_NAMES:
        return lowered
    if raw in {"\r", "\n"}:
        return "enter"
    if raw == "\x1b":
        return "escape"
    return lowered


def supports_realtime() -> bool:
    """Return whether this process has a nonblocking single-key backend."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        try:
            import msvcrt  # noqa: F401
        except ImportError:
            return False
        return True

    return _has_posix_realtime_backend()


def _has_posix_realtime_backend() -> bool:
    """Return whether POSIX terminal raw mode modules are available."""
    try:
        import termios  # noqa: F401
    except ImportError:
        return False
    return True


def _poll_raw_key() -> tuple[str, bool] | None:
    """Read one available Windows console key without waiting for input."""
    import msvcrt

    if not msvcrt.kbhit():
        return None
    raw = msvcrt.getwch()
    if raw not in {"\x00", "\xe0"}:
        return raw, False
    if not msvcrt.kbhit():
        return None
    return msvcrt.getwch(), True


def _read_windows_key_blocking() -> str | None:
    """Read one Windows console key and normalize it."""
    import msvcrt

    try:
        raw = msvcrt.getwch()
        if raw in {"\x00", "\xe0"}:
            raw = msvcrt.getwch()
            return normalize_key(raw, extended=True)
        return normalize_key(raw)
    except (EOFError, OSError):
        return None


def _begin_posix_raw_mode() -> None:
    """Switch stdin to noncanonical no-echo mode for browser/PTY games."""
    global _POSIX_ORIGINAL_ATTRS, _POSIX_RAW_DEPTH

    if os.name == "nt" or not sys.stdin.isatty():
        return

    import termios

    fd = sys.stdin.fileno()
    if _POSIX_RAW_DEPTH == 0:
        original = termios.tcgetattr(fd)
        raw = original[:]
        raw[3] &= ~(termios.ICANON | termios.ECHO)
        raw[6][termios.VMIN] = 0
        raw[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSADRAIN, raw)
        _POSIX_ORIGINAL_ATTRS = original
    _POSIX_RAW_DEPTH += 1


def _end_posix_raw_mode() -> None:
    """Restore stdin after a real-time loop, even when the game crashes."""
    global _POSIX_ORIGINAL_ATTRS, _POSIX_RAW_DEPTH

    if os.name == "nt" or _POSIX_RAW_DEPTH <= 0:
        return

    import termios

    _POSIX_RAW_DEPTH -= 1
    if _POSIX_RAW_DEPTH == 0 and _POSIX_ORIGINAL_ATTRS is not None:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _POSIX_ORIGINAL_ATTRS)
        _POSIX_ORIGINAL_ATTRS = None


def _read_posix_keys(limit: int) -> list[str]:
    """Drain available POSIX terminal bytes and return semantic key names."""
    if limit <= 0 or os.name == "nt":
        return []
    try:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
    except (OSError, ValueError):
        return []
    if not ready:
        return []

    try:
        data = os.read(sys.stdin.fileno(), 64).decode(errors="ignore")
    except (BlockingIOError, OSError, ValueError):
        return []
    return _parse_posix_keys(data)[:limit]


def _read_posix_key_blocking() -> str | None:
    """Wait for one POSIX terminal key and return its semantic name."""
    while True:
        try:
            ready, _, _ = select.select([sys.stdin], [], [], None)
        except (OSError, ValueError):
            return None
        if not ready:
            continue

        try:
            data = os.read(sys.stdin.fileno(), 64).decode(errors="ignore")
        except (BlockingIOError, OSError, ValueError):
            return None
        keys = _parse_posix_keys(data)
        if keys:
            return keys[0]


def _parse_posix_keys(data: str) -> list[str]:
    """Translate POSIX raw input, including ANSI arrows, into semantic keys."""
    global _POSIX_INPUT_BUFFER

    keys: list[str] = []
    stream = _POSIX_INPUT_BUFFER + data
    _POSIX_INPUT_BUFFER = ""
    index = 0
    while index < len(stream):
        char = stream[index]
        if char == "\x1b":
            remaining = stream[index:]
            if remaining in {"\x1b", "\x1b["}:
                _POSIX_INPUT_BUFFER = remaining
                break
            if remaining.startswith("\x1b[") and len(remaining) >= 3:
                mapped = _ANSI_KEYS.get(remaining[2])
                if mapped is not None:
                    keys.append(mapped)
                    index += 3
                    continue
            keys.append("escape")
            index += 1
            continue
        keys.append(normalize_key(char))
        index += 1
    return keys


def read_single_key(prompt: str = "") -> str | None:
    """Read one semantic key without requiring Enter when a TTY backend exists."""
    if not supports_realtime():
        return None

    if prompt:
        print(prompt, end="", flush=True)

    if os.name == "nt":
        return _read_windows_key_blocking()

    try:
        _begin_posix_raw_mode()
        return _read_posix_key_blocking()
    finally:
        _end_posix_raw_mode()


def poll_keys(limit: int = 8) -> list[str]:
    """Drain up to ``limit`` semantic keys without blocking."""
    if limit <= 0 or not supports_realtime():
        return []
    if os.name != "nt":
        return _read_posix_keys(limit)

    keys: list[str] = []
    for _ in range(limit):
        raw_key = _poll_raw_key()
        if raw_key is None:
            break
        raw, extended = raw_key
        keys.append(normalize_key(raw, extended=extended))
    return keys


def terminal_size() -> tuple[int, int]:
    """Return terminal dimensions with a predictable usable fallback."""
    size = shutil.get_terminal_size(fallback=_FALLBACK_SIZE)
    columns = size.columns if size.columns > 0 else _FALLBACK_SIZE[0]
    rows = size.lines if size.lines > 0 else _FALLBACK_SIZE[1]
    return columns, rows


def _pad_line(line: str, columns: int) -> str:
    visible_length = len(_ANSI_RE.sub("", line))
    return line + " " * max(0, columns - visible_length)


class TerminalScreen:
    """Render full ANSI frames while keeping cursor cleanup exception-safe."""

    def __init__(
        self,
        output: TextIO | None = None,
        size: Callable[[], tuple[int, int]] = terminal_size,
    ) -> None:
        self._output = output if output is not None else sys.stdout
        self._size = size
        self._has_rendered = False
        self._frame_finished = False
        self._last_payload: str | None = None

    def __enter__(self) -> "TerminalScreen":
        self._has_rendered = False
        self._frame_finished = False
        self._last_payload = None
        try:
            _begin_posix_raw_mode()
            self._output.write("\x1b[?25l")
            self._output.flush()
        except BaseException:
            _end_posix_raw_mode()
            try:
                self._output.write("\x1b[?25h")
                self._output.flush()
            except BaseException:
                pass
            raise
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        self._output.write("\x1b[?25h")
        self._output.flush()
        _end_posix_raw_mode()
        return False

    def size(self) -> tuple[int, int]:
        """Return the current terminal size for the real-time loop."""
        return self._size()

    def render(self, frame: str) -> None:
        """Replace the visible screen with a fully padded frame from the home cursor."""
        columns, rows = self.size()
        lines = frame.splitlines()
        padded = [_pad_line(line, columns) for line in lines[:rows]]
        padded.extend(" " * columns for _ in range(rows - len(padded)))
        payload = "\x1b[H" + "\n".join(padded)
        if payload == self._last_payload:
            return
        self._output.write(payload)
        self._output.flush()
        self._last_payload = payload
        self._has_rendered = True
        self._frame_finished = False

    def finish(self) -> None:
        """Move the cursor below the last rendered frame for plain-text follow-up output."""
        if not self._has_rendered or self._frame_finished:
            return
        self._output.write("\n")
        self._output.flush()
        self._last_payload = None
        self._frame_finished = True
