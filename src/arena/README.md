# Arena modules

Each file has one job:

- `build_openings.py` creates a deterministic paired-opening suite from the
  Polyglot book.
- `run_tournament.py` launches or resumes fastchess and records the exact run
  conditions in `manifest.json`.
- `ranking.py` calculates a relative rating list from a completed PGN with
  Ordo.
- `publish.py` validates a run and builds the read-only bundle consumed by the
  website.
- `run_sprt.py` runs a bounded candidate-versus-baseline acceptance test.
- `legacy/` holds the original in-process arena, frozen.

Everything runs from the repository root with `python -m src.arena.<module>`.
Each engine is started by fastchess as `python -m src.uci <bot> --no-book`
with the repository as working directory.

## Principles

- Same clock for every bot, one thread per engine, mirrored opening pairs,
  internal books disabled.
- A tournament refuses to start from a dirty worktree, because the manifest
  records the commit that played.
- Ratings are relative to this pool: `tabounv1` is fixed at 1000 as the
  origin, and the 95% margins from Ordo's simulations are published with them.
- No adjudication by score: the UCI `info score` is a static evaluation, not
  a search result.
- A published run is immutable. Rerun under a new ID instead of editing.

## Complete workflow

Each tournament copies its opening suite into its own run directory. This copy
is the file used by fastchess and makes the run self-contained:

```bash
python3 -m src.arena.run_tournament --fastchess ~/.local/bin/fastchess \
  --python /path/to/venv/bin/python --run-id 2026-08-14-pilot
```

After fastchess exits successfully, build the relative ranking with Ordo, then
publish the replay files:

```bash
python3 -m src.arena.ranking 2026-08-14-pilot --ordo ~/.local/bin/ordo
python3 -m src.arena.publish 2026-08-14-pilot
```

Publication validates every PGN move and every W/D/L total, creates the
per-game JSON files, then atomically updates `data/arena/latest.json`.

## Published bundle

```text
data/arena/latest.json          # schema_version, run_id, published_at
data/arena/runs/<run-id>/
├── manifest.json               # settings, commit, tools, hardware, command, checksums
├── ranking.json                # rating list for the site, with margins and CFS
├── ranking.csv                 # same list for humans and spreadsheets
├── bots.json                   # copy of data/bots.json at publication time
├── games.pgn                   # canonical complete PGN
├── games/
│   ├── index.json              # id, colours, result, opening, termination
│   └── game-000001.json        # UCI/SAN moves and headers for the replay
└── openings.pgn                # the opening suite actually played
```

The website reads exactly this layout (`geheim-land/apps/taboun_chess_bot/arena`).
Any schema change is made here first, tested on a temporary bundle, then
supported on the site before the next run is published. `manifest.json`
carries `schema_version` for that purpose.

## Future bot acceptance

A new version first plays the previous accepted version under identical
conditions and paired colors:

```bash
python3 -m src.arena.run_sprt tabounv13 tabounv12 \
  --fastchess ~/.local/bin/fastchess --python /path/to/venv/bin/python
```

The defaults test normalized Elo hypotheses H0 = 0 and H1 = +5 with
alpha = beta = 0.05, up to 500 opening pairs (1000 games). The bound prevents
an undecided test from running forever. Accepting H1 is evidence of a gain in
these conditions, not permission to skip the full round-robin publication.

## Legacy folder

`legacy/` holds the original in-process arena (`runner.py`, `match.py`,
`export.py`). It is frozen and untested; its CSV outputs are archived under
`data/arena/legacy/`. Nothing in the fastchess pipeline imports it.
