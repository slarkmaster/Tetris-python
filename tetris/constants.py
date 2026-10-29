"""Window, board, timing, colors, and piece shapes."""

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

# A tap moves one square. Holding Left or Right past this sends the piece
# the rest of the way to that side.
HOLD_TO_WALL_MS = 350
# After the piece lands it can still slide or rotate for this long, then it
# sticks. Down and Space skip the wait and place the piece immediately.
LOCK_DELAY_MS = 500

HARD_DROP_SCORE = 2
# One, two, three, and four lines. Multiplied by the current level.
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
# Garbage sent to the other board in Versus. A single does not attack.
# Two, three, and four lines send that many rows.
ATTACK_LINES = {1: 0, 2: 2, 3: 3, 4: 4}
# How long one garbage row takes to slide up into the well.
GARBAGE_RISE_MS = 200
# How long a garbage packet takes to fly from one Versus board to the other.
GARBAGE_FLIGHT_MS = 1500
# Mini-cells for the traveling packet, drawn just under the Versus wells.
GARBAGE_FLIGHT_CELL = 16
GARBAGE_FLIGHT_GAP = 8

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
# Versus garbage rows use that same pink.
DROPPED = (255, 122, 184)
GARBAGE = DROPPED

# Versus draws two boards in the same window, so the cells are smaller.
VS_CELL = 22
VS_BOARD_W = COLS * VS_CELL
VS_BOARD_H = ROWS * VS_CELL
VS_LEFT_X = 16
VS_TOP = 52
VS_RIGHT_X = WINDOW_WIDTH - 16 - VS_BOARD_W
VS_CENTER_X = VS_LEFT_X + VS_BOARD_W + 12
VS_CENTER_W = VS_RIGHT_X - 12 - VS_CENTER_X

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
