# Tetris

A Pygame Tetris game with Player, Bot, and Player vs Bot modes.

## Setup

Python 3.12+ and a virtual environment are recommended. System Python often cannot install pygame (PEP 668).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python main.py
```

Or:

```bash
python -m tetris
```

Always use the venv interpreter (`.venv/bin/python`). Running with system `python3` will fail if pygame is not installed there.

## Modes

Cycle with **B**, or click **PLAYER** / **BOT** / **VS**.

| Mode | Who plays |
| --- | --- |
| Player | You control the falling piece |
| Bot | A heuristic bot plays automatically |
| Versus | You on the left board, the bot on the right |

In Versus, clearing **2, 3, or 4** lines sends that many garbage rows to the other board. A single line does not attack. Same-step attacks cancel. Incoming garbage slides across under the wells, then rises into the receiver’s stack. The falling piece on that board is discarded when garbage lands.

First player to top out loses.

## Controls

Defaults (change them with **K**):

| Action | Key |
| --- | --- |
| Move left | ← |
| Move right | → |
| Rotate | ↑ |
| Drop | ↓ |
| Rotate back | Z |
| Pause | P |
| Restart | R |
| Keyboard settings | K |
| Cycle mode | B |
| Bot slower / faster | `[` / `]` |
| Quit | Esc |

Tap left or right to move one cell. Hold to slide the rest of the way to that wall.

Esc and K cannot be rebound.

Custom bindings are saved in `controls.json` in this folder.

## Tests

```bash
source .venv/bin/activate
python -m unittest test_bot.py
```

## Project layout

| Path | Role |
| --- | --- |
| `main.py` | Launcher |
| `tetris/constants.py` | Board size, colors, speeds, attack table |
| `tetris/board.py` | Grid, pieces, seven-bag |
| `tetris/game.py` | Movement, locking, scoring, garbage |
| `tetris/bot.py` | Heuristic search and bot controller |
| `tetris/versus.py` | Two boards, attacks, garbage flights |
| `tetris/controls.py` | Key bindings and settings overlay |
| `tetris/ui.py` | Drawing |
| `tetris/app.py` | Modes and the Pygame loop |
| `test_bot.py` | Bot and versus tests |

Tunable values such as garbage travel time (`GARBAGE_FLIGHT_MS`) and piece colors live in `tetris/constants.py`.
