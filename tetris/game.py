"""Live game: movement, gravity, locking, scoring, and garbage."""

import random

from tetris.board import Piece, SevenBag, cells_fit, clear_lines, empty_board, fall_delay
from tetris.bot import BotController
from tetris.constants import (
    ATTACK_LINES,
    COLS,
    GARBAGE_RISE_MS,
    HARD_DROP_SCORE,
    HOLD_TO_WALL_MS,
    KICKS,
    LINE_SCORES,
    LINES_PER_LEVEL,
    LOCK_DELAY_MS,
)
from tetris.controls import KeyBindings


class Game:
    """Board, falling piece, score, and the rules that change them."""

    def __init__(self, rng=None, bindings=None):
        self.rng = rng or random.Random()
        self.bindings = bindings if bindings is not None else KeyBindings()
        self.mode = "player"
        self.bot = BotController()
        self.shared_view = None
        self.outgoing_attack = 0
        self.garbage_offset_rows = 0.0
        self.piece_fix_rows = 0.0
        self.restart()

    def restart(self):
        """Clear the board and start again from level 1."""
        self.board = empty_board()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.fall_ms = 0
        self.lock_ms = None
        self.piece = None
        self.outgoing_attack = 0
        self.garbage_offset_rows = 0.0
        self.piece_fix_rows = 0.0
        self.release_inputs()
        self.bot.cancel()
        if self.shared_view is None:
            self.bag = SevenBag(self.rng)
        else:
            self.bag = self.shared_view
        self._spawn()

    def set_mode(self, mode):
        """Switch between player and bot control. Pending bot moves are dropped."""
        if mode not in ("player", "bot") or mode == self.mode:
            return
        self.mode = mode
        self.release_inputs()
        self.bot.cancel()
        self.bot.sync_status(self)

    def release_inputs(self):
        """Forget held keys, so the piece stops if the window loses focus."""
        self.hold_left = False
        self.hold_right = False
        self.horiz_timer = HOLD_TO_WALL_MS
        self.horiz_dashed = False

    def coming_next(self):
        """The piece that will spawn after this one locks."""
        return self.bag.peek()

    def lines_until_level(self):
        """How many more cleared lines raise the level."""
        return LINES_PER_LEVEL - (self.lines % LINES_PER_LEVEL)

    def _spawn(self):
        self.piece = Piece(self.bag.pop())
        self.fall_ms = 0
        self.lock_ms = None
        # The stack has reached the top when a new piece has nowhere to appear.
        if not cells_fit(self.board, self.piece.cells()):
            self.game_over = True
            return
        self._update_lock(boost_if_airborne=False)

    def try_move(self, dx, dy):
        """Move the falling piece if the destination is free."""
        if self.piece is None or self.game_over or self.paused:
            return False
        new_x = self.piece.x + dx
        new_y = self.piece.y + dy
        if not cells_fit(self.board, self.piece.cells(x=new_x, y=new_y)):
            return False
        self.piece.x = new_x
        self.piece.y = new_y
        # A downward move that lands starts the lock timer. A sideways move
        # off a ledge cancels it. Sliding along the floor does not restart it,
        # or the piece would never stick while a key is held.
        self._update_lock(boost_if_airborne=(dy == 0))
        return True

    def try_rotate(self, direction):
        """Rotate clockwise (direction 1) or counter-clockwise (direction -1).

        If the new pose overlaps something, try nudging the piece (a wall
        kick) before giving up. The piece stays put when every nudge fails.
        """
        if self.piece is None or self.game_over or self.paused:
            return False
        new_rotation = (self.piece.rotation + direction) % 4
        for dx, dy in KICKS:
            kicked_x = self.piece.x + dx
            kicked_y = self.piece.y + dy
            cells = self.piece.cells(new_rotation, kicked_x, kicked_y)
            if cells_fit(self.board, cells):
                self.piece.rotation = new_rotation
                self.piece.x = kicked_x
                self.piece.y = kicked_y
                self._update_lock(boost_if_airborne=True)
                return True
        return False

    def hard_drop(self):
        """Drop the piece to the landing row and place it there."""
        if self.piece is None or self.game_over or self.paused:
            return
        distance = 0
        while self.try_move(0, 1):
            distance += 1
        self.score += distance * HARD_DROP_SCORE
        self.lock_ms = None
        self.lock_piece()

    def lock_piece(self):
        """Write the falling piece onto the board, clear lines, and spawn."""
        if self.piece is None or self.game_over:
            return
        cells = self.piece.cells()
        if not cells_fit(self.board, cells):
            self.game_over = True
            self.lock_ms = None
            return
        for x, y in cells:
            self.board[y][x] = self.piece.kind
        self.board, cleared = clear_lines(self.board)
        if cleared:
            # Score with the level the player is on now, then maybe raise it.
            self.score += LINE_SCORES[cleared] * self.level
            self.lines += cleared
            self.level = self.lines // LINES_PER_LEVEL + 1
            self.outgoing_attack += ATTACK_LINES.get(cleared, 0)
        self._spawn()

    def take_attack(self):
        """Garbage lines earned since the last exchange, then reset the count."""
        sent = self.outgoing_attack
        self.outgoing_attack = 0
        return sent

    def add_garbage(self, count):
        """Push count junk rows up from the floor. Each row has one open cell.

        The falling piece is thrown away so it never sits on the incoming stack.
        """
        if count <= 0 or self.game_over:
            return
        self._discard_falling_piece()
        for _ in range(count):
            gap = self.rng.randrange(COLS)
            self.board.pop(0)
            row = ["G"] * COLS
            row[gap] = None
            self.board.append(row)
        self._begin_garbage_rise(count)
        if not self.game_over:
            self._spawn()
            # The replacement is already at spawn. Do not slide it with the stack.
            self.piece_fix_rows = self.garbage_offset_rows

    def _discard_falling_piece(self):
        """Clear the live piece without locking it onto the board."""
        self.piece = None
        self.lock_ms = None
        self.fall_ms = 0
        self.release_inputs()
        self.bot.cancel()

    def _begin_garbage_rise(self, count):
        """Queue a bottom-up slide. New garbage adds to a rise already in progress."""
        self.garbage_offset_rows += count

    def tick_garbage_rise(self, dt):
        if self.garbage_offset_rows <= 0:
            self.piece_fix_rows = 0.0
            return
        before = self.garbage_offset_rows
        self.garbage_offset_rows = max(0.0, before - dt / GARBAGE_RISE_MS)
        self.piece_fix_rows *= self.garbage_offset_rows / before

    def garbage_rise_pixels(self, cell):
        """How far below its resting row a locked block is drawn during the rise."""
        return self.garbage_offset_rows * cell

    def piece_rise_pixels(self, cell):
        """Same slide for the falling piece, minus any nudge that put it back."""
        return (self.garbage_offset_rows - self.piece_fix_rows) * cell

    def update(self, dt):
        """Advance timers by dt milliseconds. At most one gravity drop per call."""
        if self.paused:
            return
        self.tick_garbage_rise(dt)
        if self.game_over or self.piece is None:
            return
        self._slide(dt)
        if self.game_over:
            return
        self._gravity(dt)
        self._tick_lock(dt)

    def _slide(self, dt):
        if self.hold_left == self.hold_right:
            self.horiz_timer = HOLD_TO_WALL_MS
            self.horiz_dashed = False
            return
        if self.horiz_dashed:
            return
        self.horiz_timer -= dt
        if self.horiz_timer > 0:
            return
        self.horiz_dashed = True
        self._slide_to_wall(-1 if self.hold_left else 1)

    def _slide_to_wall(self, dx):
        """Move until a wall or a filled cell blocks this direction."""
        while self.try_move(dx, 0):
            pass

    def _gravity(self, dt):
        self.fall_ms += dt
        delay = fall_delay(self.level)
        if self.fall_ms < delay:
            return
        # Drop once and restart the timer. A long hitch then cannot
        # slam the piece from the top to the bottom in one frame.
        self.fall_ms = 0
        if not self.try_move(0, 1):
            self._arm_lock()

    def _arm_lock(self):
        """Start the lock timer once. Later calls do not refresh it."""
        if self.lock_ms is None:
            self.lock_ms = LOCK_DELAY_MS

    def _update_lock(self, boost_if_airborne):
        """Arm the timer when the piece is supported, or cancel it in the air."""
        if self.piece is None or self.game_over:
            return
        airborne = cells_fit(self.board, self.piece.cells(y=self.piece.y + 1))
        if airborne:
            if boost_if_airborne and self.lock_ms is not None:
                # It walked off a ledge. Drop on the next gravity tick
                # instead of hovering until the old timer finishes.
                self.fall_ms = max(self.fall_ms, fall_delay(self.level))
            self.lock_ms = None
        else:
            self._arm_lock()

    def _tick_lock(self, dt):
        if self.lock_ms is None or self.piece is None or self.game_over:
            return
        if cells_fit(self.board, self.piece.cells(y=self.piece.y + 1)):
            self.lock_ms = None
            return
        self.lock_ms -= dt
        if self.lock_ms <= 0:
            self.lock_ms = None
            self.lock_piece()

    def handle_key_down(self, key):
        action = self.bindings.action_for(key)
        if action == "restart":
            self.restart()
            return
        if action == "pause":
            if not self.game_over:
                self.paused = not self.paused
            return
        if self.paused or self.game_over or action is None:
            return
        # Bot Mode owns the falling piece. Pause and restart still work above.
        if self.mode == "bot" and action in ("move_left", "move_right", "rotate", "rotate_back", "drop"):
            return

        if action == "move_left":
            self.hold_left = True
            self.horiz_timer = HOLD_TO_WALL_MS
            self.horiz_dashed = False
            self.try_move(-1, 0)
        elif action == "move_right":
            self.hold_right = True
            self.horiz_timer = HOLD_TO_WALL_MS
            self.horiz_dashed = False
            self.try_move(1, 0)
        elif action == "drop":
            self.hard_drop()
        elif action == "rotate":
            self.try_rotate(1)
        elif action == "rotate_back":
            self.try_rotate(-1)

    def handle_key_up(self, key):
        action = self.bindings.action_for(key)
        if action == "move_left":
            self.hold_left = False
        elif action == "move_right":
            self.hold_right = False
