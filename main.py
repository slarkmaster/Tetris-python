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

import random

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

# Two columns of (key, action). Drawn from measured text widths so the
# columns cannot overlap.
CONTROLS = (
    (("Left / Right", "Move"), ("Up or X", "Rotate")),
    (("Down", "Drop"), ("Z", "Rotate back")),
    (("Space", "Drop"), ("P", "Pause")),
    (("R", "Restart"), ("Esc", "Quit")),
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

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
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
        if key == pygame.K_r:
            self.restart()
            return
        if key == pygame.K_p:
            if not self.game_over:
                self.paused = not self.paused
            return
        if self.paused or self.game_over:
            return

        if key == pygame.K_LEFT:
            self.hold_left = True
            self.horiz_timer = DAS_DELAY_MS
            self.try_move(-1, 0)
        elif key == pygame.K_RIGHT:
            self.hold_right = True
            self.horiz_timer = DAS_DELAY_MS
            self.try_move(1, 0)
        elif key in (pygame.K_DOWN, pygame.K_SPACE):
            self.hard_drop()
        elif key in (pygame.K_UP, pygame.K_x):
            self.try_rotate(1)
        elif key == pygame.K_z:
            self.try_rotate(-1)

    def handle_key_up(self, key):
        if key == pygame.K_LEFT:
            self.hold_left = False
        elif key == pygame.K_RIGHT:
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
                draw_block(surface, x, y, CELL, COLORS[kind])

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


def draw_sidebar(surface, game, fonts):
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

    help_panel = pygame.Rect(x, y, PANEL_W, 188)
    draw_panel(surface, help_panel)
    heading = fonts["section"].render("HOW TO PLAY", True, ACCENT)
    surface.blit(heading, (help_panel.x + 18, help_panel.y + 12))

    font = fonts["body"]
    left_key_w = max(font.size(key)[0] for (key, _), _ in CONTROLS)
    left_act_w = max(font.size(action)[0] for (_, action), _ in CONTROLS)
    right_key_w = max(font.size(key)[0] for _, (key, _) in CONTROLS)
    gap = 16
    column_gap = 28
    x0 = help_panel.x + 18
    x1 = x0 + left_key_w + gap
    x2 = x1 + left_act_w + column_gap
    x3 = x2 + right_key_w + gap
    row_y = help_panel.y + 42
    for (left_key, left_action), (right_key, right_action) in CONTROLS:
        surface.blit(font.render(left_key, True, ACCENT), (x0, row_y))
        surface.blit(font.render(left_action, True, TEXT), (x1, row_y))
        surface.blit(font.render(right_key, True, ACCENT), (x2, row_y))
        surface.blit(font.render(right_action, True, TEXT), (x3, row_y))
        row_y += 28


def draw_status(surface, game, fonts):
    if not game.paused and not game.game_over:
        return
    shade_layer = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
    shade_layer.fill((8, 10, 18, 188))
    surface.blit(shade_layer, (BOARD_X, BOARD_Y))

    if game.game_over:
        title, color = "GAME OVER", DANGER
        lines = (f"Score {game.score:,}", "Press R to restart")
    else:
        title, color = "PAUSED", ACCENT
        lines = ("Press P to resume",)

    center_x = BOARD_X + BOARD_W // 2
    center_y = BOARD_Y + BOARD_H // 2
    title_img = fonts["overlay"].render(title, True, color)
    surface.blit(title_img, title_img.get_rect(center=(center_x, center_y - 28)))
    for index, line in enumerate(lines):
        img = fonts["body"].render(line, True, TEXT)
        surface.blit(img, img.get_rect(center=(center_x, center_y + 18 + index * 28)))


def draw(surface, game, fonts):
    surface.fill(BG)
    draw_board(surface, game)
    draw_sidebar(surface, game, fonts)
    draw_status(surface, game, fonts)


def main():
    pygame.init()
    pygame.display.set_caption("Tetris")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = make_fonts()
    game = Game()

    running = True
    while running:
        # dt is the time since the last frame. Speed then does not depend
        # on how fast this computer happens to draw.
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    game.handle_key_down(event.key)
            elif event.type == pygame.KEYUP:
                game.handle_key_up(event.key)
            elif event.type == pygame.WINDOWFOCUSLOST:
                game.release_inputs()

        game.update(dt)
        draw(screen, game, fonts)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
