# taboun

taboun is a python chess bot built on top of `python-chess`.

## bots

| Bot | File | Idea | Notes |
| --- | --- | --- | --- |
| `tabounV1` | `src/bot/tabounv1.py` | Random legal move | |
| `tabounV2` | `src/bot/tabounv2.py` | Minimax + material evaluation | Configurable depth and optional move budget |
| `tabounV3` | `src/bot/tabounv3.py` | Minimax + simplified evaluation | Better positional sense than V2 |
| `tabounV4` | `src/bot/tabounv4.py` | Alpha-beta + simplified evaluation | Depth `3` |
| `tabounV5` | `src/bot/tabounv5.py` | Alpha-beta + simplified evaluation + move ordering | Captures then checks then quiet moves |
| `tabounV6` | `src/bot/tabounv6.py` | Alpha-beta + simplified evaluation + quiescence | Extends capture sequences |
| `tabounV7` | `src/bot/tabounv7.py` | Alpha-beta + simplified evaluation + quiescence + TT | Uses a transposition table |
| `tabounV8` | `src/bot/tabounv8.py` | V7 + advanced move ordering + iterative deepening | Orders captures, promotions, checks, and previous best move |
| `tabounV9` | `src/bot/tabounv9.py` | V8 + improved positional evaluation | Mobility, bishop pair, pawn structure, king safety, development |
| `tabounV10` | `src/bot/tabounv10.py` | V9 + time management + limited quiescence | Stops by time limit, keeps last completed depth |
| `tabounV11` | `src/bot/tabounv11.py` | V10 + Komodo Polyglot opening book | Book can be disabled with `use_book=False` |
| `tabounV12` | `src/bot/tabounv12.py` | V11 + distance-to-mate scoring, TT with best move, cheap ordering | Book can be disabled with `use_book=False` |

## Evaluation

| Function | File | Used by | Scores terminal positions |
| --- | --- | --- | --- |
| `evaluate_material` | `src/evaluation/material.py` | V2 | yes |
| `evaluate_simplified` | `src/evaluation/simplified_evaluation_function.py` | V3–V8 | yes |
| `evaluate_improved` | `src/evaluation/improved_evaluation_function.py` | V9–V11 | yes |
| `evaluate_fast` | `src/evaluation/fast_evaluation_function.py` | V12 | no, the search does |

The first three return a flat `MATE_SCORE` that does not depend on how far away
the mate is, so every mating line looks equally good and the bot can shuffle
instead of mating: `tabounV10` draws KQ vs K against a random opponent. An
evaluation cannot fix this, because it does not know the search ply.
`evaluate_fast` therefore scores only live positions, and `tabounV12` scores
mates in the search as `MATE_VALUE - ply`.

`evaluate_simplified` and `evaluate_improved` were made faster (13x and 3.3x)
without changing a single score, so V3–V11 still play exactly the same moves.

## Opening book

`tabounV11` uses a Polyglot opening book from Komodo:

```text
data/openings/books/komodo3.bin
```

At each move, `tabounV11` first asks the Komodo book for a weighted book move. If the current position is not in the book, it uses the normal `tabounV10` search.

## Move time limits

`tabounV2` through `tabounV9` accept an optional `time_limit` in seconds:

```python
bot = tabounV7(time_limit=2.0)
```

The default is `None`, which preserves the historical fixed-depth behavior.
With a limit, the bot uses iterative deepening up to its historical maximum
depth and returns the best move from the last completed depth. `tabounV10`
through `tabounV12` keep their historical one-second default.

The opening books in V11 and V12 can be disabled for fair tournaments:

```python
bot = tabounV12(use_book=False)
```

## UCI

Every bot can run as a UCI engine for tournament managers and chess GUIs:

```bash
python3 src/uci.py tabounv12
python3 src/uci.py tabounv12 --no-book
```

The adapter understands game clocks (`wtime`, `btime`, increments and
`movestogo`), fixed `movetime`, `depth`, `stop`, FEN positions and move
histories. It exposes the standard `OwnBook` option for V11 and V12.

Because the historical bot API returns only a move, UCI `info score` is a
documented **static evaluation after that move**, using the evaluation family
of the selected bot. It exists for protocol tooling and must not be used for
score-based game adjudication.

## Requirements

- `python-chess`

Install dependencies :

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
pip install python-chess
```

## cli

```bash
python src/main.py
```

You will be prompted for:

- **Start position**: new game or load from **FEN** or **PGN**
- **Mode**: `human vs bot` or `bot vs bot`
- **Bot**: pick from the available bots
- **Color** (human vs bot) : play White or Black

During the game:

- Type moves in **SAN** (e.g. `e4`, `Nf3`, `O-O`) or **UCI** (e.g. `e2e4`, `g1f3`, `e7e8q`)
- Type `abandon` to resign
- The move list is printed in a chess-like format: `1. e4 e5 2. d4 d5 ...`
- The position is printed after every move

At the end:

- The result is printed with the winning bot name + color
- You can save the game as a **PGN** file

## Professional arena

Generate the deterministic 25-opening suite:

```bash
python3 -m src.arena.build_openings
```

Run a 10-opening pilot with fastchess (20 mirrored games per pairing):

```bash
python3 -m src.arena.run_tournament --fastchess /path/to/fastchess
```

Run the official 25-opening tournament (50 games per pairing):

```bash
python3 -m src.arena.run_tournament --fastchess /path/to/fastchess --official
```

Use `--run-id ID --resume` to resume an autosaved run. Each run lives below
`data/arena/runs/ID` with its PGN, logs, fastchess state and a manifest that
records the code revision, tool versions, hardware and complete command.
Opening books are disabled for V11 and V12. The initial official time control
is 60 seconds plus 0.6 seconds per move, with four concurrent games.

## Legacy Python arena

The original in-process arena remains temporarily available for historical
comparison. Its repeated start positions, unequal thinking time and sequential
rating updates mean that it must not be used for published rankings.

Run a round-robin between all bots and export CSV files:

```bash
python -m src.arena.runner
```

Run the arena in parallel:

```bash
python -m src.arena.runner --parallel --workers 4
```

Resume an interrupted arena without replaying completed pairings:

```bash
python -m src.arena.runner --resume --parallel --workers 4
```

Run the arena only for selected bots:

```bash
python -m src.arena.runner --bots tabounv8,tabounv9,tabounv10 --parallel --workers 4 --games-per-pair 4
```

Useful options:

- `--games-per-pair 20`: number of games for each bot pairing
- `--bots tabounv8,tabounv9,tabounv10`: only run the arena for these bots
- `--parallel`: run different pairings at the same time
- `--workers 4`: number of parallel worker processes
- `--resume`: read the existing results CSV, skip completed pairings, complete partial pairings, then rebuild ranking and matrix

Outputs:

- `src/arena/results.csv` (pair results)
- `src/arena/ranking.csv` (overall ranking + Elo)
- `src/arena/matrix.csv` (matrix view per pairing)

## Arena ranking

> **This ranking is not usable yet.** The bots are deterministic and the arena
> starts every game from the initial position with no randomization, so
> `--games-per-pair 20` replays the same two games ten times each rather than
> playing twenty. The table below rests on six distinct games per bot, not 120.
> Fixing this means varied opening positions played with both colors, one time
> control for all bots, and an Elo anchored on an external engine.

Current ranking was generated before `tabounV8`, `tabounV9`, and `tabounV10` were added.

| Bot | Points | Wins | Draws | Losses | Games |
| --- | --- | --- | --- | --- | --- |
| tabounv6 | 110.0 | 110 | 0 | 10 | 120 |
| tabounv7 | 109.5 | 109 | 1 | 10 | 120 |
| tabounv5 | 59.5 | 49 | 21 | 50 | 120 |
| tabounv4 | 58.5 | 47 | 23 | 50 | 120 |
| tabounv3 | 50.0 | 40 | 20 | 60 | 120 |
| tabounv2 | 28.0 | 16 | 24 | 80 | 120 |
| tabounv1 | 4.5 | 0 | 9 | 111 | 120 |
