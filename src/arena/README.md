# Arena modules

Each file has one job:

- `build_openings.py` creates a deterministic paired-opening suite from the
  Polyglot book.
- `run_tournament.py` launches or resumes fastchess and records the exact run
  conditions.
- `ranking.py` calculates a relative rating list from a completed PGN.
- `publish.py` validates a run and builds the read-only bundle consumed by the
  website.
- `run_sprt.py` runs a bounded candidate-versus-baseline acceptance test.

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

Ordo fixes `tabounv1` at 1000 to define the origin of this pool. These numbers
are relative ratings, not universal Elo values. The 95% margins come from
Ordo's simulations; the exact command and tool version are stored in
`ranking.json`.

Publication validates every PGN move and every W/D/L total, creates the
per-game JSON files, then atomically updates `data/arena/latest.json`. A
published run is immutable: rerun the tournament under a new ID instead of
editing its results.

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

The historical `runner.py` remains available as a legacy runner until the
first fastchess tournament has been published end to end.
