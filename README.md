# taboun

taboun is a Python chess bot laboratory built on `python-chess`: twelve bot
versions with one idea each, a UCI adapter, and a reproducible fastchess arena
whose published results feed the public showcase on geheim.land.

## Layout

```text
taboun/
├── README.md
├── data/
│   ├── bots.json               # editorial card of each bot version, shown on the site
│   ├── openings/
│   │   ├── books/komodo3.bin   # Polyglot book used by V11/V12 and by the opening builder
│   │   ├── arena_openings.pgn  # deterministic 25-opening suite played in tournaments
│   │   └── arena_openings.json # seed, count and SHA-256 of that suite
│   └── arena/
│       ├── runs/<run-id>/      # one immutable folder per tournament (not in git)
│       └── latest.json         # pointer to the last validated run (not in git)
├── src/
│   ├── bot/                    # one file per bot version, plus time_control.py
│   ├── evaluation/             # the four evaluation functions
│   ├── opening/                # Polyglot book lookup
│   ├── uci/                    # UCI engine: engine.py, score.py, __main__.py
│   ├── arena/                  # fastchess pipeline, see src/arena/README.md
│   └── game/  ui/  main.py     # terminal game against a bot
└── tests/
    ├── bots/                   # historical moves, time limits, opening book switch
    ├── uci/                    # protocol parsing, clock allocation, subprocess sessions
    └── arena/                  # openings, tournament command, ranking, publication, SPRT
```

Every module is imported through the `src` package, for example
`from src.bot import BOT_REGISTRY`, and every command runs from the repository
root with `python -m`. Generated files only live under `data/arena/`.

## Bots

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
python3 -m src.uci tabounv12
python3 -m src.uci tabounv12 --no-book
```

Run it from the repository root. fastchess starts the same command with its
`dir=` option pointing at the repository. `src/uci/engine.py` holds the
protocol and clock logic, `src/uci/score.py` the static score telemetry.

The adapter understands game clocks (`wtime`, `btime`, increments and
`movestogo`), fixed `movetime`, `depth`, `stop`, FEN positions and move
histories. It exposes the standard `OwnBook` option for V11 and V12.

Because the historical bot API returns only a move, UCI `info score` is a
documented **static evaluation after that move**, using the evaluation family
of the selected bot. It exists for protocol tooling and must not be used for
score-based game adjudication.

## Requirements

- Python 3.10 or newer
- `python-chess`

```bash
python -m venv venv
source venv/bin/activate        # Windows PowerShell: venv\Scripts\Activate.ps1
pip install python-chess
python -m unittest              # or: python -m pytest
```

Tournaments additionally need the `fastchess` and `ordo` binaries; their
paths are passed on the command line.

## Terminal game

```bash
python -m src.main
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

The arena is the only source of published rankings. Its rules:

1. **Historical behaviour preserved.** Without arguments every bot plays as it
   always did; a time budget bounds a search, it never deepens it beyond the
   bot's historical maximum depth.
2. **Same computing opportunity.** Same clock for everyone, one thread per
   engine, mirrored opening pairs, internal books disabled.
3. **Reproducible.** Seed, tool versions, Git commit, exact command and
   hardware are stored in every run manifest. A tournament refuses to start
   from a dirty worktree.
4. **Honest Elo.** Ratings are relative to this pool with their 95% margins;
   V2 fixed at 1000 is an origin convention, not an absolute Elo. A bot that
   scores no point in a run, which is what the random V1 does at real time
   controls, cannot be placed on the scale: it is listed as unrated and its
   games do not count for the other ratings.
5. **Publication decoupled from computation.** Replaying a published game runs
   no bot. The website only reads immutable artefacts.
6. **No score adjudication** while the bots do not report a real search score.

### Workflow

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
The opening file used by fastchess is copied into that directory, so a run is
self-contained. Opening books are disabled for V11 and V12. The initial
official time control is 60 seconds plus 0.6 seconds per move, with four
concurrent games.

Create the relative Ordo ranking and the website replay bundle after a
successful run:

```bash
python3 -m src.arena.ranking ID --ordo /path/to/ordo
python3 -m src.arena.publish ID
```

`ranking.json` records Ordo's version, exact command and 95% simulation
margins. Publication validates the PGN and all W/D/L totals before atomically
changing `data/arena/latest.json`; published runs cannot be resumed or
overwritten.

### Published bundle

```text
data/arena/latest.json          # schema_version, run_id, published_at
data/arena/runs/<run-id>/
├── manifest.json               # settings, commit, tools, hardware, command, checksums
├── ranking.json                # rating list for the site, with margins, CFS and unrated bots
├── ranking.csv                 # same list for humans and spreadsheets
├── bots.json                   # copy of data/bots.json at publication time
├── games.pgn                   # canonical complete PGN
├── games/
│   ├── index.json              # id, colours, result, opening, termination
│   └── game-000001.json        # UCI/SAN moves and headers for the replay
└── openings.pgn                # the opening suite actually played
```

Runs that were not published, such as SPRT matches, keep their folder but
have no `publication` key in the manifest and are ignored by the site.

### Accepting a new version

For a future V13, run a bounded SPRT against the previous accepted version
before spending time on a complete round robin:

```bash
python3 -m src.arena.run_sprt tabounv13 tabounv12 \
  --fastchess /path/to/fastchess --python /path/to/venv/bin/python
```

The default normalized-Elo hypotheses are H0 = 0 and H1 = +5, with
alpha = beta = 0.05 and a hard limit of 500 mirrored opening pairs. The
manifest records the exact hypotheses, command, result and fastchess state.
An H1 acceptance still requires the official round robin before publication.

## Website

The public showcase lives in the sibling repository `geheim-land`, app
`apps/taboun_chess_bot`. taboun stays a standalone provider: a CLI and files.
Three containers touch this repository:

| Container | Sees | Role |
| --- | --- | --- |
| `web` | `data/arena`, read-only | Arena page, replay, PostgreSQL archive of published runs |
| `chess-engine` | the repository, read-only | interactive Play page, bots with a 2 s budget |
| `arena-runner` | repository read-only, `data/arena` writable | runs `python -m src.arena.run_tournament`, then `ranking` and `publish`, on request from the Arena page |

Adding a bot:

1. write `src/bot/tabounv13.py`;
2. register it in `src/bot/__init__.py`;
3. add its card to `data/bots.json`;
4. run the SPRT above against the previous version;
5. commit. The worktree must be clean: the tournament records the commit it
   plays and refuses a dirty tree.

The launch panel on the site lists the new bot immediately, because the
runner reads `BOT_REGISTRY` at each request. Only the Play page needs
`docker compose restart chess-engine` in `geheim-land`.
