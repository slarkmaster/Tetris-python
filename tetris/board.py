"""Board grid helpers, falling pieces, and the seven-bag randomizer."""

from tetris.constants import COLS, FALL_SPEED_FACTOR, FALL_START_MS, MIN_FALL_MS, ROWS, SHAPES, SPAWN_X, SPAWN_Y


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


def shape_cells(kind, rotation, x, y):
    """Board squares for a piece pose. Does not touch the live game."""
    return [(x + cx, y + cy) for cx, cy in SHAPES[kind][rotation]]


def shuffled_bag(rng):
    """All seven kinds in a random order."""
    kinds = list(SHAPES)
    rng.shuffle(kinds)
    return kinds


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
        return shape_cells(self.kind, rotation, x, y)


class SevenBag:
    """Deals all seven pieces in a random order, then shuffles them again.

    A plain random pick can go a long time without one piece. A bag cannot:
    each group of seven contains every piece once.
    """

    def __init__(self, rng):
        self.rng = rng
        self.queue = []

    def _refill(self):
        self.queue.extend(shuffled_bag(self.rng))

    def pop(self):
        if not self.queue:
            self._refill()
        return self.queue.pop(0)

    def peek(self):
        if not self.queue:
            self._refill()
        return self.queue[0]


class SharedQueue:
    """One shuffled piece order that two Versus boards can draw from."""

    def __init__(self, rng):
        self.rng = rng
        self.queue = []

    def ensure(self, index):
        while len(self.queue) <= index:
            self.queue.extend(shuffled_bag(self.rng))


class BagView:
    """A player's cursor into a SharedQueue. pop and peek match SevenBag."""

    def __init__(self, shared):
        self.shared = shared
        self.index = 0

    def pop(self):
        self.shared.ensure(self.index)
        kind = self.shared.queue[self.index]
        self.index += 1
        return kind

    def peek(self):
        self.shared.ensure(self.index)
        return self.shared.queue[self.index]
