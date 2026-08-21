# Console GG V2 Design

## Goal

Upgrade the four existing console games while keeping the retro ASCII identity and zero mandatory dependencies.

## 2048

- Use single-key movement on Windows through `msvcrt` so the player does not press Enter for every move.
- Keep a prompt fallback for terminals where single-key input is unavailable.
- Continue supporting `W/A/S/D` and `Q`.

## Blackjack

- Add small deal/reveal animations with short delays.
- Keep tests fast by making animation delay injectable or skippable.
- Make the table harder through an explicit house-edge rule: normal tied totals go to the dealer, while natural blackjack ties still push.
- Keep player blackjack payout at 3:2.

## Dungeon

- Replace the single small map with a generated multi-room dungeon.
- Use rooms connected by corridors, fog of war, more items, roaming monsters, and boss enemies.
- Bosses have an aggro range. Once the player enters that range, the boss starts chasing.
- Boss contact starts a separate turn-based battle screen inspired by classic monster RPGs.
- Battle options: attack, defend, potion, flee.
- The player can continue exploring after normal fights and after defeating bosses.

## Wordle

- Use Italian five-letter words.
- Track letter knowledge across guesses.
- Show a keyboard panel with available, present, correct, and excluded letters.

## Constraints

- Python standard library only.
- Preserve direct launch scripts and `python main.py`.
- Core logic must remain testable without interactive input.
- `python -m unittest discover -s tests -p "test*.py" -v` remains the verification command.
