"""Heuristic search and the controller that plays planned moves."""

from collections import deque

from tetris.board import cells_fit, clear_lines, shape_cells
from tetris.constants import COLS, KICKS, ROWS

# Tunable scores for Bot Mode. Positive weights reward, negative weights penalize.
# Lines are worth more than one buried hole, and a stack near the ceiling is costly.
BOT_WEIGHTS = {
    "lines": 100.0,
    "holes": -55.0,
    "aggregate_height": -1.5,
    "bumpiness": -3.5,
    "danger": -4.0,
}

BOT_STEP_MIN_MS = 30
BOT_STEP_MAX_MS = 200
BOT_STEP_MS = 80


def column_heights(board):
    """How far each column reaches up from the floor. Empty columns are 0."""
    heights = []
    for x in range(COLS):
        height = 0
        for y in range(ROWS):
            if board[y][x] is not None:
                height = ROWS - y
                break
        heights.append(height)
    return heights


def count_holes(board, heights):
    """Empty cells with at least one filled cell above them."""
    holes = 0
    for x, height in enumerate(heights):
        if height == 0:
            continue
        top = ROWS - height
        for y in range(top + 1, ROWS):
            if board[y][x] is None:
                holes += 1
    return holes


def evaluate_board(board, lines_cleared, weights):
    """Score a simulated board. Higher is better. The live board is not used."""
    heights = column_heights(board)
    holes = count_holes(board, heights)
    aggregate = sum(heights)
    bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
    peak = max(heights) if heights else 0
    # Extra cost once the stack enters the top four rows, where a spawn can die.
    danger = peak
    if peak >= ROWS - 4:
        danger += (peak - (ROWS - 5)) * 8
    return (
        weights["lines"] * lines_cleared
        + weights["holes"] * holes
        + weights["aggregate_height"] * aggregate
        + weights["bumpiness"] * bumpiness
        + weights["danger"] * danger
    )


def pose_neighbors(board, kind, rotation, x, y):
    """Legal left, right, and rotation steps from this pose, using the game's kicks."""
    steps = []
    for dx, name in ((-1, "left"), (1, "right")):
        if cells_fit(board, shape_cells(kind, rotation, x + dx, y)):
            steps.append((name, (rotation, x + dx, y)))
    for direction, name in ((1, "cw"), (-1, "ccw")):
        new_rotation = (rotation + direction) % 4
        for kick_x, kick_y in KICKS:
            next_x = x + kick_x
            next_y = y + kick_y
            if cells_fit(board, shape_cells(kind, new_rotation, next_x, next_y)):
                steps.append((name, (new_rotation, next_x, next_y)))
                break
    return steps


def drop_y(board, kind, rotation, x, y):
    """Lowest row this pose can fall to. None when the pose itself does not fit."""
    if not cells_fit(board, shape_cells(kind, rotation, x, y)):
        return None
    while cells_fit(board, shape_cells(kind, rotation, x, y + 1)):
        y += 1
    return y


def simulate_placement(board, kind, cells):
    """Copy the board, lock these cells, and clear lines. The original board stays put."""
    simulated = [row[:] for row in board]
    for x, y in cells:
        simulated[y][x] = kind
    return clear_lines(simulated)


def choose_move(board, piece, weights=None):
    """Pick a legal path of left, right, rotate, and a final drop for this piece.

    Search only poses reachable by the same moves Player Mode uses, then hard-drop
    each one on a copy of the board. The returned path is empty when nothing fits.
    """
    weights = BOT_WEIGHTS if weights is None else weights
    start = (piece.rotation, piece.x, piece.y)
    if not cells_fit(board, shape_cells(piece.kind, *start)):
        return None

    best = None
    seen = {start}
    queue = deque([(start, [])])
    while queue:
        (rotation, x, y), path = queue.popleft()
        landing = drop_y(board, piece.kind, rotation, x, y)
        if landing is not None:
            cells = shape_cells(piece.kind, rotation, x, landing)
            simulated, cleared = simulate_placement(board, piece.kind, cells)
            score = evaluate_board(simulated, cleared, weights)
            # Equal scores prefer the shorter path, then the lower landing.
            rank = (score, -len(path), landing)
            if best is None or rank > best[0]:
                best = (rank, path + ["drop"])
        for name, pose in pose_neighbors(board, piece.kind, rotation, x, y):
            if pose in seen:
                continue
            seen.add(pose)
            queue.append((pose, path + [name]))
    if best is None:
        return None
    return best[1]


class BotController:
    """Runs a planned path one step at a time through the normal game rules.

    A new piece gets one plan. Pause, reset, game over, and leaving Bot Mode
    throw that plan away so a later tick cannot move the wrong piece.
    """

    def __init__(self, weights=None, step_ms=BOT_STEP_MS):
        self.weights = BOT_WEIGHTS if weights is None else weights
        self.step_ms = step_ms
        self.status = "idle"
        self.actions = []
        self.piece_id = None
        self.timer = 0
        self.waiting = False
        self.replans = 0
        self.gave_up_id = None
        self.tracked_id = None
        self.player_rect = None
        self.bot_rect = None
        self.slower_rect = None
        self.faster_rect = None
        self.versus_rect = None

    def cancel(self):
        """Forget any move that has not been played yet."""
        self.actions = []
        self.piece_id = None
        self.tracked_id = None
        self.timer = 0
        self.waiting = False
        self.replans = 0
        self.gave_up_id = None
        if self.status not in ("paused", "game over"):
            self.status = "idle"

    def sync_status(self, game):
        if game.game_over:
            self.status = "game over"
        elif game.paused and game.mode == "bot":
            self.status = "paused"
        elif game.mode != "bot":
            self.status = "idle"

    def display_status(self, game):
        if game.game_over:
            return "Game over"
        if game.paused and game.mode == "bot":
            return "Paused"
        if game.mode != "bot":
            return "Idle"
        return {
            "idle": "Idle",
            "thinking": "Thinking",
            "moving": "Moving",
            "dropping": "Dropping",
            "paused": "Paused",
            "game over": "Game over",
        }.get(self.status, "Idle")

    def slower(self):
        self.step_ms = min(BOT_STEP_MAX_MS, self.step_ms + 20)

    def faster(self):
        self.step_ms = max(BOT_STEP_MIN_MS, self.step_ms - 20)

    def update(self, game, dt):
        """Advance the bot by dt milliseconds. Does nothing unless Bot Mode is active."""
        if game.mode != "bot":
            return
        if game.game_over:
            self.cancel()
            self.status = "game over"
            return
        if game.paused:
            self.cancel()
            self.status = "paused"
            return
        piece = game.piece
        if piece is None:
            self.status = "idle"
            return
        piece_id = id(piece)
        if self.gave_up_id == piece_id:
            self.status = "idle"
            return
        if self.tracked_id != piece_id:
            # New piece. Wait one step so this plan cannot belong to the previous one.
            self.tracked_id = piece_id
            self.timer = 0
            self.waiting = True
            self.replans = 0
            self.actions = []
            self.status = "thinking"
            return

        self.timer += dt
        if self.timer < self.step_ms:
            self.status = "thinking" if self.waiting else self.status
            return
        self.timer -= self.step_ms
        self.waiting = False
        # Search again at the moment of the move so gravity cannot leave a stale path.
        path = choose_move(game.board, piece, self.weights)
        if not path:
            self.gave_up_id = piece_id
            self.actions = []
            self.status = "idle"
            return
        action = path[0]
        self.actions = [action]
        self.status = "dropping" if action == "drop" else "moving"
        applied = self._apply(game, action)
        if game.game_over:
            self.cancel()
            self.status = "game over"
            return
        if game.piece is None or id(game.piece) != piece_id:
            self.actions = []
            self.tracked_id = None
            self.timer = 0
            self.waiting = False
            self.status = "idle"
            return
        if not applied:
            self.replans += 1
            self.actions = []
            if self.replans > 3:
                self.gave_up_id = piece_id
                self.status = "idle"
            return
        self.replans = 0

    def _apply(self, game, action):
        """Play one planned step with the same functions the keyboard uses."""
        if game.game_over or game.paused or game.piece is None:
            return False
        if action == "left":
            return game.try_move(-1, 0)
        if action == "right":
            return game.try_move(1, 0)
        if action == "cw":
            return game.try_rotate(1)
        if action == "ccw":
            return game.try_rotate(-1)
        if action == "drop":
            game.hard_drop()
            return True
        return False
