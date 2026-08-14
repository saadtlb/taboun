"""Launch or resume a reproducible Taboun tournament with fastchess."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bot import BOT_REGISTRY  # noqa: E402


DEFAULT_OPENINGS = REPO_ROOT / "data" / "openings" / "arena_openings.pgn"
RUNS_DIR = REPO_ROOT / "data" / "arena" / "runs"
PILOT_ROUNDS = 10
OFFICIAL_ROUNDS = 25
DEFAULT_SEED = 20260814


@dataclass(frozen=True)
class TournamentConfig:
    bot_names: tuple[str, ...]
    openings_path: Path
    rounds: int
    concurrency: int
    time_control: str
    seed: int
    max_moves: int
    time_margin_ms: int
    python_executable: Path
    use_affinity: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def current_commit() -> str:
    return git_output("rev-parse", "HEAD")


def dirty_paths() -> list[str]:
    lines = git_output("status", "--porcelain").splitlines()
    return [line for line in lines if line and line[3:] != "PLAN.md"]


def fastchess_version(executable: Path) -> str:
    result = subprocess.run(
        [str(executable), "-version"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "unknown"


def opening_count(path: Path) -> int:
    count = 0
    with path.open(encoding="utf-8") as source:
        while chess.pgn.read_game(source) is not None:
            count += 1
    return count


def select_bots(raw_names: str | None) -> tuple[str, ...]:
    if raw_names is None:
        return tuple(BOT_REGISTRY)
    names = tuple(name.strip().lower() for name in raw_names.split(",") if name.strip())
    unknown = [name for name in names if name not in BOT_REGISTRY]
    if unknown:
        raise ValueError(f"unknown bots: {', '.join(unknown)}")
    if len(names) < 2:
        raise ValueError("a tournament needs at least two bots")
    if len(set(names)) != len(names):
        raise ValueError("bot names must be unique")
    return names


def build_fastchess_command(
    executable: Path,
    config: TournamentConfig,
    run_dir: Path,
    *,
    resume: bool,
) -> list[str]:
    command = [str(executable)]
    for bot_name in config.bot_names:
        command.extend(
            [
                "-engine",
                f"cmd={config.python_executable}",
                f"name={bot_name}",
                f"args=src/uci.py {bot_name} --no-book",
                f"dir={REPO_ROOT}",
                "proto=uci",
                "restart=off",
            ]
        )

    command.extend(
        [
            "-each",
            f"tc={config.time_control}",
            f"timemargin={config.time_margin_ms}",
            "-tournament",
            "roundrobin",
            "-openings",
            f"file={config.openings_path}",
            "format=pgn",
            "order=sequential",
            "-srand",
            str(config.seed),
            "-rounds",
            str(config.rounds),
            "-repeat",
            "-concurrency",
            str(config.concurrency),
            "-maxmoves",
            str(config.max_moves),
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
            "-output",
            "format=fastchess",
            "-config",
        ]
    )

    config_path = run_dir / "fastchess.json"
    if resume:
        command.append(f"file={config_path}")
    command.extend([f"outname={config_path}", "stats=true"])
    if config.use_affinity:
        command.append("-use-affinity")
    return command


def write_json_atomic(path: Path, value: dict) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def create_manifest(
    config: TournamentConfig,
    command: list[str],
    executable: Path,
    run_id: str,
) -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": current_commit(),
        "fastchess_version": fastchess_version(executable),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "openings_sha256": sha256_file(config.openings_path),
        "command": command,
        "settings": {
            **asdict(config),
            "bot_names": list(config.bot_names),
            "openings_path": str(config.openings_path),
            "python_executable": str(config.python_executable),
        },
    }


def default_run_id(commit: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{commit[:8]}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fastchess", type=Path, help="Path to the fastchess binary.")
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--bots", help="Comma-separated bot names; defaults to all bots.")
    parser.add_argument("--openings", type=Path, default=DEFAULT_OPENINGS)
    parser.add_argument("--rounds", type=int, default=PILOT_ROUNDS)
    parser.add_argument("--official", action="store_true", help=f"Use {OFFICIAL_ROUNDS} rounds.")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--tc", default="60+0.6")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-moves", type=int, default=200)
    parser.add_argument("--time-margin-ms", type=int, default=100)
    parser.add_argument("--run-id", help="Stable run directory name; generated by default.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-affinity", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        bot_names = select_bots(args.bots)
        rounds = OFFICIAL_ROUNDS if args.official else args.rounds
        if rounds < 1:
            raise ValueError("rounds must be at least 1")
        if args.concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        executable = args.fastchess or (
            Path(found) if (found := shutil.which("fastchess")) is not None else None
        )
        if executable is None or not executable.is_file():
            raise FileNotFoundError("fastchess not found; pass --fastchess /path/to/fastchess")
        if not args.python.is_file():
            raise FileNotFoundError(f"Python executable not found: {args.python}")

        dirty = dirty_paths()
        if dirty and not args.allow_dirty:
            raise RuntimeError("refusing tournament from dirty worktree:\n" + "\n".join(dirty))

        commit = current_commit()
        run_id = args.run_id or default_run_id(commit)
        if "/" in run_id or run_id in {"", ".", ".."}:
            raise ValueError("run-id must be one directory name")
        run_dir = RUNS_DIR / run_id
        if args.resume:
            if not (run_dir / "fastchess.json").is_file():
                raise FileNotFoundError(f"resume state not found in {run_dir}")
            openings_path = run_dir / "openings.pgn"
        elif run_dir.exists():
            raise FileExistsError(f"run already exists: {run_dir}")
        else:
            openings_path = args.openings

        if not openings_path.is_file():
            raise FileNotFoundError(f"openings not found: {openings_path}")
        available_openings = opening_count(openings_path)
        if available_openings < rounds:
            raise ValueError(
                f"opening suite has {available_openings} games but tournament needs {rounds}"
            )

        config = TournamentConfig(
            bot_names=bot_names,
            openings_path=openings_path.resolve(),
            rounds=rounds,
            concurrency=args.concurrency,
            time_control=args.tc,
            seed=args.seed,
            max_moves=args.max_moves,
            time_margin_ms=args.time_margin_ms,
            # Keep a virtualenv launcher path intact; resolve() would follow
            # its symlink to the system Python and lose the environment.
            python_executable=args.python.absolute(),
            use_affinity=not args.no_affinity,
        )
        command = build_fastchess_command(executable.resolve(), config, run_dir, resume=args.resume)

        if args.dry_run:
            print(shlex.join(command))
            return

        run_dir.mkdir(parents=True, exist_ok=args.resume)
        if not args.resume:
            run_openings = run_dir / "openings.pgn"
            shutil.copy2(args.openings, run_openings)
            config = replace(config, openings_path=run_openings.resolve())
            command = build_fastchess_command(
                executable.resolve(), config, run_dir, resume=False
            )
        manifest_path = run_dir / "manifest.json"
        if args.resume and manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if "publication" in manifest:
                raise RuntimeError("a published run is immutable and cannot be resumed")
            manifest["status"] = "running"
            manifest["resumed_at"] = datetime.now(timezone.utc).isoformat()
            manifest["command"] = command
        else:
            manifest = create_manifest(config, command, executable.resolve(), run_id)
        write_json_atomic(manifest_path, manifest)

        completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["return_code"] = completed.returncode
        manifest["status"] = "complete" if completed.returncode == 0 else "failed"
        games_path = run_dir / "games.pgn"
        if games_path.is_file():
            manifest["games_sha256"] = sha256_file(games_path)
        write_json_atomic(manifest_path, manifest)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
