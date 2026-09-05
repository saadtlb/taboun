"""Run a bounded fastchess SPRT match between a candidate and its baseline."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.arena.run_tournament import (
    DEFAULT_OPENINGS,
    DEFAULT_SEED,
    REPO_ROOT,
    RUNS_DIR,
    current_commit,
    dirty_paths,
    fastchess_version,
    sha256_file,
    write_json_atomic,
)
from src.bot import BOT_REGISTRY


DEFAULT_ELO0 = 0.0
DEFAULT_ELO1 = 5.0
DEFAULT_ALPHA = 0.05
DEFAULT_BETA = 0.05
DEFAULT_MAX_PAIRS = 500


def build_sprt_command(
    executable: Path,
    *,
    candidate: str,
    baseline: str,
    python: Path,
    openings: Path,
    run_dir: Path,
    time_control: str,
    concurrency: int,
    max_pairs: int,
    seed: int,
    elo0: float,
    elo1: float,
    alpha: float,
    beta: float,
    max_moves: int,
    resume: bool,
) -> list[str]:
    """Build the command as an argument list, never as a shell string."""
    command = [str(executable)]
    for bot_name in (candidate, baseline):
        command.extend(
            [
                "-engine",
                f"cmd={python}",
                f"name={bot_name}",
                f"args=-m src.uci {bot_name} --no-book",
                f"dir={REPO_ROOT}",
                "proto=uci",
                "restart=off",
            ]
        )
    command.extend(
        [
            "-each",
            f"tc={time_control}",
            "timemargin=100",
            "-openings",
            f"file={openings}",
            "format=pgn",
            "order=random",
            "-srand",
            str(seed),
            "-rounds",
            str(max_pairs),
            "-repeat",
            "-sprt",
            f"elo0={elo0}",
            f"elo1={elo1}",
            f"alpha={alpha}",
            f"beta={beta}",
            "model=normalized",
            "-concurrency",
            str(concurrency),
            "-maxmoves",
            str(max_moves),
            "-recover",
            "-autosaveinterval",
            "10",
            "-pgnout",
            f"file={run_dir / 'games.pgn'}",
            "notation=san",
            "append=true",
            "timeleft=true",
            "-log",
            f"file={run_dir / 'fastchess.log'}",
            "level=info",
            "append=true",
            "engine=false",
            "-config",
        ]
    )
    state = run_dir / "fastchess.json"
    if resume:
        command.append(f"file={state}")
    command.extend([f"outname={state}", "stats=true"])
    return command


def read_decision(output_lines: list[str]) -> str:
    output = "\n".join(output_lines).lower()
    if "h1 was accepted" in output:
        return "h1_accepted"
    if "h0 was accepted" in output:
        return "h0_accepted"
    return "inconclusive_at_limit"


def run_and_capture(command: list[str], output_path: Path) -> tuple[int, list[str]]:
    interesting: list[str] = []
    with output_path.open("a", encoding="utf-8") as output:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            output.write(line)
            output.flush()
            lowered = line.lower()
            if "sprt" in lowered or "llr:" in lowered or "accepted" in lowered:
                interesting.append(line.strip())
        return process.wait(), interesting[-20:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", help="New bot under test, for example tabounv13.")
    parser.add_argument("baseline", help="Previous accepted bot, for example tabounv12.")
    parser.add_argument("--fastchess", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--openings", type=Path, default=DEFAULT_OPENINGS)
    parser.add_argument("--tc", default="60+0.6")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-pairs", type=int, default=DEFAULT_MAX_PAIRS)
    parser.add_argument("--max-moves", type=int, default=200)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--elo0", type=float, default=DEFAULT_ELO0)
    parser.add_argument("--elo1", type=float, default=DEFAULT_ELO1)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--beta", type=float, default=DEFAULT_BETA)
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        candidate = args.candidate.lower()
        baseline = args.baseline.lower()
        if candidate not in BOT_REGISTRY or baseline not in BOT_REGISTRY:
            raise ValueError("candidate and baseline must be registered bots")
        if candidate == baseline:
            raise ValueError("candidate and baseline must be different")
        if args.elo1 <= args.elo0:
            raise ValueError("elo1 must be greater than elo0")
        if not 0 < args.alpha < 1 or not 0 < args.beta < 1:
            raise ValueError("alpha and beta must be between 0 and 1")
        if args.max_pairs < 1 or args.concurrency < 1:
            raise ValueError("max-pairs and concurrency must be positive")
        if not args.openings.is_file() or not args.python.is_file():
            raise FileNotFoundError("openings or Python executable not found")
        executable = args.fastchess or (
            Path(found) if (found := shutil.which("fastchess")) else None
        )
        if executable is None or not executable.is_file():
            raise FileNotFoundError("fastchess not found; pass --fastchess /path/to/fastchess")
        dirty = dirty_paths()
        if dirty and not args.allow_dirty:
            raise RuntimeError("refusing SPRT from dirty worktree:\n" + "\n".join(dirty))

        commit = current_commit()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = args.run_id or f"sprt-{candidate}-vs-{baseline}-{timestamp}-{commit[:8]}"
        if "/" in run_id or run_id in {"", ".", ".."}:
            raise ValueError("run-id must be one directory name")
        run_dir = RUNS_DIR / run_id
        run_openings = run_dir / "openings.pgn"
        state_path = run_dir / "fastchess.json"
        manifest_path = run_dir / "manifest.json"
        if args.resume:
            if not state_path.is_file() or not run_openings.is_file():
                raise FileNotFoundError(f"resume state not found in {run_dir}")
        elif run_dir.exists():
            raise FileExistsError(f"run already exists: {run_dir}")

        effective_openings = run_openings if args.resume else args.openings.resolve()
        command = build_sprt_command(
            executable.resolve(),
            candidate=candidate,
            baseline=baseline,
            python=args.python.absolute(),
            openings=effective_openings,
            run_dir=run_dir,
            time_control=args.tc,
            concurrency=args.concurrency,
            max_pairs=args.max_pairs,
            seed=args.seed,
            elo0=args.elo0,
            elo1=args.elo1,
            alpha=args.alpha,
            beta=args.beta,
            max_moves=args.max_moves,
            resume=args.resume,
        )
        if args.dry_run:
            print(shlex.join(command))
            return

        run_dir.mkdir(parents=True, exist_ok=args.resume)
        if not args.resume:
            shutil.copy2(args.openings, run_openings)
            command = build_sprt_command(
                executable.resolve(),
                candidate=candidate,
                baseline=baseline,
                python=args.python.absolute(),
                openings=run_openings.resolve(),
                run_dir=run_dir,
                time_control=args.tc,
                concurrency=args.concurrency,
                max_pairs=args.max_pairs,
                seed=args.seed,
                elo0=args.elo0,
                elo1=args.elo1,
                alpha=args.alpha,
                beta=args.beta,
                max_moves=args.max_moves,
                resume=False,
            )

        if args.resume:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["resumed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            manifest = {
                "schema_version": 1,
                "kind": "sprt",
                "run_id": run_id,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "git_commit": commit,
                "fastchess_version": fastchess_version(executable.resolve()),
                "openings_sha256": sha256_file(run_openings),
                "settings": {
                    "candidate": candidate,
                    "baseline": baseline,
                    "time_control": args.tc,
                    "concurrency": args.concurrency,
                    "max_pairs": args.max_pairs,
                    "max_moves": args.max_moves,
                    "seed": args.seed,
                    "elo0": args.elo0,
                    "elo1": args.elo1,
                    "alpha": args.alpha,
                    "beta": args.beta,
                    "model": "normalized",
                },
            }
        manifest["status"] = "running"
        manifest["command"] = command
        write_json_atomic(manifest_path, manifest)

        return_code, decision_lines = run_and_capture(command, run_dir / "fastchess.out")
        decision_lines = [*manifest.get("decision_lines", []), *decision_lines][-20:]
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["return_code"] = return_code
        manifest["status"] = "complete" if return_code == 0 else "failed"
        manifest["decision"] = read_decision(decision_lines)
        manifest["decision_lines"] = decision_lines
        if (games_path := run_dir / "games.pgn").is_file():
            manifest["games_sha256"] = sha256_file(games_path)
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            manifest["result"] = {"sprt": state.get("sprt"), "stats": state.get("stats")}
        write_json_atomic(manifest_path, manifest)
        if return_code:
            raise SystemExit(return_code)
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
