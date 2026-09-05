# taboun

taboun is a series of chess bots. The first one plays random moves. Each following version keeps what the previous one does and adds one improvement, such as looking further ahead, judging positions better or managing its clock. All versions are kept side by side, so you can see what each idea changes.

You can play against any version, watch two of them play each other, or let them all compete in a tournament. The results are published on a public arena, [geheim.land](https://geheim.land/apps/taboun-chess-bot/arena), where every game can be replayed.

The whole project is written to be read. Each version is one small file, and every tournament can be reproduced.

## Versions

| Version | Change | What it does |
| --- | --- | --- |
| V1 | Random legal move | The baseline. Everyone has to beat it. |
| V2 | Minimax with material counting | Looks two moves ahead and counts the pieces. |
| V3 | Piece-square tables | Learns that a knight in the centre is worth more than one in the corner. |
| V4 | Alpha-beta pruning | Skips the branches that cannot change the result, and reaches three plies. |
| V5 | Move ordering | Looks at captures and checks first, which makes pruning far more effective. |
| V6 | Quiescence search | Follows capture sequences to the end before judging a position. |
| V7 | Transposition table | Remembers positions it has already analysed. |
| V8 | Iterative deepening | Searches one ply, then two, then three, and reuses what it learnt each time. |
| V9 | Improved evaluation | Adds mobility, the bishop pair, pawn structure and king safety. |
| V10 | Time management | Stops when its time is up and keeps the best move found so far. |
| V11 | Opening book | Plays the first moves from the Komodo book. |
| V12 | Mate distance and a smarter table | Prefers the fastest mate and stores the best move of every position. |
| V13 | PeSTO evaluation | Replaces the hand-written evaluation by tables tuned automatically and blended by game phase. |

Every bot has the same interface. It takes a board and returns a move.

## Ratings

The bots are rated against each other in the arena. The rating is relative to this pool, with V2 fixed at 1000 as the origin. It is not a FIDE or Lichess rating. Every number comes with its 95% margin, and every published run links to its games and to the exact commit that played them.

Standings after the first official tournament, played on 5 September 2026 at 10 seconds plus 0.1 second per move, 25 mirrored openings, 3300 games.

| Rank | Bot | Rating | Margin |
| --- | --- | --- | --- |
| 1 | V12 | 2069 | 75 |
| 2 | V11 | 1771 | 67 |
| 3 | V8 | 1764 | 67 |
| 4 | V10 | 1763 | 67 |
| 5 | V9 | 1724 | 66 |
| 6 | V5 | 1593 | 65 |
| 7 | V6 | 1555 | 65 |
| 8 | V7 | 1528 | 65 |
| 9 | V4 | 1427 | 64 |
| 10 | V3 | 1271 | 63 |
| 11 | V2 | 1000 | origin |
| 12 | V1 | 409 | 180 |

V1 scored 2.5 points out of 550, hence its wide margin. A bot that scores no point at all cannot be rated and is listed as unrated.

V13 was added after this tournament. It beat V12 in a sequential test of 568 games with 386 wins, 151 losses and 31 draws, a gain of about 153 points with a margin of 33. It joins the next official tournament.

## Play against a bot

```bash
python -m src.main
```

The game asks a few questions. Start from the initial position or load a FEN or a PGN. Choose human against bot, or bot against bot. Pick a bot and a colour. Then type your moves in standard notation such as `e4`, `Nf3` or `O-O`, or in UCI form such as `e2e4`. Type `resign` to give up. The board is printed after every move, the move list grows in chess notation, and at the end you can save the game as a PGN file.

## Use the bots in a chess app

Every bot speaks UCI, the protocol chess programs use to talk to engines. Point your GUI or tournament manager at this command, run from the repository root.

```bash
python -m src.uci tabounv13
python -m src.uci tabounv13 --no-book
```

The adapter understands game clocks, fixed time per move, fixed depth, stop, FEN positions and move histories. V11 to V13 expose the standard `OwnBook` option. The `info score` line is a static evaluation of the position after the chosen move. It exists for tooling and must never be used to adjudicate games.

## Installation

You need Python 3.10 or newer and the python-chess library.

```bash
python -m venv venv
source venv/bin/activate        # on Windows PowerShell, venv\Scripts\Activate.ps1
pip install python-chess
python -m unittest
```

Tournaments also need the fastchess and Ordo binaries. Their paths are passed on the command line.

## Adding a version

1. It is written as one new file with one new idea, and registered next to the others.
2. It plays its predecessor in a sequential probability ratio test. Same clock, same mirrored openings, books off, until the test decides whether it is better.
3. If it is, it joins a full round robin against every other version.
4. The tournament is published as an immutable bundle with its games, its ranking and its manifest, and the website picks it up.

Older versions never change. When a version receives a time budget it did not have historically, the budget only bounds its search. It never deepens it.

## Running a tournament

Everything runs from the repository root and writes only under `data/arena/`.

```bash
python -m src.arena.build_openings                                              # the deterministic 25-opening suite
python -m src.arena.run_tournament --fastchess /path/to/fastchess               # 10-opening pilot
python -m src.arena.run_tournament --fastchess /path/to/fastchess --official    # 25 openings, the official size
python -m src.arena.run_tournament --fastchess /path/to/fastchess --run-id ID --resume
python -m src.arena.ranking ID --ordo /path/to/ordo
python -m src.arena.publish ID
```

Each run lives in `data/arena/runs/ID` with its PGN, its logs, the opening file it used and a manifest that records the code revision, tool versions, hardware and complete command. The ranking step calls Ordo and writes `ranking.json` and `ranking.csv`. Publication validates every move and every total, then atomically updates `data/arena/latest.json`. A published run is immutable. Rerun under a new ID instead of editing.

To test a candidate against the previous version before spending a full round robin, run the sequential test. It stops on its own, with a hard limit of 500 opening pairs.

```bash
python -m src.arena.run_sprt tabounv14 tabounv13 --fastchess /path/to/fastchess --tc 10+0.1
```

## Technical details

### Arena rules

1. **Historical behaviour preserved.** Without arguments every bot plays as it always did. A time budget bounds a search, it never deepens it beyond the bot's historical maximum depth.
2. **Same computing opportunity.** Same clock for everyone, one thread per engine, mirrored opening pairs, internal books disabled.
3. **Reproducible.** Seed, tool versions, Git commit, exact command and hardware are stored in every run manifest. A tournament refuses to start from a dirty worktree.
4. **Honest rating.** Ratings are relative to this pool with their 95% margins. V2 fixed at 1000 is an origin convention, not an absolute Elo. A bot that scores no point in a run cannot be placed on the scale. It is listed as unrated and its games do not count for the other ratings.
5. **Publication decoupled from computation.** Replaying a published game runs no bot. The website only reads immutable artefacts.
6. **No score adjudication** while the bots do not report a real search score.

### Evaluation functions

| Function | File | Used by | Scores terminal positions |
| --- | --- | --- | --- |
| `evaluate_material` | `src/evaluation/material.py` | V2 | yes |
| `evaluate_simplified` | `src/evaluation/simplified_evaluation_function.py` | V3 to V8 | yes |
| `evaluate_improved` | `src/evaluation/improved_evaluation_function.py` | V9 to V11 | yes |
| `evaluate_fast` | `src/evaluation/fast_evaluation_function.py` | V12 | no, the search does |
| `evaluate_pesto` | `src/evaluation/pesto_evaluation_function.py` | V13 | no, the search does |

The first three return a flat mate score that does not depend on how far away the mate is, so every mating line looks equally good and a bot can shuffle instead of mating. V10 draws king and queen against king for that reason. An evaluation cannot fix this because it does not know the search ply. `evaluate_fast` therefore scores only live positions, and V12 scores mates in the search by their distance.

`evaluate_simplified` and `evaluate_improved` were made faster, by 13 and 3.3 times, without changing a single score, so V3 to V11 still play exactly the same moves.

`evaluate_pesto` drops every hand-written term. It is PeSTO, the evaluation of the engine RofChade. Two piece-square tables per piece, one for the middlegame and one for the endgame, tuned automatically and blended by a game phase computed from the remaining material. V13 runs V12's search on it.

### Time limits and opening books

V2 to V9 accept an optional `time_limit` in seconds.

```python
bot = tabounV7(time_limit=2.0)
```

The default is `None`, which preserves the historical fixed-depth behaviour. With a limit, the bot uses iterative deepening up to its historical maximum depth and returns the best move from the last completed depth. V10 to V13 keep their historical default of one second.

V11 to V13 read the Komodo Polyglot book in `data/openings/books/komodo3.bin` before searching. The book can be disabled, and tournaments always do.

```python
bot = tabounV13(use_book=False)
```

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
│   └── game-000001.json        # UCI and SAN moves plus headers for the replay
└── openings.pgn                # the opening suite actually played
```

Runs that were not published, such as sequential tests, keep their folder but have no `publication` key in their manifest and are ignored by the website.

### Website

The website lives in the sibling repository `geheim-land`, app `apps/taboun_chess_bot`. taboun stays a standalone provider, a command line and files. Three containers touch this repository.

| Container | Sees | Role |
| --- | --- | --- |
| `web` | `data/arena`, read only | Arena page, replay, PostgreSQL archive of published runs |
| `chess-engine` | the repository, read only | interactive Play page, bots with a 2 second budget |
| `arena-runner` | repository read only, `data/arena` writable | runs `python -m src.arena.run_tournament`, then `ranking` and `publish`, on request from the Arena page |

Adding a bot takes five steps. Write `src/bot/tabounv14.py`. Register it in `src/bot/__init__.py`. Add its card to `data/bots.json`. Run the sequential test against the previous version. Commit, because the tournament records the commit it plays and refuses a dirty tree. The launch panel on the site lists the new bot immediately. Only the Play page needs `docker compose restart chess-engine` in `geheim-land`.

### Layout

```text
taboun/
├── README.md
├── data/
│   ├── bots.json               # editorial card of each bot version, shown on the site
│   ├── openings/
│   │   ├── books/komodo3.bin   # Polyglot book used by V11 to V13 and by the opening builder
│   │   ├── arena_openings.pgn  # deterministic 25-opening suite played in tournaments
│   │   └── arena_openings.json # seed, count and SHA-256 of that suite
│   └── arena/
│       ├── runs/<run-id>/      # one immutable folder per tournament (not in git)
│       └── latest.json         # pointer to the last validated run (not in git)
├── src/
│   ├── bot/                    # one file per bot version, plus time_control.py
│   ├── evaluation/             # one evaluation function per file
│   ├── opening/                # Polyglot book lookup
│   ├── uci/                    # UCI engine, engine.py, score.py, __main__.py
│   ├── arena/                  # fastchess pipeline, see src/arena/README.md
│   └── game/  ui/  main.py     # terminal game against a bot
└── tests/
    ├── bots/                   # historical moves, time limits, opening book switch, V12 and V13
    ├── uci/                    # protocol parsing, clock allocation, subprocess sessions
    ├── evaluation/             # PeSTO tables, phase and symmetry
    └── arena/                  # openings, tournament command, ranking, publication, SPRT
```

Every module is imported through the `src` package, for example `from src.bot import BOT_REGISTRY`, and every command runs from the repository root with `python -m`. Generated files only live under `data/arena/`.
