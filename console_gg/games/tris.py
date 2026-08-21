"""Tris game logic and terminal loop."""

from __future__ import annotations

from console_gg.stats import load_stats, record_outcome, save_stats
from console_gg.ui import clear_screen, color, frame, pause, safe_input


EMPTY = " "
PLAYER_MARK = "X"
COMPUTER_MARK = "O"

WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)

PREFERRED_MOVES = (4, 0, 2, 6, 8, 1, 3, 5, 7)


def new_board() -> list[str]:
    """Return an empty Tris board."""
    return [EMPTY] * 9


def available_moves(board: list[str]) -> list[int]:
    """Return the indexes of empty cells."""
    _validate_board(board)
    return [index for index, cell in enumerate(board) if cell == EMPTY]


def board_full(board: list[str]) -> bool:
    """Return True when no moves remain."""
    return not available_moves(board)


def winner(board: list[str]) -> str | None:
    """Return the winning mark, or None when there is no winner."""
    _validate_board(board)
    for first, second, third in WIN_LINES:
        mark = board[first]
        if mark != EMPTY and mark == board[second] == board[third]:
            return mark
    return None


def is_draw(board: list[str]) -> bool:
    """Return True when the board is full and neither mark won."""
    return board_full(board) and winner(board) is None


def place_mark(board: list[str], index: int, mark: str) -> list[str]:
    """Place a mark in a copy of board and return it."""
    _validate_board(board)
    if mark not in {PLAYER_MARK, COMPUTER_MARK}:
        raise ValueError("mark must be X or O")
    if not 0 <= index < len(board):
        raise ValueError("cell index must be between 0 and 8")
    if board[index] != EMPTY:
        raise ValueError("cell is already occupied")

    updated = board[:]
    updated[index] = mark
    return updated


def choose_computer_move(
    board: list[str],
    computer_mark: str = COMPUTER_MARK,
    player_mark: str = PLAYER_MARK,
) -> int:
    """Choose a deterministic computer move: win, block, center, corners, sides."""
    _validate_board(board)
    for mark in (computer_mark, player_mark):
        move = _line_completion_move(board, mark)
        if move is not None:
            return move

    for index in PREFERRED_MOVES:
        if board[index] == EMPTY:
            return index
    raise ValueError("board is full")


def play() -> None:
    """Run an interactive Tris session against a deterministic computer."""
    board = new_board()
    stats = load_stats()
    message = "Scegli una casella da 1 a 9. Tu sei X."

    while True:
        clear_screen()
        print(color(_render_game(board, message), "cyan"))
        finished = _finished_message(board)
        if finished:
            print(color(finished, _finished_color(board)))
            _record_completed_game(board, stats)
            return

        raw_choice = safe_input(color("\nCasella> ", "yellow"), default="q").strip().lower()
        if raw_choice in {"q", "quit", "exit"}:
            print(color("Partita interrotta.", "magenta"))
            return

        index = _parse_cell(raw_choice)
        if index is None:
            message = "Inserisci un numero da 1 a 9 oppure Q."
            continue

        try:
            board = place_mark(board, index, PLAYER_MARK)
        except ValueError:
            message = "Casella occupata. Scegline un'altra."
            continue

        if winner(board) or is_draw(board):
            message = "Ultima mossa giocata."
            continue

        computer_index = choose_computer_move(board)
        board = place_mark(board, computer_index, COMPUTER_MARK)
        message = f"Il cabinato sceglie la casella {computer_index + 1}."


def main() -> None:
    play()
    pause()


def _validate_board(board: list[str]) -> None:
    if len(board) != 9:
        raise ValueError("board must contain exactly nine cells")


def _line_completion_move(board: list[str], mark: str) -> int | None:
    for first, second, third in WIN_LINES:
        values = [board[first], board[second], board[third]]
        if values.count(mark) == 2 and values.count(EMPTY) == 1:
            return (first, second, third)[values.index(EMPTY)]
    return None


def _parse_cell(raw_choice: str) -> int | None:
    if not raw_choice.isdigit():
        return None
    cell = int(raw_choice)
    if 1 <= cell <= 9:
        return cell - 1
    return None


def _cell_label(board: list[str], index: int) -> str:
    return str(index + 1) if board[index] == EMPTY else board[index]


def _render_board(board: list[str]) -> list[str]:
    rows: list[str] = []
    for start in range(0, 9, 3):
        rows.append(" | ".join(f" {_cell_label(board, index)} " for index in range(start, start + 3)))
        if start < 6:
            rows.append("---+---+---")
    return rows


def _render_game(board: list[str], message: str) -> str:
    lines = [
        "TRIS: tre in fila per vincere.",
        "",
        *_render_board(board),
        "",
        message,
        "",
        "1-9: gioca una casella   Q: esci",
    ]
    return frame("TRIS", lines, width=48)


def _finished_message(board: list[str]) -> str:
    winning_mark = winner(board)
    if winning_mark == PLAYER_MARK:
        return "Hai vinto il Tris!"
    if winning_mark == COMPUTER_MARK:
        return "Il cabinato fa Tris."
    if is_draw(board):
        return "Pareggio. Griglia piena."
    return ""


def _finished_color(board: list[str]) -> str:
    winning_mark = winner(board)
    if winning_mark == PLAYER_MARK:
        return "green"
    if winning_mark == COMPUTER_MARK:
        return "red"
    return "yellow"


def _record_completed_game(board: list[str], stats: dict | None = None) -> None:
    winning_mark = winner(board)
    if winning_mark is None and not is_draw(board):
        return

    game_stats = stats if stats is not None else load_stats()
    if winning_mark == PLAYER_MARK:
        record_outcome(game_stats, "tris", won=True)
    elif winning_mark == COMPUTER_MARK:
        record_outcome(game_stats, "tris", won=False)
    else:
        record_outcome(game_stats, "tris", draw=True)
    save_stats(game_stats)


if __name__ == "__main__":
    main()
