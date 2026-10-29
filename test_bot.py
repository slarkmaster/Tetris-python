"""Tests for Bot Mode. Run with: .venv/bin/python -m unittest test_bot.py"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

import main


def new_game(seed=1):
    bindings = main.KeyBindings("/tmp/tetris-bot-test-controls.json")
    return main.Game(rng=main.random.Random(seed), bindings=bindings)


def snapshot(board):
    return [row[:] for row in board]


def filled_cells(board):
    return sum(cell is not None for row in board for cell in row)


class BotPlacementTests(unittest.TestCase):
    def test_search_does_not_change_the_live_board(self):
        game = new_game()
        before = snapshot(game.board)
        piece_cells = game.piece.cells()
        path = main.choose_move(game.board, game.piece)
        self.assertIsNotNone(path)
        self.assertEqual(game.board, before)
        self.assertEqual(game.piece.cells(), piece_cells)

    def test_every_kind_has_a_legal_path_on_an_empty_board(self):
        for kind in main.SHAPES:
            game = new_game()
            game.piece = main.Piece(kind)
            path = main.choose_move(game.board, game.piece)
            self.assertTrue(path, kind)
            self.assertEqual(path[-1], "drop")
            self._replay(game, path)

    def test_every_kind_has_a_legal_path_on_a_jagged_stack(self):
        for kind in main.SHAPES:
            game = new_game()
            for x in range(main.COLS):
                for height in range((x * 3) % 5):
                    game.board[main.ROWS - 1 - height][x] = "T"
            game.piece = main.Piece(kind)
            self.assertTrue(main.cells_fit(game.board, game.piece.cells()), kind)
            path = main.choose_move(game.board, game.piece)
            self.assertTrue(path, kind)
            self._replay(game, path)

    def test_line_clear_beats_burying_a_hole(self):
        flat = main.empty_board()
        for x in range(main.COLS):
            flat[main.ROWS - 1][x] = "I"
        buried = main.empty_board()
        for x in range(main.COLS):
            buried[main.ROWS - 1][x] = "I"
        buried[main.ROWS - 1][0] = None
        buried[main.ROWS - 2][0] = "I"
        self.assertGreater(
            main.evaluate_board(flat, 0, main.BOT_WEIGHTS),
            main.evaluate_board(buried, 0, main.BOT_WEIGHTS),
        )
        self.assertGreater(
            main.evaluate_board(main.empty_board(), 1, main.BOT_WEIGHTS),
            main.evaluate_board(main.empty_board(), 0, main.BOT_WEIGHTS),
        )

    def test_bot_fills_a_one_cell_gap_and_clears_the_line(self):
        game = new_game()
        gap = 4
        for x in range(main.COLS):
            if x != gap:
                game.board[main.ROWS - 1][x] = "I"
        game.piece = main.Piece("I")
        path = main.choose_move(game.board, game.piece)
        self._replay(game, path)
        self.assertGreaterEqual(game.lines, 1)
        self.assertGreater(game.score, 0)

    def _replay(self, game, path):
        for action in path:
            piece = game.piece
            self.assertIsNotNone(piece)
            if action != "drop":
                self.assertTrue(game.bot._apply(game, action), action)
                self.assertTrue(main.cells_fit(game.board, game.piece.cells()))
                for x, y in game.piece.cells():
                    self.assertGreaterEqual(x, 0)
                    self.assertLess(x, main.COLS)
                    self.assertGreaterEqual(y, 0)
                    self.assertLess(y, main.ROWS)
            else:
                before_lines = game.lines
                before_cells = filled_cells(game.board)
                before_id = id(game.piece)
                self.assertTrue(game.bot._apply(game, action))
                self.assertFalse(game.game_over)
                self.assertTrue(
                    game.lines != before_lines
                    or filled_cells(game.board) != before_cells
                    or id(game.piece) != before_id
                )


class BotPlayTests(unittest.TestCase):
    def test_player_mode_still_moves_and_clears(self):
        game = new_game()
        self.assertEqual(game.mode, "player")
        start = game.piece.x
        game.handle_key_down(pygame.K_LEFT)
        self.assertEqual(game.piece.x, start - 1)
        game.handle_key_up(pygame.K_LEFT)
        for x in range(4, main.COLS):
            game.board[main.ROWS - 1][x] = "I"
        game.piece = main.Piece("I")
        game.piece.x = 0
        game.hard_drop()
        self.assertGreaterEqual(game.lines, 1)

    def test_bot_ignores_movement_keys(self):
        game = new_game()
        game.set_mode("bot")
        start = game.piece.x
        game.handle_key_down(pygame.K_LEFT)
        game.handle_key_down(pygame.K_RIGHT)
        game.handle_key_down(pygame.K_UP)
        game.handle_key_down(pygame.K_DOWN)
        self.assertEqual(game.piece.x, start)
        self.assertEqual(game.piece.rotation, 0)
        self.assertFalse(game.game_over)

    def test_bot_places_consecutive_pieces(self):
        game = new_game()
        game.set_mode("bot")
        locks = self.play_locks(game, 8)
        self.assertEqual(locks, 8)
        self.assertFalse(game.game_over)
        self.assertGreater(filled_cells(game.board), 0)

    def test_bot_survives_and_clears_lines(self):
        game = new_game(seed=3)
        game.set_mode("bot")
        locks = self.play_locks(game, 24)
        self.assertEqual(locks, 24)
        self.assertFalse(game.game_over)
        self.assertGreaterEqual(game.lines, 1)

    def test_pause_resume_reset_and_game_over(self):
        game = new_game()
        game.set_mode("bot")
        game.bot.update(game, 1)
        self.assertEqual(game.bot.status, "thinking")
        frozen = (game.piece.x, game.piece.rotation, snapshot(game.board))
        game.paused = True
        game.bot.update(game, 5000)
        self.assertEqual((game.piece.x, game.piece.rotation, snapshot(game.board)), frozen)
        self.assertEqual(game.bot.display_status(game), "Paused")
        game.paused = False
        self.play_locks(game, 1)
        self.assertGreater(filled_cells(game.board), 0)

        game.restart()
        self.assertEqual(game.score, 0)
        self.assertEqual(game.lines, 0)
        self.assertEqual(filled_cells(game.board), 0)
        self.assertEqual(game.bot.actions, [])
        self.assertEqual(game.mode, "bot")

        board = snapshot(game.board)
        game.game_over = True
        game.bot.update(game, 5000)
        self.assertEqual(snapshot(game.board), board)
        self.assertEqual(game.bot.status, "game over")
        self.assertEqual(game.bot.actions, [])

    def test_mode_switch_does_not_mix_controls(self):
        game = new_game()
        game.set_mode("bot")
        game.bot.actions = ["left", "drop"]
        game.bot.tracked_id = id(game.piece)
        game.set_mode("player")
        self.assertEqual(game.bot.actions, [])
        start = game.piece.x
        game.handle_key_down(pygame.K_LEFT)
        self.assertEqual(game.piece.x, start - 1)
        game.handle_key_up(pygame.K_LEFT)
        game.set_mode("bot")
        held = game.piece.x
        game.handle_key_down(pygame.K_RIGHT)
        self.assertEqual(game.piece.x, held)
        game.bot.update(game, 1)
        game.bot.update(game, game.bot.step_ms)
        self.assertNotEqual(game.bot.status, "game over")

    def play_locks(self, game, count):
        locks = 0
        seen = id(game.piece)
        for _ in range(count * 40):
            if game.game_over:
                break
            game.bot.update(game, max(game.bot.step_ms, 1))
            if game.piece is None or id(game.piece) != seen:
                locks += 1
                if game.piece is None or locks >= count:
                    break
                seen = id(game.piece)
        return locks


class VersusTests(unittest.TestCase):
    def test_both_boards_start_on_the_same_piece_sequence(self):
        versus = main.Versus(main.KeyBindings("/tmp/tetris-versus-controls.json"))
        self.assertEqual(versus.player.piece.kind, versus.opponent.piece.kind)
        self.assertEqual(versus.player.coming_next(), versus.opponent.coming_next())
        self.assertEqual(versus.opponent.mode, "bot")
        self.assertIsNone(versus.winner())

    def test_attack_table_matches_cleared_lines(self):
        self.assertEqual(main.ATTACK_LINES[1], 0)
        self.assertEqual(main.ATTACK_LINES[2], 2)
        self.assertEqual(main.ATTACK_LINES[3], 3)
        self.assertEqual(main.ATTACK_LINES[4], 4)

    def test_garbage_rises_from_the_bottom_then_settles(self):
        game = new_game()
        game.add_garbage(2)
        cell = 22
        self.assertAlmostEqual(game.garbage_rise_pixels(cell), 2 * cell)
        game.tick_garbage_rise(main.GARBAGE_RISE_MS)
        self.assertAlmostEqual(game.garbage_rise_pixels(cell), cell)
        game.tick_garbage_rise(main.GARBAGE_RISE_MS)
        self.assertEqual(game.garbage_rise_pixels(cell), 0)
        self.assertEqual(game.piece_rise_pixels(cell), 0)
        screen = pygame.display.set_mode((main.WINDOW_WIDTH, main.WINDOW_HEIGHT))
        game.add_garbage(3)
        main.draw_board(screen, game, 16, 52, cell)
        game.tick_garbage_rise(main.GARBAGE_RISE_MS * 1.5)
        main.draw_board(screen, game, 16, 52, cell)

    def test_garbage_rows_have_one_gap_and_drop_the_falling_piece(self):
        game = new_game()
        old = game.piece
        old_kind = old.kind
        game.piece.y = 10
        game.add_garbage(2)
        self.assertFalse(game.game_over)
        self.assertIsNotNone(game.piece)
        self.assertIsNot(game.piece, old)
        self.assertTrue(main.cells_fit(game.board, game.piece.cells()))
        self.assertLess(game.piece.y, 4)
        self.assertFalse(any(cell == old_kind for row in game.board for cell in row))
        junk = [row for row in game.board if any(cell == "G" for cell in row)]
        self.assertEqual(len(junk), 2)
        for row in junk:
            self.assertEqual(row.count(None), 1)
            self.assertEqual(row.count("G"), main.COLS - 1)

    def test_same_step_attacks_cancel(self):
        left = new_game(1)
        right = new_game(2)
        left.outgoing_attack = 4
        right.outgoing_attack = 1
        before = snapshot(left.board)
        main.exchange_attacks(left, right)
        self.assertEqual(snapshot(left.board), before)
        junk = [row for row in right.board if any(cell == "G" for cell in row)]
        self.assertEqual(len(junk), 3)
        left.outgoing_attack = 2
        right.outgoing_attack = 2
        main.exchange_attacks(left, right)
        self.assertEqual(len([row for row in right.board if any(cell == "G" for cell in row)]), 3)

    def test_clearing_lines_queues_an_attack(self):
        game = new_game()
        for x in range(4, main.COLS):
            game.board[main.ROWS - 1][x] = "I"
        game.piece = main.Piece("I")
        game.piece.x = 0
        game.hard_drop()
        self.assertGreaterEqual(game.lines, 1)
        self.assertEqual(game.outgoing_attack, main.ATTACK_LINES[game.lines])

    def test_garbage_flies_then_lands(self):
        versus = main.Versus(main.KeyBindings("/tmp/tetris-versus-controls.json"))
        versus.player.outgoing_attack = 3
        versus.update(1)
        flight = versus.flights[0]
        self.assertEqual(flight.count, 3)
        self.assertTrue(flight.from_left)
        self.assertLess(flight.progress(), 0.05)
        versus.update(main.GARBAGE_FLIGHT_MS / 2)
        self.assertGreater(flight.progress(), 0.4)
        self.assertLess(flight.progress(), 1)
        self.assertEqual(filled_cells(versus.opponent.board), 0)
        versus.update(main.GARBAGE_FLIGHT_MS)
        self.assertEqual(versus.flights, [])
        junk = [row for row in versus.opponent.board if any(cell == "G" for cell in row)]
        self.assertEqual(len(junk), 3)
        screen = pygame.display.set_mode((main.WINDOW_WIDTH, main.WINDOW_HEIGHT))
        versus.player.outgoing_attack = 2
        versus.update(1)
        versus.update(main.GARBAGE_FLIGHT_MS / 3)
        fonts = main.make_fonts()
        session = main.Session(versus.bindings)
        session.mode = "versus"
        session.versus = versus
        settings = main.KeyboardSettings(versus.bindings)
        main.draw_versus(screen, session, fonts, settings)

    def test_player_keys_do_not_move_the_bot_board(self):
        versus = main.Versus(main.KeyBindings("/tmp/tetris-versus-controls.json"))
        bot_x = versus.opponent.piece.x
        versus.player.handle_key_down(pygame.K_LEFT)
        self.assertEqual(versus.opponent.piece.x, bot_x)
        self.assertEqual(versus.player.piece.x, main.SPAWN_X - 1)

    def test_match_plays_and_restart_clears_both_boards(self):
        versus = main.Versus(main.KeyBindings("/tmp/tetris-versus-controls.json"))
        versus.opponent.bot.step_ms = 40
        for _ in range(30):
            versus.update(40)
        self.assertIsNone(versus.winner())
        versus.player.outgoing_attack = 4
        def junk():
            return sum(cell == "G" for row in versus.opponent.board for cell in row)
        before = junk()
        versus.update(1)
        self.assertEqual(len(versus.flights), 1)
        self.assertEqual(junk(), before)
        versus.update(main.GARBAGE_FLIGHT_MS)
        self.assertGreater(junk(), before)
        self.assertEqual(versus.flights, [])
        versus.restart()
        self.assertEqual(versus.flights, [])
        self.assertEqual(filled_cells(versus.player.board), 0)
        self.assertEqual(filled_cells(versus.opponent.board), 0)
        self.assertFalse(versus.player.game_over)
        self.assertFalse(versus.opponent.game_over)
        self.assertEqual(versus.player.piece.kind, versus.opponent.piece.kind)

    def test_top_out_names_the_winner_and_stops_play(self):
        versus = main.Versus(main.KeyBindings("/tmp/tetris-versus-controls.json"))
        versus.player.game_over = True
        piece = versus.opponent.piece.x
        versus.update(500)
        self.assertEqual(versus.winner(), "bot")
        self.assertEqual(versus.opponent.piece.x, piece)


if __name__ == "__main__":
    unittest.main()
