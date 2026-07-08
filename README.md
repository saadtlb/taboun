# taboun

taboun is a python chess bot built on top of `python-chess`.

## bots

| Bot | File | Idea | Notes |
| --- | --- | --- | --- |
| `tabounV1` | `src/bot/tabounv1.py` | Random legal move | |
| `tabounV2` | `src/bot/tabounv2.py` | Minimax + material evaluation | Configurable depth (default `2`) |
| `tabounV3` | `src/bot/tabounv3.py` | Minimax + simplified evaluation | Better positional sense than V2 |
| `tabounV4` | `src/bot/tabounv4.py` | Alpha-beta + simplified evaluation | Depth `3` |
| `tabounV5` | `src/bot/tabounv5.py` | Alpha-beta + simplified evaluation + move ordering | Captures then checks then quiet moves |
| `tabounV6` | `src/bot/tabounv6.py` | Alpha-beta + simplified evaluation + quiescence | Extends capture sequences |
| `tabounV7` | `src/bot/tabounv7.py` | Alpha-beta + simplified evaluation + quiescence + TT | Uses a transposition table |
| `tabounV8` | `src/bot/tabounv8.py` | V7 + advanced move ordering + iterative deepening | Orders captures, promotions, checks, and previous best move |
| `tabounV9` | `src/bot/tabounv9.py` | V8 + improved positional evaluation | Mobility, bishop pair, pawn structure, king safety, development |
| `tabounV10` | `src/bot/tabounv10.py` | V9 + time management + limited quiescence | Stops by time limit, keeps last completed depth |
| `tabounV11` | `src/bot/tabounv11.py` | V10 + Komodo Polyglot opening book | Uses `data/openings/books/komodo3.bin`, copied from the Komodo3 book `Book.bin`; falls back to V10 outside the book |

## Opening book

`tabounV11` uses a Polyglot opening book from Komodo:

```text
data/openings/books/komodo3.bin
```

At each move, `tabounV11` first asks the Komodo book for a weighted book move. If the current position is not in the book, it uses the normal `tabounV10` search.

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

## Arena

Run a round-robin between all bots and export CSV files:

```bash
python -m src.arena.runner
```

Run the arena in parallel:

```bash
python -m src.arena.runner --parallel --workers 4
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

Outputs (inside `arena/`):

- `arena/results.csv` (pair results)
- `arena/ranking.csv` (overall ranking + Elo)
- `arena/matrix.csv` (matrix view per pairing)

## Arena ranking

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
