# Arena modules

Each file has one job:

- `build_openings.py` creates a deterministic paired-opening suite from the
  Polyglot book.
- `run_tournament.py` launches or resumes fastchess and records the exact run
  conditions.
- `ranking.py` calculates a relative rating list from a completed PGN.
- `publish.py` validates a run and builds the read-only bundle consumed by the
  website.

The historical `runner.py` remains available as a legacy runner until the
first fastchess tournament has been published end to end.
