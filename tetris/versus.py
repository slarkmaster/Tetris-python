"""Player vs bot: shared bags, attack exchange, and garbage flights."""

import random

from tetris.board import BagView, SharedQueue
from tetris.constants import GARBAGE_FLIGHT_MS
from tetris.game import Game


def net_attack(left, right):
    """Positive when left sends leftover garbage at right. Same-step attacks cancel."""
    return left.take_attack() - right.take_attack()


def exchange_attacks(left, right):
    """Trade pending garbage immediately. Tests use this; Versus flies it first."""
    net = net_attack(left, right)
    if net > 0:
        right.add_garbage(net)
    elif net < 0:
        left.add_garbage(-net)


class GarbageFlight:
    """One packet of garbage rows traveling along the bottom to the other board."""

    def __init__(self, count, from_left):
        self.count = count
        self.from_left = from_left
        self.elapsed = 0
        self.delivered = False

    def arrived(self):
        return self.elapsed >= GARBAGE_FLIGHT_MS

    def progress(self):
        t = max(0.0, min(1.0, self.elapsed / GARBAGE_FLIGHT_MS))
        # Mild ease-in-out so the packet glides instead of darting through the middle.
        return t * t * (3 - 2 * t)


class Versus:
    """Player and bot boards that attack each other with garbage lines."""

    def __init__(self, bindings, rng=None):
        self.rng = rng or random.Random()
        self.bindings = bindings
        self.player = Game(rng=random.Random(), bindings=bindings)
        self.opponent = Game(rng=random.Random(), bindings=bindings)
        self.restart()

    def restart(self):
        """Start both boards from the same piece sequence."""
        shared = SharedQueue(random.Random(self.rng.randrange(1 << 30)))
        self.player.shared_view = BagView(shared)
        self.opponent.shared_view = BagView(shared)
        self.player.restart()
        self.opponent.restart()
        self.player.mode = "player"
        self.opponent.mode = "bot"
        self.player.outgoing_attack = 0
        self.opponent.outgoing_attack = 0
        self.flights = []

    def winner(self):
        """'player', 'bot', 'draw', or None while both boards are still alive."""
        player_over = self.player.game_over
        bot_over = self.opponent.game_over
        if player_over and bot_over:
            return "draw"
        if bot_over:
            return "player"
        if player_over:
            return "bot"
        return None

    def toggle_pause(self):
        if self.winner():
            return
        paused = not self.player.paused
        self.player.paused = paused
        self.opponent.paused = paused
        self.player.release_inputs()
        if paused:
            self.opponent.bot.cancel()
            self.opponent.bot.status = "paused"

    def update(self, dt):
        if self.winner():
            self.flights = []
            if not self.player.paused:
                self.player.tick_garbage_rise(dt)
                self.opponent.tick_garbage_rise(dt)
            return
        self.player.update(dt)
        self.opponent.update(dt)
        self.opponent.bot.update(self.opponent, dt)
        net = net_attack(self.player, self.opponent)
        if net > 0:
            self.flights.append(GarbageFlight(net, True))
        elif net < 0:
            self.flights.append(GarbageFlight(-net, False))
        if self.player.paused:
            return
        remaining = []
        for flight in self.flights:
            flight.elapsed += dt
            if flight.arrived() and not flight.delivered:
                target = self.opponent if flight.from_left else self.player
                target.add_garbage(flight.count)
                flight.delivered = True
            if not flight.delivered:
                remaining.append(flight)
        self.flights = remaining


def handle_versus_key(session, key):
    """Pause and restart apply to both boards. Other keys move only the player."""
    versus = session.versus
    action = session.bindings.action_for(key)
    if action == "restart":
        versus.restart()
        versus.opponent.bot.step_ms = session.game.bot.step_ms
        return
    if action == "pause":
        versus.toggle_pause()
        return
    versus.player.handle_key_down(key)
