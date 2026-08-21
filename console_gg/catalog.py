"""Stable game catalog for the Console GG arcade shell."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameSpec:
    game_id: str
    title: str
    category: str
    description: str
    module: str
    controls: str
    stats_key: str

    @property
    def id(self) -> str:
        """Compatibility alias for the implementation-plan field name."""
        return self.game_id


GAME_CATALOG = (
    GameSpec(
        "2048",
        "2048",
        "ROMPICAPO",
        "Unisci tessere, insegui il 2048.",
        "console_gg.games.game_2048",
        "WASD/frecce; Q esce.",
        "best_score",
    ),
    GameSpec(
        "wordle",
        "Wordle",
        "ROMPICAPO",
        "Sei tentativi per trovare la parola.",
        "console_gg.games.wordle",
        "Lettere e INVIO; Q esce.",
        "best_streak",
    ),
    GameSpec(
        "minesweeper",
        "Campo Minato",
        "ROMPICAPO",
        "Scopri le caselle senza trovare mine.",
        "console_gg.games.minesweeper",
        "WASD/frecce; SPAZIO apri; F bandiera; R; Q.",
        "best_time",
    ),
    GameSpec(
        "blackjack",
        "Blackjack",
        "TAVOLO",
        "Carte, puntate finte e dealer testardo.",
        "console_gg.games.blackjack",
        "Puntata, C carta, S sto, Q esci.",
        "bankroll",
    ),
    GameSpec(
        "tris",
        "Tris",
        "TAVOLO",
        "Tre simboli in fila contro il cabinato.",
        "console_gg.games.tris",
        "1-9 caselle; Q esce.",
        "wins",
    ),
    GameSpec(
        "forza4",
        "Forza 4",
        "TAVOLO",
        "Gettoni in caduta, quattro in fila.",
        "console_gg.games.forza4",
        "1-7 colonne; Q esce.",
        "wins",
    ),
    GameSpec(
        "battleship",
        "Battaglia Navale",
        "TAVOLO",
        "Affonda la flotta del cabinato.",
        "console_gg.games.battleship",
        "WASD/frecce+SPAZIO; coordinate+INVIO; R flotta; Q.",
        "fewest_shots",
    ),
    GameSpec(
        "snake",
        "Snake",
        "ARCADE",
        "Serpente ASCII, cibo e riflessi.",
        "console_gg.games.snake",
        "WASD/frecce; Q esce.",
        "best_score",
    ),
    GameSpec(
        "block_dropper",
        "Block Dropper",
        "ARCADE",
        "Blocchi in caduta e righe da pulire.",
        "console_gg.games.block_dropper",
        "A/D; W ruota; S giu; SPAZIO drop; P pausa; Q.",
        "best_score",
    ),
    GameSpec(
        "dungeon",
        "Dungeon",
        "AVVENTURA",
        "Mini avventura ASCII con mostri e tesori.",
        "console_gg.games.dungeon",
        "WASD e comandi; Q esce.",
        "best_score",
    ),
)


def legacy_games() -> list[tuple[str, str, str]]:
    """Return the original main-menu tuple shape for compatibility."""
    return [(game.title, game.description, game.module) for game in GAME_CATALOG]


def render_catalog(catalog: tuple[GameSpec, ...] | list[GameSpec] = GAME_CATALOG) -> str:
    """Render the arcade catalog from the public catalog module."""
    from console_gg.shell import render_catalog as _render_catalog

    return _render_catalog(catalog)
