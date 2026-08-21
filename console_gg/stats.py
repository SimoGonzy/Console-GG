"""Persistent arcade statistics for Console GG."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_STATS_PATH = Path("console_gg_stats.json")
STATS_PATH_ENV = "CONSOLE_GG_STATS_PATH"
SPECIALIZED_OUTCOME_GAME_IDS = {"2048", "wordle"}
DEFAULT_STATS: dict[str, Any] = {
    "2048": {
        "games": 0,
        "wins": 0,
        "best_score": 0,
        "best_tile": 0,
        "total_score": 0,
        "total_moves": 0,
    },
    "wordle": {
        "games": 0,
        "wins": 0,
        "current_streak": 0,
        "best_streak": 0,
        "failures": 0,
        "guess_distribution": {str(attempt): 0 for attempt in range(1, 7)},
    },
    "minesweeper": {"games": 0, "wins": 0, "losses": 0, "draws": 0, "best_time": 0},
    "blackjack": {
        "games": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "bankroll": 0,
        "current_streak": 0,
        "best_streak": 0,
    },
    "tris": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
    "forza4": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
    "battleship": {
        "games": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "fewest_shots": 0,
        "total_shots": 0,
        "total_hits": 0,
        "hit_accuracy": 0,
    },
    "snake": {"games": 0, "wins": 0, "losses": 0, "draws": 0, "best_score": 0},
    "block_dropper": {"games": 0, "wins": 0, "losses": 0, "draws": 0, "best_score": 0},
    "dungeon": {
        "games": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "best_score": 0,
        "deepest_level": 0,
        "bosses_defeated": 0,
    },
}


def fresh_stats() -> dict[str, Any]:
    """Return a clean stats dictionary."""
    return deepcopy(DEFAULT_STATS)


def _merge_defaults(value: Any, default: Any) -> Any:
    if isinstance(default, dict):
        merged = deepcopy(default)
        if isinstance(value, dict):
            for key, item in value.items():
                merged[key] = _merge_defaults(item, default[key]) if key in default else item
        return merged
    return value if isinstance(value, type(default)) else deepcopy(default)


def load_stats(path: Path | str = DEFAULT_STATS_PATH) -> dict[str, Any]:
    """Load stats from disk, falling back to defaults when unavailable."""
    stats_path = _resolve_stats_path(path)
    if not stats_path.exists():
        return fresh_stats()

    try:
        raw_stats = json.loads(stats_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fresh_stats()
    return _merge_defaults(raw_stats, DEFAULT_STATS)


def save_stats(stats: dict[str, Any], path: Path | str = DEFAULT_STATS_PATH) -> None:
    """Persist stats to disk as readable JSON."""
    stats_path = _resolve_stats_path(path)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _merge_defaults(stats, DEFAULT_STATS)
    stats_path.write_text(
        json.dumps(normalized, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _resolve_stats_path(path: Path | str) -> Path:
    default = Path(path)
    if default == DEFAULT_STATS_PATH:
        override = os.environ.get(STATS_PATH_ENV)
        if override:
            return Path(override)
    return default


def _win_rate(wins: int, games: int) -> int:
    return round((wins / games) * 100) if games else 0


def _generic_game_stats(stats: dict[str, Any], game_id: str) -> dict[str, Any]:
    default = fresh_stats().get(game_id, {"games": 0, "wins": 0, "losses": 0, "draws": 0})
    game_stats = stats.setdefault(game_id, default)
    for key in ("games", "wins", "losses", "draws"):
        if key in default:
            game_stats.setdefault(key, default[key])
    return game_stats


def record_outcome(
    stats: dict[str, Any],
    game_id: str,
    won: bool | None = None,
    draw: bool = False,
) -> dict[str, Any]:
    """Record one completed result without treating a quit as an outcome."""
    if (won is None and not draw) or game_id in SPECIALIZED_OUTCOME_GAME_IDS:
        return stats

    game_stats = _generic_game_stats(stats, game_id)
    game_stats["games"] += 1
    if draw:
        game_stats["draws"] += 1
    elif won is True:
        game_stats["wins"] += 1
    elif won is False:
        game_stats["losses"] += 1
    return stats


def record_metric(
    stats: dict[str, Any],
    game_id: str,
    metric: str,
    value: int | float,
    lower_is_better: bool = False,
) -> dict[str, Any]:
    """Keep a game's best numeric metric in-place and return the stats map."""
    game_stats = _generic_game_stats(stats, game_id)
    current = game_stats.get(metric)
    if current is None or (lower_is_better and (current == 0 or value < current)) or (
        not lower_is_better and value > current
    ):
        game_stats[metric] = value
    return stats


def format_arcade_records(stats: dict[str, Any], catalog: Any) -> list[str]:
    """Return one primary record line for each catalog game."""
    normalized = _merge_defaults(stats, DEFAULT_STATS)
    records: list[str] = []
    for game in catalog:
        game_stats = normalized.get(game.game_id, {})
        value = game_stats.get(game.stats_key, 0)
        label = game.stats_key.replace("_", " ").upper()
        records.append(f"{game.title}: {label} {value}")
    return records


def summary_for(game_id: str, stats: dict[str, Any]) -> str:
    """Return the primary record summary for one game id."""
    from console_gg.catalog import GAME_CATALOG

    matches = [game for game in GAME_CATALOG if game.game_id == game_id]
    if not matches:
        return f"{game_id}: -"
    return format_arcade_records(stats, matches)[0]


def record_2048_game(
    stats: dict[str, Any],
    *,
    score: int,
    max_tile: int,
    won: bool,
    moves: int,
) -> dict[str, Any]:
    """Update 2048 stats in-place and return the same dictionary."""
    game_stats = stats.setdefault("2048", fresh_stats()["2048"])
    game_stats["games"] += 1
    game_stats["wins"] += int(won)
    game_stats["best_score"] = max(game_stats["best_score"], score)
    game_stats["best_tile"] = max(game_stats["best_tile"], max_tile)
    game_stats["total_score"] += score
    game_stats["total_moves"] += moves
    return stats


def format_2048_stats(stats: dict[str, Any]) -> list[str]:
    """Render compact 2048 stats for the terminal board."""
    game_stats = _merge_defaults(stats, DEFAULT_STATS)["2048"]
    games = game_stats["games"]
    wins = game_stats["wins"]
    average_score = round(game_stats["total_score"] / games) if games else 0
    average_moves = round(game_stats["total_moves"] / games) if games else 0
    return [
        f"Vittorie: {wins}/{games} ({_win_rate(wins, games)}%)",
        f"Record: {game_stats['best_score']} pt  Tessera: {game_stats['best_tile']}",
        f"Media: {average_score} pt  Mosse: {average_moves}",
    ]


def record_wordle_game(
    stats: dict[str, Any],
    *,
    won: bool,
    attempts: int,
) -> dict[str, Any]:
    """Update Wordle stats in-place and return the same dictionary."""
    wordle_stats = stats.setdefault("wordle", fresh_stats()["wordle"])
    distribution = wordle_stats.setdefault("guess_distribution", {})
    wordle_stats["games"] += 1

    if won:
        wordle_stats["wins"] += 1
        wordle_stats["current_streak"] += 1
        wordle_stats["best_streak"] = max(
            wordle_stats["best_streak"],
            wordle_stats["current_streak"],
        )
        distribution[str(attempts)] = distribution.get(str(attempts), 0) + 1
    else:
        wordle_stats["failures"] += 1
        wordle_stats["current_streak"] = 0
    return stats


def format_wordle_stats(stats: dict[str, Any]) -> list[str]:
    """Render compact Wordle stats for the terminal board."""
    wordle_stats = _merge_defaults(stats, DEFAULT_STATS)["wordle"]
    games = wordle_stats["games"]
    wins = wordle_stats["wins"]
    distribution = wordle_stats["guess_distribution"]
    distribution_text = " ".join(
        f"{attempt}:{distribution[str(attempt)]}" for attempt in range(1, 7)
    )
    return [
        f"Vittorie: {wins}/{games} ({_win_rate(wins, games)}%)",
        f"Serie: {wordle_stats['current_streak']}  Record: {wordle_stats['best_streak']}",
        f"Tentativi: {distribution_text}",
    ]


def record_blackjack_round(
    stats: dict[str, Any],
    *,
    result: str,
    bankroll: int,
) -> dict[str, Any]:
    """Record one completed blackjack round, streaks, and best bankroll."""
    winning_results = {"player_blackjack", "player_win", "dealer_bust"}
    draw_results = {"push"}
    losing_results = {"dealer_win", "dealer_blackjack", "player_bust"}
    if result in winning_results:
        record_outcome(stats, "blackjack", won=True)
        won_round = True
    elif result in draw_results:
        record_outcome(stats, "blackjack", draw=True)
        won_round = False
    elif result in losing_results:
        record_outcome(stats, "blackjack", won=False)
        won_round = False
    else:
        raise ValueError(f"Unknown blackjack result: {result}")

    blackjack_stats = _generic_game_stats(stats, "blackjack")
    blackjack_stats.setdefault("current_streak", 0)
    blackjack_stats.setdefault("best_streak", 0)
    blackjack_stats["current_streak"] = blackjack_stats["current_streak"] + 1 if won_round else 0
    record_metric(stats, "blackjack", "best_streak", blackjack_stats["current_streak"])
    record_metric(stats, "blackjack", "bankroll", bankroll)
    return stats
