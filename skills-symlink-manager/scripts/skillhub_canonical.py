#!/usr/bin/env python3
"""
Install a SkillHub skill into the canonical ~/.agents/skills repo, then
symlink it into detected agent skill directories and optionally git commit/push.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def run_cmd(cmd: List[str], cwd: Optional[Path] = None, dry_run: bool = False) -> int:
    prefix = "+ "
    location = f" (cwd={cwd})" if cwd else ""
    print(prefix + shlex.join(cmd) + location)
    if dry_run:
        return 0
    completed = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def capture(cmd: List[str], cwd: Optional[Path] = None) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, text=True).strip()


def has_staged_changes(repo: Path, paths: List[str]) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *paths],
        cwd=str(repo),
    )
    return result.returncode == 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install a SkillHub skill into ~/.agents/skills, link it into detected agents, "
            "and git commit/push the canonical repo."
        )
    )
    parser.add_argument("slug", help="Skill slug to install from SkillHub")
    parser.add_argument(
        "--canonical",
        default="~/.agents/skills",
        help="Canonical skills repository (default: ~/.agents/skills)",
    )
    parser.add_argument(
        "--skillhub-bin",
        default="skillhub",
        help="SkillHub CLI binary (default: skillhub)",
    )
    parser.add_argument(
        "--agents",
        action="append",
        help="Comma-separated list of agent keys to target during linking",
    )
    parser.add_argument(
        "--all-agents",
        action="store_true",
        help="Link to all known agents instead of only detected ones",
    )
    parser.add_argument(
        "--force-install",
        action="store_true",
        help="Pass --force to skillhub install",
    )
    parser.add_argument(
        "--force-links",
        action="store_true",
        help="Replace conflicting link targets when linking",
    )
    parser.add_argument(
        "--no-link",
        action="store_true",
        help="Skip the symlink step",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git add/commit/push",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit locally but do not push",
    )
    parser.add_argument(
        "--git-remote",
        default="origin",
        help="Git remote to push to (default: origin)",
    )
    parser.add_argument(
        "--commit-message",
        help="Custom git commit message",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without making changes",
    )
    return parser


def main(argv: List[str]) -> int:
    args = build_parser().parse_args(argv)

    canonical = _expand(args.canonical)
    if not canonical.exists() and not args.dry_run:
        raise SystemExit(f"Canonical dir not found: {canonical}")

    script_dir = Path(__file__).resolve().parent
    symlink_manager = script_dir / "skills_symlink_manager.py"
    if not symlink_manager.exists():
        raise SystemExit(f"Missing symlink manager: {symlink_manager}")

    install_cmd = [
        args.skillhub_bin,
        "--dir",
        str(canonical),
        "install",
        args.slug,
    ]
    if args.force_install:
        install_cmd.append("--force")
    run_cmd(install_cmd, dry_run=args.dry_run)

    if not args.no_link:
        link_cmd: List[str] = [sys.executable, str(symlink_manager)]
        if args.all_agents:
            link_cmd.append("--all-agents")
        if args.agents:
            for item in args.agents:
                link_cmd.extend(["--agents", item])
        link_cmd.extend(["link", "--skill", args.slug])
        if args.force_links:
            link_cmd.append("--force")
        run_cmd(link_cmd, cwd=canonical, dry_run=args.dry_run)

    if args.no_git:
        return 0

    if not (canonical / ".git").exists() and not args.dry_run:
        print(f"warn: {canonical} is not a git repo; skip git steps", file=sys.stderr)
        return 0

    tracked_paths = [args.slug]
    lockfile = canonical / ".skills_store_lock.json"
    if lockfile.exists() or args.dry_run:
        tracked_paths.append(lockfile.name)

    run_cmd(["git", "add", "--", *tracked_paths], cwd=canonical, dry_run=args.dry_run)

    if args.dry_run:
        message = args.commit_message or f"feat(skills): install {args.slug} via skillhub"
        push_note = " (push skipped by --no-push)" if args.no_push else ""
        print(f"dry-run: would commit with message: {message}{push_note}")
        return 0

    if not has_staged_changes(canonical, tracked_paths):
        print("No staged changes for installed skill; skip commit/push.")
        return 0

    message = args.commit_message or f"feat(skills): install {args.slug} via skillhub"
    run_cmd(["git", "commit", "-m", message], cwd=canonical)

    if args.no_push:
        return 0

    branch = capture(["git", "branch", "--show-current"], cwd=canonical) or "main"
    run_cmd(["git", "push", args.git_remote, branch], cwd=canonical)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
