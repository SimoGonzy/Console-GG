"""Blackjack for the Console GG retro arcade."""

from __future__ import annotations

import random
from dataclasses import dataclass

from console_gg.stats import load_stats, record_blackjack_round, save_stats
from console_gg.ui import animated_pause, clear_screen, color, frame, pause, prompt_choice, print_title, safe_input, type_line


Card = tuple[str, str]

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["S", "H", "D", "C"]
STARTING_CHIPS = 100
DEAL_DELAY = 0.45
TEXT_DELAY = 0.012
TABLE_WIDTH = 80
ZONE_WIDTH = 68
CARDS_PER_ROW = 8

ASCII_SUITS = {
    "S": "^",
    "H": "v",
    "D": "o",
    "C": "&",
}

CARD_VALUES = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10,
}

RESULT_MESSAGES = {
    "player_blackjack": "Blackjack! Pagamento 3:2.",
    "dealer_blackjack": "Il dealer ha Blackjack.",
    "player_win": "Hai battuto il dealer.",
    "dealer_win": "Il dealer vince la mano.",
    "push": "Pareggio. La puntata torna indietro.",
    "player_bust": "Sballi. Mano al dealer.",
    "dealer_bust": "Il dealer sballa.",
}


@dataclass
class Shoe:
    """Small public wrapper around the mutable blackjack shoe."""

    cards: list[Card]

    @classmethod
    def fresh(cls, decks: int = 4) -> "Shoe":
        return cls(fresh_shoe(decks))

    def draw(self) -> Card:
        return _draw(self.cards)

    def needs_shuffle(self) -> bool:
        return needs_shuffle(self.cards)

    def __len__(self) -> int:
        return len(self.cards)


def hand_value(cards: list[Card]) -> int:
    """Return the best blackjack value for a hand."""
    total = 0
    aces = 0
    for rank, _suit in cards:
        if rank == "A":
            total += 11
            aces += 1
        else:
            total += CARD_VALUES[rank]

    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def round_result(player: list[Card], dealer: list[Card]) -> str:
    """Return a stable result string for a completed blackjack round."""
    player_total = hand_value(player)
    dealer_total = hand_value(dealer)

    if player_total > 21:
        return "player_bust"
    if dealer_total > 21:
        return "dealer_bust"

    player_blackjack = _is_blackjack(player)
    dealer_blackjack = _is_blackjack(dealer)
    if player_blackjack and dealer_blackjack:
        return "push"
    if player_blackjack:
        return "player_blackjack"
    if dealer_blackjack:
        return "dealer_blackjack"

    if player_total > dealer_total:
        return "player_win"
    if dealer_total > player_total:
        return "dealer_win"
    return "push"


def settle_chips(chips: int, bet: int, result: str) -> int:
    """Return the new chip balance after applying a round result."""
    if result == "player_blackjack":
        return chips + (bet * 3) // 2
    if result in {"player_win", "dealer_bust"}:
        return chips + bet
    if result in {"dealer_win", "dealer_blackjack", "player_bust"}:
        return chips - bet
    if result == "push":
        return chips
    raise ValueError(f"Unknown blackjack result: {result}")


def play() -> None:
    """Run the interactive Blackjack table."""
    chips = STARTING_CHIPS
    shoe = fresh_shoe()
    stats = load_stats()
    while chips > 0:
        clear_screen()
        print_title("Blackjack", f"Gettoni: {chips}")
        bet = _ask_bet(chips)
        if bet is None:
            print(color("Tieni stretti i gettoni. Alla prossima.", "magenta"))
            return
        if needs_shuffle(shoe):
            type_line("Si rimescola il sabot...", "magenta", delay=TEXT_DELAY)
            animated_pause(DEAL_DELAY)
            shoe = fresh_shoe()

        player: list[Card] = []
        dealer: list[Card] = []
        _deal_opening_hands(shoe, player, dealer, chips, bet)

        quit_requested = False
        active_bet = bet
        if not _is_blackjack(player) and not _is_blackjack(dealer):
            quit_requested, active_bet = _player_turn(shoe, player, dealer, chips, bet)
            if quit_requested:
                print(color("Tavolo lasciato.", "magenta"))
                return
            if hand_value(player) <= 21:
                _show_round(
                    player,
                    dealer,
                    chips,
                    active_bet,
                    reveal_dealer=True,
                    status="DEALER TURN",
                    shoe_remaining=len(shoe),
                )
                animated_pause(DEAL_DELAY)
                _dealer_turn(shoe, dealer, player, chips, active_bet)

        result = round_result(player, dealer)
        new_chips = settle_chips(chips, active_bet, result)
        round_delta = new_chips - chips
        chips = new_chips
        record_blackjack_round(stats, result=result, bankroll=chips)
        save_stats(stats)
        _show_round(
            player,
            dealer,
            chips,
            active_bet,
            reveal_dealer=True,
            shoe_remaining=len(shoe),
            round_delta=round_delta,
        )
        print(color(RESULT_MESSAGES[result], _result_color(result)))
        pause()

    clear_screen()
    print_title("Blackjack", "Fine partita")
    print(color("Hai finito i gettoni.", "red"))


def main() -> None:
    play()


def _is_blackjack(cards: list[Card]) -> bool:
    return len(cards) == 2 and hand_value(cards) == 21


def _fresh_deck() -> list[Card]:
    return fresh_shoe(1)


def fresh_shoe(decks: int = 4) -> list[Card]:
    shoe = [(rank, suit) for _deck in range(decks) for suit in SUITS for rank in RANKS]
    random.shuffle(shoe)
    return shoe


def needs_shuffle(shoe: list[Card]) -> bool:
    return len(shoe) < 52


def can_double_down(player: list[Card], chips: int, bet: int) -> bool:
    """Return whether the current hand can double down."""
    return len(player) == 2 and chips >= bet * 2


def _draw(deck: list[Card]) -> Card:
    return deck.pop()


def _deal_card(
    deck: list[Card],
    hand: list[Card],
) -> Card:
    card = _draw(deck)
    hand.append(card)
    return card


def _deal_and_show(
    deck: list[Card],
    hand: list[Card],
    player: list[Card],
    dealer: list[Card],
    chips: int,
    bet: int,
    *,
    reveal_dealer: bool = False,
    status: str = "DEALING",
) -> Card:
    card = _deal_card(deck, hand)
    _show_round(
        player,
        dealer,
        chips,
        bet,
        reveal_dealer=reveal_dealer,
        status=status,
        shoe_remaining=len(deck),
    )
    animated_pause(DEAL_DELAY)
    return card


def _deal_opening_hands(
    deck: list[Card],
    player: list[Card],
    dealer: list[Card],
    chips: int,
    bet: int,
) -> None:
    _show_round(
        player,
        dealer,
        chips,
        bet,
        reveal_dealer=False,
        status="DEALING",
        shoe_remaining=len(deck),
    )
    animated_pause(DEAL_DELAY)
    _deal_and_show(deck, player, player, dealer, chips, bet)
    _deal_and_show(deck, dealer, player, dealer, chips, bet)
    _deal_and_show(deck, player, player, dealer, chips, bet)
    _deal_and_show(deck, dealer, player, dealer, chips, bet)


def double_down(
    deck: list[Card],
    player: list[Card],
    chips: int,
    bet: int,
    delay: float = DEAL_DELAY,
) -> int:
    """Double the active bet, draw exactly one card, and return the new bet."""
    if not can_double_down(player, chips, bet):
        raise ValueError("Double down is not allowed for this hand")
    _deal_card(deck, player)
    return bet * 2


def _dealer_turn(
    deck: list[Card],
    dealer: list[Card],
    player: list[Card],
    chips: int,
    bet: int,
) -> None:
    while hand_value(dealer) < 17:
        _deal_and_show(
            deck,
            dealer,
            player,
            dealer,
            chips,
            bet,
            reveal_dealer=True,
            status="DEALER TURN",
        )


def _player_turn(
    deck: list[Card],
    player: list[Card],
    dealer: list[Card],
    chips: int,
    bet: int,
) -> tuple[bool, int]:
    active_bet = bet
    while hand_value(player) <= 21:
        _show_round(player, dealer, chips, active_bet, reveal_dealer=False, shoe_remaining=len(deck))
        choice = prompt_choice(
            "\n[C]arta  [S]to  [D]ouble  [Q]esci > ",
            {"c", "carta", "h", "hit", "s", "sto", "stand", "d", "double", "q", "quit"},
        )
        if choice in {"q", "quit"}:
            return True, active_bet
        if choice in {"s", "sto", "stand"}:
            return False, active_bet
        if choice in {"d", "double"}:
            if can_double_down(player, chips, active_bet):
                active_bet *= 2
                _deal_and_show(deck, player, player, dealer, chips, active_bet, status="PLAYER TURN")
                return False, active_bet
            type_line("Double non consentito.", "red", delay=TEXT_DELAY)
            animated_pause(DEAL_DELAY / 2)
            continue
        _deal_and_show(deck, player, player, dealer, chips, active_bet, status="PLAYER TURN")
    return False, active_bet


def _ask_bet(chips: int) -> int | None:
    while True:
        raw = safe_input(color(f"Puntata 1-{chips} oppure Q per uscire > ", "yellow"), default="q").strip().lower()
        if raw in {"q", "quit", "exit"}:
            return None
        try:
            bet = int(raw)
        except ValueError:
            print(color("Inserisci un numero valido.", "red"))
            continue
        if 1 <= bet <= chips:
            return bet
        print(color(f"La puntata deve essere tra 1 e {chips}.", "red"))


def _show_round(
    player: list[Card],
    dealer: list[Card],
    chips: int,
    bet: int,
    *,
    reveal_dealer: bool,
    status: str | None = None,
    shoe_remaining: int | None = None,
    round_delta: int | None = None,
) -> None:
    clear_screen()
    round_status = status or ("SHOWDOWN" if reveal_dealer else "PLAYER TURN")
    dealer_cards = _dealer_display_cards(dealer, reveal_dealer)
    dealer_value = str(hand_value(dealer)) if reveal_dealer else "?"
    lines = [
        _status_strip(chips, bet, round_status, shoe_remaining=shoe_remaining, round_delta=round_delta),
        "",
        *_render_zone("DEALER", dealer_cards, dealer_value),
        "",
        *_render_zone("PLAYER", list(player), str(hand_value(player))),
    ]
    print(color(frame("BLACKJACK TABLE", lines, width=TABLE_WIDTH), "green"))


def _dealer_display_cards(dealer: list[Card], reveal_dealer: bool) -> list[Card | None]:
    if reveal_dealer:
        return list(dealer)
    if not dealer:
        return []
    return [dealer[0], *([None] * (len(dealer) - 1))]


def _status_strip(
    chips: int,
    bet: int,
    status: str,
    *,
    shoe_remaining: int | None = None,
    round_delta: int | None = None,
) -> str:
    parts = [f"CHIPS {chips}", f"BET {bet}"]
    if shoe_remaining is not None:
        parts.append(f"SHOE {shoe_remaining}")
    if round_delta is not None:
        parts.append(f"ROUND {round_delta:+d}")
    parts.append(f"STATUS {status}")
    return _zone_text(" | ".join(parts))


def _render_zone(title: str, cards: list[Card | None], value: str) -> list[str]:
    lines = [
        _zone_border(title),
        _zone_text(f"Value: {value}"),
    ]
    lines.extend(_zone_text(card_row) for card_row in _render_card_rows(cards))
    lines.append(_zone_border(""))
    return lines


def _zone_border(title: str) -> str:
    inner_width = ZONE_WIDTH - 2
    if not title:
        return f"+{'-' * inner_width}+"
    label = f" {title[:inner_width - 2]} "
    left = (inner_width - len(label)) // 2
    right = inner_width - len(label) - left
    return f"+{'-' * left}{label}{'-' * right}+"


def _zone_text(text: str) -> str:
    inner_width = ZONE_WIDTH - 4
    safe_text = text[:inner_width]
    return f"| {safe_text.ljust(inner_width)} |"


def _render_card_rows(cards: list[Card | None]) -> list[str]:
    if not cards:
        return ["(no cards)"]

    rows: list[str] = []
    for start in range(0, len(cards), CARDS_PER_ROW):
        rendered_cards = [_render_card(card) for card in cards[start : start + CARDS_PER_ROW]]
        for row_index in range(len(rendered_cards[0])):
            rows.append(" ".join(card[row_index] for card in rendered_cards))
    return rows


def _render_card(card: Card | None) -> list[str]:
    if card is None:
        return [
            "+-----+",
            "|/////|",
            "|/GG//|",
            "|/////|",
            "+-----+",
        ]

    rank, suit = card
    pip = ASCII_SUITS.get(suit, "?")
    return [
        "+-----+",
        f"|{rank:<5}|",
        f"|  {pip}  |",
        f"|{rank:>5}|",
        "+-----+",
    ]


def _format_hand(cards: list[Card]) -> str:
    return " ".join(_format_card(card) for card in cards)


def _format_card(card: Card) -> str:
    rank, suit = card
    return f"{rank}{suit}"


def _result_color(result: str) -> str:
    if result in {"player_blackjack", "player_win", "dealer_bust"}:
        return "green"
    if result == "push":
        return "yellow"
    return "red"


if __name__ == "__main__":
    main()
