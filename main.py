from __future__ import annotations

from console_gg.catalog import legacy_games
from console_gg.shell import run_shell


GAMES = legacy_games()


def main() -> None:
    run_shell()


if __name__ == "__main__":
    main()
