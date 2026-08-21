from __future__ import annotations

import unittest
from unittest.mock import patch

from console_gg.games import blackjack


class BlackjackDealingTests(unittest.TestCase):
    def test_deal_and_show_renders_the_table_after_the_draw(self) -> None:
        deck = [("10", "H")]
        player: list[blackjack.Card] = []
        dealer: list[blackjack.Card] = []

        with (
            patch.object(blackjack, "_show_round") as show_round,
            patch.object(blackjack, "animated_pause") as pause,
        ):
            dealt = blackjack._deal_and_show(
                deck,
                player,
                player,
                dealer,
                100,
                10,
                status="DEALING",
            )

        self.assertEqual(dealt, ("10", "H"))
        self.assertEqual(player, [("10", "H")])
        show_round.assert_called_once_with(
            player,
            dealer,
            100,
            10,
            reveal_dealer=False,
            status="DEALING",
            shoe_remaining=0,
        )
        pause.assert_called_once_with(blackjack.DEAL_DELAY)

    def test_dealer_turn_renders_every_dealer_draw_revealed(self) -> None:
        deck = [("2", "H"), ("6", "C")]
        player = [("K", "D"), ("7", "C")]
        dealer = [("10", "S")]

        with (
            patch.object(blackjack, "_show_round") as show_round,
            patch.object(blackjack, "animated_pause"),
        ):
            blackjack._dealer_turn(deck, dealer, player, 100, 10)

        self.assertEqual(dealer, [("10", "S"), ("6", "C"), ("2", "H")])
        self.assertEqual(show_round.call_count, 2)
        for call in show_round.call_args_list:
            self.assertIs(call.kwargs["reveal_dealer"], True)
            self.assertEqual(call.kwargs["status"], "DEALER TURN")

    def test_opening_deal_starts_from_empty_table_then_reveals_each_card(self) -> None:
        deck = [("9", "S"), ("5", "H"), ("K", "D"), ("A", "C")]
        player: list[blackjack.Card] = []
        dealer: list[blackjack.Card] = []
        snapshots: list[tuple[list[blackjack.Card], list[blackjack.Card], dict[str, object]]] = []

        def snapshot(
            shown_player: list[blackjack.Card],
            shown_dealer: list[blackjack.Card],
            *_args: object,
            **kwargs: object,
        ) -> None:
            snapshots.append((list(shown_player), list(shown_dealer), dict(kwargs)))

        with (
            patch.object(blackjack, "_show_round", side_effect=snapshot) as show_round,
            patch.object(blackjack, "animated_pause") as pause,
        ):
            blackjack._deal_opening_hands(deck, player, dealer, 100, 10)

        self.assertEqual(player, [("A", "C"), ("5", "H")])
        self.assertEqual(dealer, [("K", "D"), ("9", "S")])
        self.assertEqual(show_round.call_count, 5)
        self.assertEqual(
            snapshots,
            [
                ([], [], {"reveal_dealer": False, "status": "DEALING", "shoe_remaining": 4}),
                ([("A", "C")], [], {"reveal_dealer": False, "status": "DEALING", "shoe_remaining": 3}),
                (
                    [("A", "C")],
                    [("K", "D")],
                    {"reveal_dealer": False, "status": "DEALING", "shoe_remaining": 2},
                ),
                (
                    [("A", "C"), ("5", "H")],
                    [("K", "D")],
                    {"reveal_dealer": False, "status": "DEALING", "shoe_remaining": 1},
                ),
                (
                    [("A", "C"), ("5", "H")],
                    [("K", "D"), ("9", "S")],
                    {"reveal_dealer": False, "status": "DEALING", "shoe_remaining": 0},
                ),
            ],
        )
        self.assertEqual(pause.call_count, 5)


if __name__ == "__main__":
    unittest.main()
