"""All drawing: boards, sidebars, versus layout, and overlays."""

import pygame

from tetris.constants import (
    ACCENT,
    BG,
    BOARD_BG,
    BOARD_H,
    BOARD_W,
    BOARD_X,
    BOARD_Y,
    CELL,
    COLORS,
    COLS,
    DANGER,
    DROPPED,
    EMPTY,
    GARBAGE,
    GARBAGE_FLIGHT_CELL,
    GARBAGE_FLIGHT_GAP,
    LINES_PER_LEVEL,
    MUTED,
    PANEL,
    PANEL_EDGE,
    PANEL_W,
    ROWS,
    SHAPES,
    SIDE_X,
    TEXT,
    VS_BOARD_H,
    VS_BOARD_W,
    VS_CELL,
    VS_CENTER_W,
    VS_CENTER_X,
    VS_LEFT_X,
    VS_RIGHT_X,
    VS_TOP,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from tetris.controls import ACTIONS, control_rows


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


def cell_origin(column, row, origin_x=BOARD_X, origin_y=BOARD_Y, cell=CELL):
    return origin_x + column * cell, origin_y + row * cell


def draw_panel(surface, rect):
    pygame.draw.rect(surface, (8, 9, 14), rect.move(0, 4), border_radius=14)
    pygame.draw.rect(surface, PANEL, rect, border_radius=14)
    pygame.draw.rect(surface, PANEL_EDGE, rect, width=2, border_radius=14)


def draw_block(surface, x, y, size, color):
    rect = pygame.Rect(x + 1, y + 1, size - 2, size - 2)
    pygame.draw.rect(surface, color, rect, border_radius=4)
    shine = pygame.Rect(rect.x + 3, rect.y + 3, rect.w - 6, max(2, rect.h // 7))
    pygame.draw.rect(surface, shade(color, 85), shine, border_radius=2)


def draw_cells(surface, cells, color, origin_x=BOARD_X, origin_y=BOARD_Y, cell=CELL, pixel_dy=0):
    for column, row in cells:
        if 0 <= column < COLS and 0 <= row < ROWS:
            x, y = cell_origin(column, row, origin_x, origin_y, cell)
            draw_block(surface, x, y + pixel_dy, cell, color)


def draw_board(surface, game, origin_x=BOARD_X, origin_y=BOARD_Y, cell=CELL):
    board_w = COLS * cell
    board_h = ROWS * cell
    outer = pygame.Rect(origin_x - 8, origin_y - 8, board_w + 16, board_h + 16)
    draw_panel(surface, outer)
    pygame.draw.rect(surface, BOARD_BG, (origin_x, origin_y, board_w, board_h))

    for row in range(ROWS):
        for column in range(COLS):
            x, y = cell_origin(column, row, origin_x, origin_y, cell)
            pygame.draw.rect(surface, EMPTY, (x + 1, y + 1, cell - 2, cell - 2), border_radius=3)

    # During a garbage rise the well stays put and the stack slides up into it,
    # so the new rows enter from below the bottom edge.
    rise = game.garbage_rise_pixels(cell)
    piece_rise = game.piece_rise_pixels(cell)
    board_rect = pygame.Rect(origin_x, origin_y, board_w, board_h)
    previous_clip = surface.get_clip()
    surface.set_clip(board_rect)
    for row in range(ROWS):
        for column in range(COLS):
            kind = game.board[row][column]
            if kind is not None:
                x, y = cell_origin(column, row, origin_x, origin_y, cell)
                color = GARBAGE if kind == "G" else DROPPED
                draw_block(surface, x, y + rise, cell, color)

    piece = game.piece
    if piece is not None:
        draw_cells(surface, piece.cells(), COLORS[piece.kind], origin_x, origin_y, cell, piece_rise)
    surface.set_clip(previous_clip)


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
    y += tag.get_height() + 10
    y = draw_mode_bar(surface, game, fonts, y, mode=game.mode)

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

    nxt = pygame.Rect(x, y, PANEL_W, 116)
    draw_panel(surface, nxt)
    next_label = fonts["section"].render("NEXT", True, MUTED)
    surface.blit(next_label, (nxt.x + 18, nxt.y + 12))
    preview = pygame.Rect(nxt.x + 18, nxt.y + 36, nxt.w - 36, nxt.h - 48)
    draw_shape_preview(surface, game.coming_next(), preview)
    y = nxt.bottom + 14

    help_panel = pygame.Rect(x, y, PANEL_W, 176)
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


def draw_mode_bar(surface, game, fonts, y, x=SIDE_X, width=PANEL_W, mode="player", status_game=None):
    """Player / Bot / Versus switch, bot status, and the bot's step delay."""
    panel = pygame.Rect(x, y, width, 74)
    draw_panel(surface, panel)
    mode_label = fonts["section"].render("MODE", True, MUTED)
    surface.blit(mode_label, (panel.x + 18, panel.y + 10))
    shown = game if status_game is None else status_game
    status = fonts["small"].render(f"Bot {shown.bot.display_status(shown)}", True, TEXT)
    surface.blit(status, status.get_rect(right=panel.right - 18, centery=panel.y + 18))

    def pill(text, selected, left):
        image = fonts["section"].render(text, True, BG if selected else ACCENT)
        rect = image.get_rect(topleft=(left, panel.y + 38))
        background = rect.inflate(20, 10)
        pygame.draw.rect(surface, ACCENT if selected else (36, 44, 68), background, border_radius=8)
        surface.blit(image, image.get_rect(center=background.center))
        return background

    game.bot.player_rect = pill("PLAYER", mode == "player", panel.x + 18)
    game.bot.bot_rect = pill("BOT", mode == "bot", game.bot.player_rect.right + 18)
    game.bot.versus_rect = pill("VS", mode == "versus", game.bot.bot_rect.right + 18)

    faster = fonts["section"].render("+", True, ACCENT)
    faster_rect = faster.get_rect(topright=(panel.right - 24, panel.y + 40))
    faster_bg = faster_rect.inflate(16, 8)
    pygame.draw.rect(surface, (36, 44, 68), faster_bg, border_radius=8)
    surface.blit(faster, faster.get_rect(center=faster_bg.center))
    game.bot.faster_rect = faster_bg

    slower = fonts["section"].render("-", True, ACCENT)
    slower_rect = slower.get_rect(topright=(faster_bg.left - 8, panel.y + 40))
    slower_bg = slower_rect.inflate(16, 8)
    pygame.draw.rect(surface, (36, 44, 68), slower_bg, border_radius=8)
    surface.blit(slower, slower.get_rect(center=slower_bg.center))
    game.bot.slower_rect = slower_bg

    speed = fonts["small"].render(f"{game.bot.step_ms} ms", True, MUTED)
    surface.blit(speed, speed.get_rect(midright=(slower_bg.left - 8, slower_bg.centery)))
    return panel.bottom + 12


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


def draw_board_message(surface, origin_x, origin_y, cell, fonts, title, color, lines):
    width = COLS * cell
    height = ROWS * cell
    shade_layer = pygame.Surface((width, height), pygame.SRCALPHA)
    shade_layer.fill((8, 10, 18, 188))
    surface.blit(shade_layer, (origin_x, origin_y))
    center_x = origin_x + width // 2
    center_y = origin_y + height // 2
    title_img = fonts["overlay"].render(title, True, color)
    surface.blit(title_img, title_img.get_rect(center=(center_x, center_y - 28)))
    for index, line in enumerate(lines):
        img = fonts["small"].render(line, True, TEXT)
        surface.blit(img, img.get_rect(center=(center_x, center_y + 16 + index * 24)))


def garbage_flight_y():
    """Top of the traveling packet, a few pixels under both wells."""
    return VS_TOP + VS_BOARD_H + GARBAGE_FLIGHT_GAP


def garbage_flight_ends(from_left):
    """Centers of the two wells, on the strip directly under both boards."""
    y = garbage_flight_y()
    left = (VS_LEFT_X + VS_BOARD_W // 2, y)
    right = (VS_RIGHT_X + VS_BOARD_W // 2, y)
    return (left, right) if from_left else (right, left)


def draw_garbage_flights(surface, versus):
    """Draw a stack of garbage rows sliding from one board to the other."""
    size = GARBAGE_FLIGHT_CELL
    blocks = 8
    gap = 3
    packet_w = blocks * size
    for flight in versus.flights:
        t = flight.progress()
        start, end = garbage_flight_ends(flight.from_left)
        x = start[0] + (end[0] - start[0]) * t - packet_w / 2
        y = start[1]
        for row in range(flight.count):
            for column in range(blocks):
                if column == gap:
                    continue
                draw_block(
                    surface,
                    round(x) + column * size,
                    y + row * size,
                    size,
                    GARBAGE,
                )


def draw_versus(surface, session, fonts, settings):
    """Two boards with the mode controls between them."""
    versus = session.versus
    settings.keyboard_rect = None
    surface.fill(BG)
    you = fonts["section"].render(f"YOU  {versus.player.score:,}", True, TEXT)
    bot = fonts["section"].render(f"BOT  {versus.opponent.score:,}", True, TEXT)
    surface.blit(you, you.get_rect(center=(VS_LEFT_X + VS_BOARD_W // 2, 28)))
    surface.blit(bot, bot.get_rect(center=(VS_RIGHT_X + VS_BOARD_W // 2, 28)))
    draw_board(surface, versus.player, VS_LEFT_X, VS_TOP, VS_CELL)
    draw_board(surface, versus.opponent, VS_RIGHT_X, VS_TOP, VS_CELL)

    x = VS_CENTER_X
    y = 28
    title = fonts["value"].render("VERSUS", True, TEXT)
    surface.blit(title, (x, y))
    y += title.get_height() + 8
    rule = fonts["small"].render("2, 3, or 4 lines send that many garbage rows.", True, MUTED)
    surface.blit(rule, (x, y))
    y += rule.get_height() + 12
    y = draw_mode_bar(
        surface,
        session.game,
        fonts,
        y,
        x=x,
        width=VS_CENTER_W,
        mode="versus",
        status_game=versus.opponent,
    )

    scores = pygame.Rect(x, y, VS_CENTER_W, 88)
    draw_panel(surface, scores)
    for index, (label, game) in enumerate((("YOU", versus.player), ("BOT", versus.opponent))):
        column = scores.x + 16 + index * (scores.w // 2)
        name = fonts["label"].render(label, True, MUTED)
        value = fonts["value"].render(str(game.lines), True, TEXT)
        caption = fonts["small"].render("lines", True, MUTED)
        surface.blit(name, (column, scores.y + 12))
        surface.blit(value, (column, scores.y + 32))
        surface.blit(caption, (column, scores.y + 64))
    y = scores.bottom + 12

    for label, game in (("YOUR NEXT", versus.player), ("BOT NEXT", versus.opponent)):
        card = pygame.Rect(x, y, VS_CENTER_W, 92)
        draw_panel(surface, card)
        heading = fonts["section"].render(label, True, MUTED)
        surface.blit(heading, (card.x + 14, card.y + 8))
        preview = pygame.Rect(card.x + 14, card.y + 28, card.w - 28, card.h - 36)
        draw_shape_preview(surface, game.coming_next(), preview)
        y = card.bottom + 12

    draw_garbage_flights(surface, versus)
    hint = fonts["small"].render("B cycles mode.  P pauses.  R restarts.", True, MUTED)
    hint_y = garbage_flight_y() + 4 * GARBAGE_FLIGHT_CELL + 10
    surface.blit(hint, (x, max(y, hint_y)))

    winner = versus.winner()
    restart = session.bindings.label("restart")
    if winner == "player":
        draw_board_message(surface, VS_RIGHT_X, VS_TOP, VS_CELL, fonts, "GAME OVER", DANGER, ())
        draw_board_message(
            surface, VS_LEFT_X, VS_TOP, VS_CELL, fonts, "YOU WIN", ACCENT, (f"Press {restart} to play again",)
        )
    elif winner == "bot":
        draw_board_message(surface, VS_LEFT_X, VS_TOP, VS_CELL, fonts, "GAME OVER", DANGER, ())
        draw_board_message(
            surface, VS_RIGHT_X, VS_TOP, VS_CELL, fonts, "BOT WINS", DANGER, (f"Press {restart} to play again",)
        )
    elif winner == "draw":
        for origin in (VS_LEFT_X, VS_RIGHT_X):
            draw_board_message(
                surface, origin, VS_TOP, VS_CELL, fonts, "DRAW", ACCENT, (f"Press {restart} to play again",)
            )
    elif versus.player.paused:
        resume = session.bindings.label("pause")
        for origin in (VS_LEFT_X, VS_RIGHT_X):
            draw_board_message(
                surface, origin, VS_TOP, VS_CELL, fonts, "PAUSED", ACCENT, (f"Press {resume} to resume",)
            )
    if settings.open:
        draw_keyboard_settings(surface, fonts, settings)


def draw(surface, session, fonts, settings):
    if session.mode == "versus":
        draw_versus(surface, session, fonts, settings)
        return
    game = session.game
    surface.fill(BG)
    draw_board(surface, game)
    draw_sidebar(surface, game, fonts, settings)
    draw_status(surface, game, fonts)
    if settings.open:
        draw_keyboard_settings(surface, fonts, settings)
