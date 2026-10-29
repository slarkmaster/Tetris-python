"""Session modes and the Pygame event loop."""

import pygame

from tetris.constants import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from tetris.controls import KeyBindings, KeyboardSettings
from tetris.game import Game
from tetris.ui import draw, make_fonts
from tetris.versus import Versus, handle_versus_key


class Session:
    """Which mode is showing, and the games behind it."""

    def __init__(self, bindings):
        self.bindings = bindings
        self.mode = "player"
        self.game = Game(bindings=bindings)
        self.versus = None

    def set_mode(self, mode):
        if mode not in ("player", "bot", "versus") or mode == self.mode:
            return
        self.game.release_inputs()
        self.game.bot.cancel()
        if mode == "versus":
            if self.versus is None:
                self.versus = Versus(self.bindings)
            else:
                self.versus.restart()
            self.versus.opponent.bot.step_ms = self.game.bot.step_ms
            self.mode = "versus"
            return
        if self.mode == "versus":
            self.game.restart()
        self.mode = mode
        self.game.mode = "bot" if mode == "bot" else "player"
        self.game.bot.cancel()
        self.game.bot.sync_status(self.game)

    def cycle_mode(self):
        order = ("player", "bot", "versus")
        self.set_mode(order[(order.index(self.mode) + 1) % len(order)])

    def controlled(self):
        """The board that receives the keyboard."""
        if self.mode == "versus":
            return self.versus.player
        return self.game


def main():
    pygame.init()
    pygame.display.set_caption("Tetris")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = make_fonts()
    bindings = KeyBindings()
    session = Session(bindings)
    settings = KeyboardSettings(bindings)

    running = True
    while running:
        # dt is the time since the last frame. Speed then does not depend
        # on how fast this computer happens to draw.
        dt = clock.tick(FPS)
        controlled = session.controlled()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                controlled.release_inputs()
            elif settings.open:
                settings.handle_event(event, controlled)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_k:
                    settings.toggle(controlled)
                elif event.key == pygame.K_b and session.bindings.action_for(event.key) is None:
                    session.cycle_mode()
                elif event.key == pygame.K_LEFTBRACKET and session.bindings.action_for(event.key) is None:
                    session.game.bot.slower()
                elif event.key == pygame.K_RIGHTBRACKET and session.bindings.action_for(event.key) is None:
                    session.game.bot.faster()
                elif session.mode == "versus":
                    handle_versus_key(session, event.key)
                else:
                    session.game.handle_key_down(event.key)
            elif event.type == pygame.KEYUP:
                controlled.handle_key_up(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                point = event.pos
                rect = settings.keyboard_rect
                bot = session.game.bot
                if rect is not None and rect.collidepoint(point):
                    settings.toggle(controlled)
                elif bot.player_rect is not None and bot.player_rect.collidepoint(point):
                    session.set_mode("player")
                elif bot.bot_rect is not None and bot.bot_rect.collidepoint(point):
                    session.set_mode("bot")
                elif bot.versus_rect is not None and bot.versus_rect.collidepoint(point):
                    session.set_mode("versus")
                elif bot.slower_rect is not None and bot.slower_rect.collidepoint(point):
                    session.game.bot.slower()
                elif bot.faster_rect is not None and bot.faster_rect.collidepoint(point):
                    session.game.bot.faster()

        if not settings.open:
            if session.mode == "versus":
                session.versus.opponent.bot.step_ms = session.game.bot.step_ms
                session.versus.update(dt)
            else:
                session.game.update(dt)
                if session.game.mode == "bot":
                    session.game.bot.update(session.game, dt)
        draw(screen, session, fonts, settings)
        pygame.display.flip()

    pygame.quit()

