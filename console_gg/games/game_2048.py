"""2048 game logic and terminal loop."""

from __future__ import annotations

import random
from typing import Any

from console_gg.stats import format_2048_stats, load_stats, record_2048_game, save_stats
from console_gg.ui import clear_screen, color, frame, read_key, safe_input


BOARD_SIZE = 4
WIN_TILE = 2048
SPAWN_FOUR_CHANCE = 0.1

_DIRECTION_ALIASES = {
    "w": "up",
    "a": "left",
    "s": "down",
    "d": "right",
    "up": "up",
    "left": "left",
    "down": "down",
    "right": "right",
}

_KEY_ALIASES = {
    "w": "w",
    "a": "a",
    "s": "s",
    "d": "d",
    "h": "w",
    "k": "a",
    "p": "s",
    "m": "d",
    "up": "w",
    "left": "a",
    "down": "s",
    "right": "d",
    "q": "q",
}

_CONTINUE_AFTER_WIN_KEYS = {"c", "continua", "continue", "y", "yes"}


def normalize_move_key(key: str) -> str | None:
    if not key:
        return None
    return _KEY_ALIASES.get(key.strip().lower())


def merge_line(line: list[int]) -> tuple[list[int], int]:
    """Slide a single row or column left, merging equal tiles once."""
    tiles = [tile for tile in line if tile != 0]
    merged: list[int] = []
    score = 0
    index = 0

    while index < len(tiles):
        if index + 1 < len(tiles) and tiles[index] == tiles[index + 1]:
            value = tiles[index] * 2
            merged.append(value)
            score += value
            index += 2
        else:
            merged.append(tiles[index])
            index += 1

    merged.extend([0] * (len(line) - len(merged)))
    return merged, score


def move_board(board: list[list[int]], direction: str) -> tuple[list[list[int]], int, bool]:
    """Move the board in one direction and return board, gained score, changed."""
    normalized = _DIRECTION_ALIASES.get(direction.lower())
    if normalized is None:
        raise ValueError("direction must be one of: up, down, left, right")

    original = [row[:] for row in board]
    size = len(original)
    total_score = 0

    if normalized == "left":
        moved = []
        for row in original:
            new_row, gained = merge_line(row)
            moved.append(new_row)
            total_score += gained
    elif normalized == "right":
        moved = []
        for row in original:
            new_row, gained = merge_line(list(reversed(row)))
            moved.append(list(reversed(new_row)))
            total_score += gained
    else:
        moved = [[0 for _ in range(size)] for _ in range(size)]
        for column_index in range(size):
            column = [original[row_index][column_index] for row_index in range(size)]
            if normalized == "down":
                column = list(reversed(column))
            new_column, gained = merge_line(column)
            if normalized == "down":
                new_column = list(reversed(new_column))
            for row_index, value in enumerate(new_column):
                moved[row_index][column_index] = value
            total_score += gained

    return moved, total_score, moved != original


def has_moves(board: list[list[int]]) -> bool:
    """Return True when at least one legal 2048 move remains."""
    for row in board:
        if 0 in row:
            return True

    size = len(board)
    for row_index in range(size):
        for column_index in range(size):
            tile = board[row_index][column_index]
            if column_index + 1 < size and tile == board[row_index][column_index + 1]:
                return True
            if row_index + 1 < size and tile == board[row_index + 1][column_index]:
                return True
    return False


def _spawn_tile(
    board: list[list[int]], randomizer: random.Random | None = None
) -> list[list[int]]:
    randomizer = randomizer or random
    spawned = [row[:] for row in board]
    empty_cells = [
        (row_index, column_index)
        for row_index, row in enumerate(spawned)
        for column_index, tile in enumerate(row)
        if tile == 0
    ]
    if not empty_cells:
        return spawned

    row_index, column_index = randomizer.choice(empty_cells)
    spawned[row_index][column_index] = 4 if randomizer.random() < SPAWN_FOUR_CHANCE else 2
    return spawned


def _new_board(randomizer: random.Random | None = None) -> list[list[int]]:
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    board = _spawn_tile(board, randomizer)
    return _spawn_tile(board, randomizer)


def _has_winning_tile(board: list[list[int]]) -> bool:
    return any(tile >= WIN_TILE for row in board for tile in row)


def _max_tile(board: list[list[int]]) -> int:
    return max((tile for row in board for tile in row), default=0)


def _tile_color(tile: int) -> str:
    if tile == 0:
        return "dim"
    if tile < 8:
        return "cyan"
    if tile < 32:
        return "green"
    if tile < 128:
        return "yellow"
    if tile < 512:
        return "magenta"
    if tile < 2048:
        return "red"
    return "bold"


def _format_tile(tile: int) -> str:
    label = "." if tile == 0 else str(tile)
    return color(f"{label:^6}", _tile_color(tile))


def _render_grid(board: list[list[int]]) -> list[str]:
    border = "+------+------+------+------+"
    lines = [border]
    for row in board:
        lines.append("|" + "|".join(_format_tile(tile) for tile in row) + "|")
        lines.append(border)
    return lines


def _render_board(
    board: list[list[int]],
    score: int,
    message: str = "",
    moves: int = 0,
    stats: dict[str, Any] | None = None,
) -> str:
    lines = [
        f"Score: {score}   Mosse: {moves}   Tessera max: {_max_tile(board)}",
        "",
        *_render_grid(board),
        "",
    ]
    if stats is not None:
        lines.extend([color("STATISTICHE", "magenta"), *format_2048_stats(stats), ""])
    lines.append("W/A/S/D o frecce: muovi - Q esci")
    if message:
        lines.extend(["", message])
    return frame("2048", lines, width=68)


def _wants_endless_mode() -> bool:
    choice = safe_input(
        color("Premi C per continuare, INVIO per tornare al menu... ", "yellow"),
        default="",
    )
    return choice.strip().lower() in _CONTINUE_AFTER_WIN_KEYS


def play() -> None:
    """Run an interactive retro terminal 2048 session."""
    board = _new_board()
    stats = load_stats()
    score = 0
    moves = 0
    message = "Unisci le tessere fino a 2048."
    won = False
    game_recorded = False

    def finish_game(game_won: bool) -> None:
        nonlocal game_recorded
        if game_recorded:
            return
        record_2048_game(
            stats,
            score=score,
            max_tile=_max_tile(board),
            won=game_won,
            moves=moves,
        )
        save_stats(stats)
        game_recorded = True

    while True:
        clear_screen()
        print(color(_render_board(board, score, message, moves=moves, stats=stats), "cyan"))

        if _has_winning_tile(board) and not won:
            won = True
            print(color("\nHai vinto! Tessera 2048 raggiunta.", "green"))
            if _wants_endless_mode():
                message = "Modalita infinita attiva: continua finche vuoi."
                continue
            finish_game(game_won=True)
            return
        if not has_moves(board):
            finish_game(game_won=won)
            print(color("\nGame over. Non ci sono mosse disponibili.", "red"))
            safe_input(color("Premi INVIO per tornare al menu...", "yellow"))
            return

        command = normalize_move_key(read_key(color("\nMossa> ", "yellow"), default="q"))
        if command in {"q", "quit", "exit"}:
            if moves > 0 or won:
                finish_game(game_won=won)
            print(color("Partita interrotta.", "magenta"))
            return
        if command not in {"w", "a", "s", "d"}:
            message = "Comando non valido. Usa W/A/S/D oppure Q."
            continue

        moved, gained, changed = move_board(board, command)
        if not changed:
            message = "Mossa non valida: nessuna tessera si muove."
            continue

        board = _spawn_tile(moved)
        score += gained
        moves += 1
        message = f"+{gained} punti" if gained else "Mossa valida."


def main() -> None:
    play()


if __name__ == "__main__":
    main()
