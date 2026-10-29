#!/usr/bin/env python3
"""A classic Tetris game in one file.

Install (from this folder):

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt

Run:

    python main.py

The Game class holds the rules (movement, rotation, line clears, score).
main() is the Pygame loop: read keys, update the game, draw the screen.
"""

import json
import random
from pathlib import Path

import pygame

# The window is wider than the board so the score and controls fit beside it.
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
FPS = 60

# A standard Tetris board is 10 columns wide and 20 rows tall.
COLS = 10
ROWS = 20
CELL = 30
BOARD_X = 40
BOARD_Y = 50
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL

# x is the column (0 is the left edge). y is the row (0 is the top).
# y grows downward, same as the screen.
SPAWN_X = 3
SPAWN_Y = 0

SIDE_X = 384
PANEL_W = 476

# Gravity. Level 1 waits 800 ms. Each level is a bit faster, down to a floor
# so the game stays playable.
FALL_START_MS = 800
FALL_SPEED_FACTOR = 0.85
MIN_FALL_MS = 60
LINES_PER_LEVEL = 10

# Holding Left or Right: wait DAS_DELAY_MS, then repeat every MOVE_REPEAT_MS.
# That way a tap moves one square and holding the key slides.
DAS_DELAY_MS = 170
MOVE_REPEAT_MS = 45
# After the piece lands it can still slide or rotate for this long, then it
# sticks. Down and Space skip the wait and place the piece immediately.
LOCK_DELAY_MS = 500

HARD_DROP_SCORE = 2
# One, two, three, and four lines. Multiplied by the current level.
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}

# Tried in order when a rotation would overlap a wall or a block.
# (0, -1) and (0, -2) let a piece rotate when it is against the floor.
KICKS = ((0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1), (0, -2))

# Classic colors: I cyan, O yellow, T purple, S green, Z red, J blue, L orange.
COLORS = {
    "I": (56, 220, 230),
    "O": (242, 206, 62),
    "T": (176, 96, 240),
    "S": (86, 214, 110),
    "Z": (236, 82, 96),
    "J": (72, 126, 242),
    "L": (242, 154, 58),
}

BG = (15, 17, 26)
BOARD_BG = (12, 14, 22)
EMPTY = (30, 34, 48)
PANEL = (26, 30, 44)
PANEL_EDGE = (62, 72, 102)
TEXT = (236, 240, 248)
MUTED = (154, 164, 186)
ACCENT = (126, 214, 255)
DANGER = (255, 112, 128)
# Pieces keep their own color while they fall. Once they lock, they turn pink.
DROPPED = (255, 122, 184)

# Each piece has 4 rotations. A rotation is 4 squares in a 4x4 box.
# (0, 0) is the top-left of that box. The piece's board position is where
# that top-left sits, so square (2, 1) on a piece at (3, 0) lands on column 5, row 1.
SHAPES = {
    "I": (
        ((0, 1), (1, 1), (2, 1), (3, 1)),
        ((2, 0), (2, 1), (2, 2), (2, 3)),
        ((0, 2), (1, 2), (2, 2), (3, 2)),
        ((1, 0), (1, 1), (1, 2), (1, 3)),
    ),
    "O": (
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
    ),
    "T": (
        ((1, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (1, 2)),
        ((1, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "S": (
        ((1, 0), (2, 0), (0, 1), (1, 1)),
        ((1, 0), (1, 1), (2, 1), (2, 2)),
        ((1, 1), (2, 1), (0, 2), (1, 2)),
        ((0, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "Z": (
        ((0, 0), (1, 0), (1, 1), (2, 1)),
        ((2, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (1, 2), (2, 2)),
        ((1, 0), (0, 1), (1, 1), (0, 2)),
    ),
    "J": (
        ((0, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (2, 2)),
        ((1, 0), (1, 1), (0, 2), (1, 2)),
    ),
    "L": (
        ((2, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (1, 2), (2, 2)),
        ((0, 1), (1, 1), (2, 1), (0, 2)),
        ((0, 0), (1, 0), (1, 1), (1, 2)),
    ),
}

# One key per action. Esc always quits, and K always opens keyboard settings,
# so those two cannot be chosen as bindings.
ACTIONS = (
    ("move_left", "Move Left"),
    ("move_right", "Move Right"),
    ("rotate", "Rotate"),
    ("drop", "Drop"),
    ("rotate_back", "Rotate Back"),
    ("pause", "Pause"),
    ("restart", "Restart"),
)

DEFAULT_KEYS = {
    "move_left": pygame.K_LEFT,
    "move_right": pygame.K_RIGHT,
    "rotate": pygame.K_UP,
    "drop": pygame.K_DOWN,
    "rotate_back": pygame.K_z,
    "pause": pygame.K_p,
    "restart": pygame.K_r,
}

RESERVED_KEYS = (pygame.K_ESCAPE, pygame.K_k)
CONTROLS_PATH = Path(__file__).with_name("controls.json")

KEY_LABELS = {
    pygame.K_LEFT: "←",
    pygame.K_RIGHT: "→",
    pygame.K_UP: "↑",
    pygame.K_DOWN: "↓",
    pygame.K_SPACE: "Space",
    pygame.K_RETURN: "Enter",
    pygame.K_KP_ENTER: "Enter",
    pygame.K_TAB: "Tab",
    pygame.K_BACKSPACE: "Backspace",
    pygame.K_LSHIFT: "L Shift",
    pygame.K_RSHIFT: "R Shift",
    pygame.K_LCTRL: "L Ctrl",
    pygame.K_RCTRL: "R Ctrl",
    pygame.K_LALT: "L Alt",
    pygame.K_RALT: "R Alt",
    pygame.K_CAPSLOCK: "Caps Lock",
    pygame.K_ESCAPE: "Esc",
}


def key_label(key):
    """Short name drawn on the key cap and in the help panel."""
    if key is None:
        return "—"
    if key in KEY_LABELS:
        return KEY_LABELS[key]
    name = pygame.key.name(key)
    if not name or name == "unknown key":
        return "Key"
    if len(name) == 1:
        return name.upper()
    return name.title()


class KeyBindings:
    """Which key runs each action. Changes are stored in controls.json."""

    def __init__(self, path=CONTROLS_PATH):
        self.path = Path(path)
        self.keys = dict(DEFAULT_KEYS)
        self.load()

    def load(self):
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return
        if not isinstance(saved, dict):
            return
        assigned = {}
        used = set()
        for action, _label in ACTIONS:
            key = self._decode(saved.get(action))
            if key is None or key in used:
                continue
            assigned[action] = key
            used.add(key)
        for action, default in DEFAULT_KEYS.items():
            if action in assigned:
                continue
            if default in used:
                assigned[action] = None
            else:
                assigned[action] = default
                used.add(default)
        self.keys = assigned

    def _decode(self, raw):
        if not isinstance(raw, str):
            return None
        try:
            key = pygame.key.key_code(raw)
        except (ValueError, LookupError):
            return None
        if key in RESERVED_KEYS:
            return None
        return key

    def save(self):
        data = {}
        for action, _label in ACTIONS:
            key = self.keys.get(action)
            if key is None:
                continue
            data[action] = pygame.key.name(key)
        try:
            self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    def action_for(self, key):
        for action, bound in self.keys.items():
            if bound == key:
                return action
        return None

    def label(self, action):
        return key_label(self.keys.get(action))

    def set_key(self, action, key):
        """Bind action to key. The action that had this key receives the old one."""
        if key in RESERVED_KEYS:
            return False
        owner = self.action_for(key)
        previous = self.keys.get(action)
        if owner is not None and owner != action:
            self.keys[owner] = previous
        self.keys[action] = key
        self.save()
        return True

    def reset(self):
        self.keys = dict(DEFAULT_KEYS)
        self.save()


def control_rows(bindings):
    """Help-panel pairs: (key name, what it does), two per row."""

    def entry(action, description):
        return bindings.label(action), description

    return (
        (entry("move_left", "Move left"), entry("rotate", "Rotate")),
        (entry("move_right", "Move right"), entry("drop", "Drop")),
        (entry("rotate_back", "Rotate back"), entry("pause", "Pause")),
        (entry("restart", "Restart"), ("Esc", "Quit")),
    )


def fall_delay(level):
    """Milliseconds between automatic drops at this level."""
    delay = int(FALL_START_MS * (FALL_SPEED_FACTOR ** (level - 1)))
    return max(MIN_FALL_MS, delay)


def empty_board():
    """A 20 by 10 grid. board[row][column] is None or a piece letter.

    Each row is its own list. Reusing one list for every row would make
    filling a cell fill the whole board.
    """
    return [[None for _ in range(COLS)] for _ in range(ROWS)]


def cells_fit(board, cells):
    """True when every square is inside the board and not already filled."""
    for x, y in cells:
        if x < 0 or x >= COLS or y < 0 or y >= ROWS:
            return False
        if board[y][x] is not None:
            return False
    return True


def clear_lines(board):
    """Drop full rows out and let the rows above fall.

    Surviving rows are packed to the bottom. New empty rows are added at
    the top, which is the same as each row falling once per cleared line
    below it. Returns the new board and how many rows were cleared.
    """
    survivors = [row[:] for row in board if None in row]
    cleared = ROWS - len(survivors)
    blanks = [[None for _ in range(COLS)] for _ in range(cleared)]
    return blanks + survivors, cleared


class Piece:
    """One falling piece: a letter, a rotation, and a position on the board."""

    def __init__(self, kind):
        self.kind = kind
        self.rotation = 0
        self.x = SPAWN_X
        self.y = SPAWN_Y

    def cells(self, rotation=None, x=None, y=None):
        """Board squares this piece would cover, optionally at another pose."""
        rotation = self.rotation if rotation is None else rotation
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(x + cx, y + cy) for cx, cy in SHAPES[self.kind][rotation]]


class SevenBag:
    """Deals all seven pieces in a random order, then shuffles them again.

    A plain random pick can go a long time without one piece. A bag cannot:
    each group of seven contains every piece once.
    """

    def __init__(self, rng):
        self.rng = rng
        self.queue = []

    def _refill(self):
        kinds = list(SHAPES)
        self.rng.shuffle(kinds)
        self.queue.extend(kinds)

    def pop(self):
        if not self.queue:
            self._refill()
        return self.queue.pop(0)

    def peek(self):
        if not self.queue:
            self._refill()
        return self.queue[0]


class Game:
    """Board, falling piece, score, and the rules that change them."""

    def __init__(self, rng=None, bindings=None):
        self.rng = rng or random.Random()
        self.bindings = bindings if bindings is not None else KeyBindings()
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
        self.bag = SevenBag(self.rng)
        self.piece = None
        self.release_inputs()
        self._spawn()

    def release_inputs(self):
        """Forget held keys, so the piece stops if the window loses focus."""
        self.hold_left = False
        self.hold_right = False
        self.horiz_timer = DAS_DELAY_MS

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
        self._spawn()

    def update(self, dt):
        """Advance timers by dt milliseconds. At most one gravity drop per call."""
        if self.paused or self.game_over or self.piece is None:
            return
        self._slide(dt)
        if self.game_over:
            return
        self._gravity(dt)
        self._tick_lock(dt)

    def _slide(self, dt):
        if self.hold_left == self.hold_right:
            self.horiz_timer = DAS_DELAY_MS
            return
        self.horiz_timer -= dt
        if self.horiz_timer > 0:
            return
        self.horiz_timer = MOVE_REPEAT_MS
        self.try_move(-1 if self.hold_left else 1, 0)

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

        if action == "move_left":
            self.hold_left = True
            self.horiz_timer = DAS_DELAY_MS
            self.try_move(-1, 0)
        elif action == "move_right":
            self.hold_right = True
            self.horiz_timer = DAS_DELAY_MS
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


def shade(color, amount):
    return tuple(max(0, min(255, channel + amount)) for channel in color)


def make_fonts():
    names = ["dejavusans", "freesans", "liberation sans", "arial"]

    def font(size, bold=False):
        return pygame.font.SysFont(names, size, bold=bold)

    return {
        "title": font(52, True),
        "tag": font(18),
        "label": font(14, True),
        "value": font(30, True),
        "body": font(18),
        "small": font(16),
        "overlay": font(40, True),
        "section": font(16, True),
    }


def cell_origin(column, row):
    return BOARD_X + column * CELL, BOARD_Y + row * CELL


def draw_panel(surface, rect):
    pygame.draw.rect(surface, (8, 9, 14), rect.move(0, 4), border_radius=14)
    pygame.draw.rect(surface, PANEL, rect, border_radius=14)
    pygame.draw.rect(surface, PANEL_EDGE, rect, width=2, border_radius=14)


def draw_block(surface, x, y, size, color):
    rect = pygame.Rect(x + 1, y + 1, size - 2, size - 2)
    pygame.draw.rect(surface, color, rect, border_radius=4)
    shine = pygame.Rect(rect.x + 3, rect.y + 3, rect.w - 6, max(2, rect.h // 7))
    pygame.draw.rect(surface, shade(color, 85), shine, border_radius=2)


def draw_cells(surface, cells, color):
    for column, row in cells:
        if 0 <= column < COLS and 0 <= row < ROWS:
            x, y = cell_origin(column, row)
            draw_block(surface, x, y, CELL, color)


def draw_board(surface, game):
    outer = pygame.Rect(BOARD_X - 8, BOARD_Y - 8, BOARD_W + 16, BOARD_H + 16)
    draw_panel(surface, outer)
    pygame.draw.rect(surface, BOARD_BG, (BOARD_X, BOARD_Y, BOARD_W, BOARD_H))

    for row in range(ROWS):
        for column in range(COLS):
            x, y = cell_origin(column, row)
            pygame.draw.rect(surface, EMPTY, (x + 1, y + 1, CELL - 2, CELL - 2), border_radius=4)

    for row in range(ROWS):
        for column in range(COLS):
            kind = game.board[row][column]
            if kind is not None:
                x, y = cell_origin(column, row)
                draw_block(surface, x, y, CELL, DROPPED)

    piece = game.piece
    if piece is None:
        return

    draw_cells(surface, piece.cells(), COLORS[piece.kind])


def draw_shape_preview(surface, kind, box):
    cells = SHAPES[kind][0]
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    size = 26
    width = (max(xs) - min(xs) + 1) * size
    height = (max(ys) - min(ys) + 1) * size
    origin_x = box.centerx - width // 2
    origin_y = box.centery - height // 2
    color = COLORS[kind]
    for x, y in cells:
        pixel_x = origin_x + (x - min(xs)) * size
        pixel_y = origin_y + (y - min(ys)) * size
        draw_block(surface, pixel_x, pixel_y, size, color)


class KeyboardSettings:
    """The screen where a player picks a new key for an action.

    Esc closes it (and cancels a key capture). K toggles it. Neither key can
    be assigned, so the player can always get back out.
    """

    def __init__(self, bindings):
        self.bindings = bindings
        self.open = False
        self.selected = 0
        self.capturing = False
        self.note = ""
        self.note_bad = False
        self.panel_rect = None
        self.row_rects = []
        self.reset_rect = None
        self.keyboard_rect = None

    def toggle(self, game):
        self.open = not self.open
        self.capturing = False
        self.note = ""
        self.note_bad = False
        game.release_inputs()

    def handle_event(self, event, game):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._click(event.pos, game)
            return
        if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
            return
        if self.capturing:
            self._capture(event.key)
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_k):
            self.toggle(game)
            return
        count = len(ACTIONS) + 1
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % count
            self.note = ""
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % count
            self.note = ""
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.activate()

    def activate(self):
        if self.selected >= len(ACTIONS):
            self.bindings.reset()
            self.capturing = False
            self.note = "Defaults restored."
            self.note_bad = False
            return
        self.capturing = True
        self.note = ""
        self.note_bad = False

    def _capture(self, key):
        if key == pygame.K_ESCAPE:
            self.capturing = False
            self.note = ""
            self.note_bad = False
            return
        action = ACTIONS[self.selected][0]
        if self.bindings.set_key(action, key):
            self.capturing = False
            self.note = ""
            self.note_bad = False
            return
        self.note = "K and Esc stay fixed. Choose a different key."
        self.note_bad = True

    def _click(self, pos, game):
        if self.panel_rect is not None and not self.panel_rect.collidepoint(pos):
            self.toggle(game)
            return
        if self.reset_rect is not None and self.reset_rect.collidepoint(pos):
            self.selected = len(ACTIONS)
            self.activate()
            return
        for index, rect in enumerate(self.row_rects):
            if rect.collidepoint(pos):
                self.selected = index
                self.capturing = True
                self.note = ""
                self.note_bad = False
                return


def draw_sidebar(surface, game, fonts, settings):
    x = SIDE_X
    y = 36

    title = fonts["title"].render("TETRIS", True, TEXT)
    surface.blit(title, (x, y))
    y += title.get_height() + 8

    for index, kind in enumerate(("I", "O", "T", "S", "Z", "J", "L")):
        pygame.draw.rect(
            surface,
            COLORS[kind],
            (x + index * 34, y, 28, 6),
            border_radius=3,
        )
    y += 18

    tag = fonts["tag"].render("Clear a full line and it disappears.", True, MUTED)
    surface.blit(tag, (x, y))
    y += tag.get_height() + 16

    stats = pygame.Rect(x, y, PANEL_W, 132)
    draw_panel(surface, stats)
    labels = ("SCORE", "LEVEL", "LINES")
    values = (f"{game.score:,}", str(game.level), str(game.lines))
    column_w = PANEL_W // 3
    for index, (label, value) in enumerate(zip(labels, values)):
        label_img = fonts["label"].render(label, True, MUTED)
        value_img = fonts["value"].render(value, True, TEXT)
        center = x + column_w * index + column_w // 2
        surface.blit(label_img, label_img.get_rect(center=(center, stats.y + 28)))
        surface.blit(value_img, value_img.get_rect(center=(center, stats.y + 58)))

    bar_x = stats.x + 20
    bar_w = stats.w - 40
    filled = game.lines % LINES_PER_LEVEL
    gap = 5
    segment_w = (bar_w - gap * 9) // 10
    for index in range(LINES_PER_LEVEL):
        color = ACCENT if index < filled else (42, 48, 68)
        segment = pygame.Rect(bar_x + index * (segment_w + gap), stats.y + 86, segment_w, 8)
        pygame.draw.rect(surface, color, segment, border_radius=3)

    remaining = game.lines_until_level()
    word = "line" if remaining == 1 else "lines"
    hint = fonts["small"].render(f"Next level in {remaining} {word}", True, MUTED)
    surface.blit(hint, hint.get_rect(center=(stats.centerx, stats.bottom - 18)))
    y = stats.bottom + 14

    nxt = pygame.Rect(x, y, PANEL_W, 148)
    draw_panel(surface, nxt)
    next_label = fonts["section"].render("NEXT", True, MUTED)
    surface.blit(next_label, (nxt.x + 18, nxt.y + 12))
    preview = pygame.Rect(nxt.x + 18, nxt.y + 36, nxt.w - 36, nxt.h - 48)
    draw_shape_preview(surface, game.coming_next(), preview)
    y = nxt.bottom + 14

    help_panel = pygame.Rect(x, y, PANEL_W, 208)
    draw_panel(surface, help_panel)
    heading = fonts["section"].render("HOW TO PLAY", True, ACCENT)
    surface.blit(heading, (help_panel.x + 18, help_panel.y + 12))

    button_label = fonts["section"].render("KEYBOARD", True, ACCENT)
    button = button_label.get_rect(topright=(help_panel.right - 26, help_panel.y + 14))
    button_bg = button.inflate(16, 8)
    pygame.draw.rect(surface, (36, 44, 68), button_bg, border_radius=8)
    surface.blit(button_label, button)
    settings.keyboard_rect = button_bg

    rows = control_rows(game.bindings)
    font = fonts["body"]
    left_key_w = max(font.size(key)[0] for (key, _), _ in rows)
    left_act_w = max(font.size(action)[0] for (_, action), _ in rows)
    right_key_w = max(font.size(key)[0] for _, (key, _) in rows)
    right_act_w = max(font.size(action)[0] for _, (_, action) in rows)
    gap = 12
    column_gap = 28
    used = left_key_w + gap + left_act_w + column_gap + right_key_w + gap + right_act_w
    limit = help_panel.w - 36
    if used > limit:
        column_gap = max(8, column_gap - (used - limit))
    x0 = help_panel.x + 18
    x1 = x0 + left_key_w + gap
    x2 = x1 + left_act_w + column_gap
    x3 = x2 + right_key_w + gap
    row_y = help_panel.y + 42
    for (left_key, left_action), (right_key, right_action) in rows:
        surface.blit(font.render(left_key, True, ACCENT), (x0, row_y))
        surface.blit(font.render(left_action, True, TEXT), (x1, row_y))
        surface.blit(font.render(right_key, True, ACCENT), (x2, row_y))
        surface.blit(font.render(right_action, True, TEXT), (x3, row_y))
        row_y += 28
    hint = fonts["small"].render("K opens keyboard settings", True, MUTED)
    surface.blit(hint, (help_panel.x + 18, row_y + 2))


def draw_status(surface, game, fonts):
    if not game.paused and not game.game_over:
        return
    shade_layer = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
    shade_layer.fill((8, 10, 18, 188))
    surface.blit(shade_layer, (BOARD_X, BOARD_Y))

    if game.game_over:
        title, color = "GAME OVER", DANGER
        restart = game.bindings.label("restart")
        lines = (f"Score {game.score:,}", f"Press {restart} to restart")
    else:
        title, color = "PAUSED", ACCENT
        resume = game.bindings.label("pause")
        lines = (f"Press {resume} to resume",)

    center_x = BOARD_X + BOARD_W // 2
    center_y = BOARD_Y + BOARD_H // 2
    title_img = fonts["overlay"].render(title, True, color)
    surface.blit(title_img, title_img.get_rect(center=(center_x, center_y - 28)))
    for index, line in enumerate(lines):
        img = fonts["body"].render(line, True, TEXT)
        surface.blit(img, img.get_rect(center=(center_x, center_y + 18 + index * 28)))


def draw_keyboard_settings(surface, fonts, settings):
    shade_layer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    shade_layer.fill((8, 10, 18, 188))
    surface.blit(shade_layer, (0, 0))

    row_h = 46
    header = 96
    footer = 52
    panel_h = header + row_h * len(ACTIONS) + 8 + row_h + footer
    panel = pygame.Rect(0, 0, 540, panel_h)
    panel.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
    settings.panel_rect = panel
    draw_panel(surface, panel)

    title = fonts["value"].render("KEYBOARD", True, TEXT)
    surface.blit(title, (panel.x + 28, panel.y + 18))
    subtitle = fonts["small"].render(
        "Click a row or press Enter, then press the new key.", True, MUTED
    )
    surface.blit(subtitle, (panel.x + 28, panel.y + 56))

    settings.row_rects = []
    top = panel.y + header
    for index, (action, label) in enumerate(ACTIONS):
        rect = pygame.Rect(panel.x + 24, top + index * row_h, panel.w - 48, row_h - 6)
        settings.row_rects.append(rect)
        selected = index == settings.selected
        if selected:
            pygame.draw.rect(surface, (46, 58, 88), rect, border_radius=8)
        name_color = ACCENT if selected else TEXT
        name = fonts["body"].render(label, True, name_color)
        surface.blit(name, (rect.x + 14, rect.centery - name.get_height() // 2))
        waiting = settings.capturing and selected
        chip_text = "Press a key" if waiting else settings.bindings.label(action)
        chip_color = BG if waiting else TEXT
        chip = fonts["body"].render(chip_text, True, chip_color)
        chip_rect = chip.get_rect(midright=(rect.right - 16, rect.centery))
        chip_bg = chip_rect.inflate(18, 10)
        pygame.draw.rect(surface, ACCENT if waiting else (62, 72, 102), chip_bg, border_radius=6)
        surface.blit(chip, chip_rect)

    reset = pygame.Rect(panel.x + 24, top + len(ACTIONS) * row_h + 8, panel.w - 48, row_h - 6)
    settings.reset_rect = reset
    if settings.selected == len(ACTIONS):
        pygame.draw.rect(surface, (46, 58, 88), reset, border_radius=8)
    reset_color = ACCENT if settings.selected == len(ACTIONS) else TEXT
    reset_label = fonts["body"].render("Reset defaults", True, reset_color)
    surface.blit(reset_label, (reset.x + 14, reset.centery - reset_label.get_height() // 2))

    if settings.note:
        footer_text = settings.note
    elif settings.capturing:
        footer_text = "Press a new key. Esc cancels."
    else:
        footer_text = "Esc closes this screen."
    footer_color = DANGER if settings.note_bad else MUTED
    footer_img = fonts["small"].render(footer_text, True, footer_color)
    surface.blit(footer_img, footer_img.get_rect(midbottom=(panel.centerx, panel.bottom - 16)))


def draw(surface, game, fonts, settings):
    surface.fill(BG)
    draw_board(surface, game)
    draw_sidebar(surface, game, fonts, settings)
    draw_status(surface, game, fonts)
    if settings.open:
        draw_keyboard_settings(surface, fonts, settings)


def main():
    pygame.init()
    pygame.display.set_caption("Tetris")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = make_fonts()
    bindings = KeyBindings()
    game = Game(bindings=bindings)
    settings = KeyboardSettings(bindings)

    running = True
    while running:
        # dt is the time since the last frame. Speed then does not depend
        # on how fast this computer happens to draw.
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                game.release_inputs()
            elif settings.open:
                settings.handle_event(event, game)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_k:
                    settings.toggle(game)
                else:
                    game.handle_key_down(event.key)
            elif event.type == pygame.KEYUP:
                game.handle_key_up(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                rect = settings.keyboard_rect
                if rect is not None and rect.collidepoint(event.pos):
                    settings.toggle(game)

        if not settings.open:
            game.update(dt)
        draw(screen, game, fonts, settings)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
