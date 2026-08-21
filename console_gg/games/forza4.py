"""Forza 4 game logic and terminal loop."""

from __future__ import annotations

from console_gg.stats import load_stats, record_outcome, save_stats
from console_gg.ui import clear_screen, color, frame, pause, safe_input


ROWS = 6
COLUMNS = 7
EMPTY = "."
PLAYER_DISC = "X"
COMPUTER_DISC = "O"

DIRECTIONS = (
    (0, 1),
    (1, 0),
    (1, 1),
    (1, -1),
)


def create_board() -> list[list[str]]:
    """Return an empty Forza 4 board."""
    return [[EMPTY for _column in range(COLUMNS)] for _row in range(ROWS)]


def valid_columns(board: list[list[str]]) -> list[int]:
    """Return all columns that can accept another disc."""
    _validate_board(board)
    return [column for column in range(COLUMNS) if board[0][column] == EMPTY]


def board_full(board: list[list[str]]) -> bool:
    """Return True when no column can accept another disc."""
    return not valid_columns(board)


def drop_disc(board: list[list[str]], column: int, disc: str) -> tuple[list[list[str]], int]:
    """Drop a disc into a column and return the updated board plus row index."""
    _validate_board(board)
    if disc not in {PLAYER_DISC, COMPUTER_DISC}:
        raise ValueError("disc must be X or O")
    if not 0 <= column < COLUMNS:
        raise ValueError("column must be between 0 and 6")

    updated = [row[:] for row in board]
    for row in range(ROWS - 1, -1, -1):
        if updated[row][column] == EMPTY:
            updated[row][column] = disc
            return updated, row
    raise ValueError("column is full")


def check_winner(board: list[list[str]], disc: str) -> bool:
    """Return True when disc has four connected cells."""
    _validate_board(board)
    for row in range(ROWS):
        for column in range(COLUMNS):
            if board[row][column] != disc:
                continue
            for delta_row, delta_column in DIRECTIONS:
                if _has_line(board, row, column, delta_row, delta_column, disc):
                    return True
    return False


def choose_computer_move(
    board: list[list[str]],
    computer_disc: str = COMPUTER_DISC,
    player_disc: str = PLAYER_DISC,
) -> int:
    """Choose a deterministic move: win, block, then varied positional score."""
    _validate_board(board)
    for disc in (computer_disc, player_disc):
        for column in _ordered_valid_columns(board):
            candidate, _row = drop_disc(board, column, disc)
            if check_winner(candidate, disc):
                return column

    candidates = valid_columns(board)
    if not candidates:
        raise ValueError("board is full")
    return max(
        candidates,
        key=lambda column: (
            _score_quiet_move(board, column, computer_disc, player_disc),
            -abs(column - (COLUMNS // 2)),
            -column,
        ),
    )


def play() -> None:
    """Run an interactive Forza 4 session against a deterministic computer."""
    board = create_board()
    stats = load_stats()
    message = "Lascia cadere X in una colonna da 1 a 7."

    while True:
        clear_screen()
        print(color(_render_game(board, message), "cyan"))
        finished = _finished_message(board)
        if finished:
            print(color(finished, _finished_color(board)))
            _record_completed_game(board, stats)
            return

        raw_choice = safe_input(color("\nColonna> ", "yellow"), default="q").strip().lower()
        if raw_choice in {"q", "quit", "exit"}:
            print(color("Partita interrotta.", "magenta"))
            return

        column = _parse_column(raw_choice)
        if column is None:
            message = "Inserisci una colonna da 1 a 7 oppure Q."
            continue

        try:
            board, _row = drop_disc(board, column, PLAYER_DISC)
        except ValueError:
            message = "Colonna piena. Scegline un'altra."
            continue

        if check_winner(board, PLAYER_DISC) or board_full(board):
            message = "Ultimo gettone giocato."
            continue

        computer_column = choose_computer_move(board)
        board, _row = drop_disc(board, computer_column, COMPUTER_DISC)
        message = f"Il cabinato gioca in colonna {computer_column + 1}."


def main() -> None:
    play()
    pause()


def _validate_board(board: list[list[str]]) -> None:
    if len(board) != ROWS or any(len(row) != COLUMNS for row in board):
        raise ValueError("board must be a 6 by 7 grid")


def _has_line(
    board: list[list[str]],
    row: int,
    column: int,
    delta_row: int,
    delta_column: int,
    disc: str,
) -> bool:
    for offset in range(4):
        target_row = row + (delta_row * offset)
        target_column = column + (delta_column * offset)
        if not (0 <= target_row < ROWS and 0 <= target_column < COLUMNS):
            return False
        if board[target_row][target_column] != disc:
            return False
    return True


def _ordered_valid_columns(board: list[list[str]]) -> list[int]:
    center = COLUMNS // 2
    return sorted(valid_columns(board), key=lambda column: (abs(column - center), column))


def _score_quiet_move(
    board: list[list[str]],
    column: int,
    computer_disc: str,
    player_disc: str,
) -> int:
    candidate, _row = drop_disc(board, column, computer_disc)
    center = COLUMNS // 2
    score = max(0, 3 - abs(column - center)) * 2
    score -= _column_disc_count(board, column, computer_disc) * 20
    score -= _column_height(board, column)
    score += _potential_line_score(candidate, computer_disc, player_disc) * 2
    return score


def _column_disc_count(board: list[list[str]], column: int, disc: str) -> int:
    return sum(1 for row in range(ROWS) if board[row][column] == disc)


def _column_height(board: list[list[str]], column: int) -> int:
    return sum(1 for row in range(ROWS) if board[row][column] != EMPTY)


def _potential_line_score(
    board: list[list[str]],
    computer_disc: str,
    player_disc: str,
) -> int:
    score = 0
    for window in _all_windows(board):
        if player_disc not in window:
            computer_count = window.count(computer_disc)
            score += computer_count * computer_count
    return score


def _all_windows(board: list[list[str]]) -> list[list[str]]:
    windows: list[list[str]] = []
    for row in range(ROWS):
        for column in range(COLUMNS):
            for delta_row, delta_column in DIRECTIONS:
                cells: list[str] = []
                for offset in range(4):
                    target_row = row + (delta_row * offset)
                    target_column = column + (delta_column * offset)
                    if not (0 <= target_row < ROWS and 0 <= target_column < COLUMNS):
                        break
                    cells.append(board[target_row][target_column])
                if len(cells) == 4:
                    windows.append(cells)
    return windows


def _parse_column(raw_choice: str) -> int | None:
    if not raw_choice.isdigit():
        return None
    column = int(raw_choice)
    if 1 <= column <= COLUMNS:
        return column - 1
    return None


def _render_board(board: list[list[str]]) -> list[str]:
    lines = [" ".join(str(column + 1) for column in range(COLUMNS))]
    lines.append(" ".join("-" for _column in range(COLUMNS)))
    for row in board:
        lines.append(" ".join(row))
    return lines


def _render_game(board: list[list[str]], message: str) -> str:
    lines = [
        "FORZA 4: quattro gettoni in fila.",
        "",
        *_render_board(board),
        "",
        message,
        "",
        "1-7: scegli colonna   Q: esci",
    ]
    return frame("FORZA 4", lines, width=52)


def _finished_message(board: list[list[str]]) -> str:
    if check_winner(board, PLAYER_DISC):
        return "Hai fatto Forza 4!"
    if check_winner(board, COMPUTER_DISC):
        return "Il cabinato collega quattro gettoni."
    if board_full(board):
        return "Pareggio. Griglia piena."
    return ""


def _finished_color(board: list[list[str]]) -> str:
    if check_winner(board, PLAYER_DISC):
        return "green"
    if check_winner(board, COMPUTER_DISC):
        return "red"
    return "yellow"


def _record_completed_game(board: list[list[str]], stats: dict | None = None) -> None:
    if check_winner(board, PLAYER_DISC):
        won = True
        draw = False
    elif check_winner(board, COMPUTER_DISC):
        won = False
        draw = False
    elif board_full(board):
        won = None
        draw = True
    else:
        return

    game_stats = stats if stats is not None else load_stats()
    record_outcome(game_stats, "forza4", won=won, draw=draw)
    save_stats(game_stats)


if __name__ == "__main__":
    main()
