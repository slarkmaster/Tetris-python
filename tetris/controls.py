"""Key bindings, the settings overlay state, and key labels."""

import json
from pathlib import Path

import pygame

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
CONTROLS_PATH = Path(__file__).resolve().parent.parent / "controls.json"

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
