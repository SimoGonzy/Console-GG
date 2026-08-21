"""Wordle for the Console GG arcade."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from console_gg.stats import format_wordle_stats, load_stats, record_wordle_game, save_stats
from console_gg.ui import clear_screen, color, frame, print_title, safe_input


WORD_LENGTH = 5
MAX_ATTEMPTS = 6
FEEDBACK_CORRECT = "correct"
FEEDBACK_PRESENT = "present"
FEEDBACK_ABSENT = "absent"
FEEDBACK_AVAILABLE = "available"

ITALIAN_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
ITALIAN_WORD_BANK = (
    "acqua",
    "aceto",
    "amore",
    "anima",
    "aroma",
    "asilo",
    "audio",
    "bacio",
    "banda",
    "banco",
    "barca",
    "birra",
    "bosco",
    "borsa",
    "bravo",
    "campo",
    "canto",
    "carta",
    "cassa",
    "cervo",
    "cielo",
    "colle",
    "cuore",
    "donna",
    "dolce",
    "erede",
    "fango",
    "farro",
    "festa",
    "fiore",
    "forma",
    "fuoco",
    "fiume",
    "gatto",
    "gioco",
    "grano",
    "isola",
    "lampo",
    "latte",
    "leone",
    "libro",
    "linea",
    "luogo",
    "madre",
    "miele",
    "mondo",
    "monte",
    "notte",
    "nuovo",
    "ombra",
    "palla",
    "pasta",
    "pesca",
    "porta",
    "prato",
    "radio",
    "ruota",
    "sasso",
    "scala",
    "sedia",
    "sfera",
    "sogno",
    "suono",
    "tempo",
    "terra",
    "treno",
    "torre",
    "vento",
    "verde",
    "vetro",
    "zuppa",
)
WORD_BANK = ITALIAN_WORD_BANK

FEEDBACK_COLORS = {
    FEEDBACK_CORRECT: "green",
    FEEDBACK_PRESENT: "yellow",
    FEEDBACK_ABSENT: "dim",
    FEEDBACK_AVAILABLE: "white",
}


def evaluate_guess(secret: str, guess: str) -> list[str]:
    """Evaluate a guess using Wordle's duplicate-letter rules."""
    secret_word = secret.lower()
    guess_word = guess.lower()
    if len(secret_word) != len(guess_word):
        raise ValueError("secret and guess must have the same length")

    feedback = [FEEDBACK_ABSENT] * len(secret_word)
    remaining_letters: Counter[str] = Counter()

    for index, (secret_letter, guess_letter) in enumerate(zip(secret_word, guess_word)):
        if secret_letter == guess_letter:
            feedback[index] = FEEDBACK_CORRECT
        else:
            remaining_letters[secret_letter] += 1

    for index, guess_letter in enumerate(guess_word):
        if feedback[index] == FEEDBACK_CORRECT:
            continue
        if remaining_letters[guess_letter] > 0:
            feedback[index] = FEEDBACK_PRESENT
            remaining_letters[guess_letter] -= 1

    return feedback


def is_valid_guess(guess: str, word_length: int = WORD_LENGTH) -> bool:
    """Return True when guess is alphabetic and exactly word_length letters."""
    return len(guess) == word_length and guess.isalpha()


def format_feedback(guess: str, feedback: list[str]) -> str:
    """Render a colored row for a guess and its feedback."""
    if len(guess) != len(feedback):
        raise ValueError("guess and feedback must have the same length")

    rendered_letters: list[str] = []
    for letter, status in zip(guess.upper(), feedback):
        if status not in FEEDBACK_COLORS:
            raise ValueError(f"unknown feedback status: {status}")
        rendered_letters.append(color(letter, FEEDBACK_COLORS[status]))
    return " ".join(rendered_letters)


def build_keyboard_state(history: list[tuple[str, list[str]]]) -> dict[str, str]:
    priority = {
        FEEDBACK_AVAILABLE: 0,
        FEEDBACK_ABSENT: 1,
        FEEDBACK_PRESENT: 2,
        FEEDBACK_CORRECT: 3,
    }
    state = {letter: FEEDBACK_AVAILABLE for letter in ITALIAN_ALPHABET}
    for guess, feedback in history:
        for letter, status in zip(guess.lower(), feedback):
            if priority[status] > priority[state.get(letter, FEEDBACK_AVAILABLE)]:
                state[letter] = status
    return state


def format_keyboard_state(state: dict[str, str]) -> list[str]:
    groups = [
        ("Giuste", FEEDBACK_CORRECT, "green"),
        ("Presenti", FEEDBACK_PRESENT, "yellow"),
        ("Disponibili", FEEDBACK_AVAILABLE, "white"),
        ("Escluse", FEEDBACK_ABSENT, "dim"),
    ]
    rows: list[str] = []
    for label, status, color_name in groups:
        letters = " ".join(letter.upper() for letter in ITALIAN_ALPHABET if state.get(letter) == status)
        rows.append(f"{label:<11}: {color(letters or '-', color_name)}")
    return rows


def _blank_row() -> str:
    return " ".join("_" for _ in range(WORD_LENGTH))


def _render_history(history: list[tuple[str, list[str]]]) -> list[str]:
    rows = [format_feedback(guess, feedback) for guess, feedback in history]
    rows.extend(_blank_row() for _ in range(MAX_ATTEMPTS - len(history)))
    return rows


def _render_game(
    history: list[tuple[str, list[str]]],
    message: str,
    stats: dict[str, Any] | None = None,
) -> str:
    keyboard = format_keyboard_state(build_keyboard_state(history))
    lines = [
        f"Tentativo {min(len(history) + 1, MAX_ATTEMPTS)}/{MAX_ATTEMPTS}",
        "",
        *_render_history(history),
        "",
        *keyboard,
        "",
    ]
    if stats is not None:
        lines.extend([color("STATISTICHE", "magenta"), *format_wordle_stats(stats), ""])
    lines.extend([
        message,
        "",
        "Scrivi una parola di cinque lettere oppure Q per uscire.",
    ])
    return frame("WORDLE", lines, width=72)


def play() -> None:
    """Run an interactive Wordle session."""
    secret = random.choice(WORD_BANK)
    stats = load_stats()
    history: list[tuple[str, list[str]]] = []
    message = color("Trova la parola segreta.", "cyan")

    while True:
        clear_screen()
        print_title("Wordle", "Sei tentativi, stile cabinato.")
        print(_render_game(history, message, stats=stats))

        if history and history[-1][0] == secret:
            record_wordle_game(stats, won=True, attempts=len(history))
            save_stats(stats)
            print(color(f"\nHai indovinato: {secret.upper()}!", "green"))
            return
        if len(history) >= MAX_ATTEMPTS:
            record_wordle_game(stats, won=False, attempts=len(history))
            save_stats(stats)
            print(color(f"\nTentativi finiti. La parola era {secret.upper()}.", "red"))
            return

        raw_guess = safe_input(color("\nParola> ", "yellow"), default="q").strip()
        if raw_guess.lower() in {"q", "quit", "exit"}:
            print(color("Partita interrotta.", "magenta"))
            return
        if not is_valid_guess(raw_guess):
            message = color("Serve una parola alfabetica di cinque lettere.", "red")
            continue

        guess = raw_guess.lower()
        feedback = evaluate_guess(secret, guess)
        history.append((guess, feedback))
        message = color("Continua a provare.", "cyan")


def main() -> None:
    play()


if __name__ == "__main__":
    main()
