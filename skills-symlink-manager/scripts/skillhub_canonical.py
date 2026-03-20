#!/usr/bin/env python3
"""
Canonical SkillHub workflow helper.

Default behavior preserves backward compatibility:
- `skillhub-canonical <slug>` => install into ~/.agents/skills

Extended behavior:
- `skillhub-canonical install <slug>`
- `skillhub-canonical upgrade [slug]`
- `skillhub-canonical update [slug]`

After install/upgrade it can relink skills into detected agent skill directories
and git add/commit/push the canonical repo.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


DEFAULT_CANONICAL = "~/.agents/skills"
DEFAULT_SKILLHUB_BIN = "skillhub"
DEFAULT_GIT_REMOTE = "origin"
LOCKFILE_NAME = ".skills_store_lock.json"


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def sh(cmd: Sequence[str]) -> str:
    return shlex.join(list(cmd))


def run_cmd(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    dry_run: bool = False,
    allow_exit_codes: Optional[Iterable[int]] = None,
) -> int:
    allow = set(allow_exit_codes or [])
    location = f" (cwd={cwd})" if cwd else ""
    print(f"+ {sh(cmd)}{location}")
    if dry_run:
        return 0
    completed = subprocess.run(list(cmd), cwd=str(cwd) if cwd else None)
    if completed.returncode != 0 and completed.returncode not in allow:
        raise SystemExit(completed.returncode)
    return completed.returncode


def capture(cmd: Sequence[str], *, cwd: Optional[Path] = None) -> str:
    return subprocess.check_output(list(cmd), cwd=str(cwd) if cwd else None, text=True).strip()


def lockfile_path(canonical: Path) -> Path:
    return canonical / LOCKFILE_NAME


def load_lockfile_slugs(canonical: Path) -> List[str]:
    path = lockfile_path(canonical)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    skills = raw.get("skills", {}) if isinstance(raw, dict) else {}
    if not isinstance(skills, dict):
        return []
    return sorted(str(k).strip() for k in skills.keys() if str(k).strip())


def unique_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def has_staged_changes(repo: Path, paths: Sequence[str]) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *paths],
        cwd=str(repo),
    )
    return result.returncode == 1


def build_common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--canonical",
        default=DEFAULT_CANONICAL,
        help=f"Canonical skills repository (default: {DEFAULT_CANONICAL})",
    )
    parser.add_argument(
        "--skillhub-bin",
        default=DEFAULT_SKILLHUB_BIN,
        help=f"SkillHub CLI binary (default: {DEFAULT_SKILLHUB_BIN})",
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
        default=DEFAULT_GIT_REMOTE,
        help=f"Git remote to push to (default: {DEFAULT_GIT_REMOTE})",
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


def build_install_parser() -> argparse.ArgumentParser:
    parser = build_common_parser(
        "Install a SkillHub skill into ~/.agents/skills, link it into detected agents, and git commit/push the canonical repo."
    )
    parser.add_argument("slug", help="Skill slug to install from SkillHub")
    parser.add_argument(
        "--force-install",
        action="store_true",
        help="Pass --force to skillhub install",
    )
    return parser


def build_upgrade_parser() -> argparse.ArgumentParser:
    parser = build_common_parser(
        "Upgrade SkillHub-installed skills inside ~/.agents/skills, then relink and git commit/push."
    )
    parser.add_argument(
        "slug",
        nargs="?",
        help="Optional skill slug to upgrade. If omitted, upgrade all skills in the lockfile.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Upgrade all installed skills (same as omitting slug).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check and print available upgrades without installing.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Timeout in seconds for manifest fetch (default: 20)",
    )
    return parser


def build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillhub-canonical",
        description=(
            "Canonical SkillHub helper for ~/.agents/skills.\n\n"
            "Default usage is backward-compatible: `skillhub-canonical <slug>` installs a skill.\n"
            "Explicit subcommands are also supported: install / upgrade / update."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.epilog = (
        "Examples:\n"
        "  skillhub-canonical caldav-calendar\n"
        "  skillhub-canonical install caldav-calendar --no-push\n"
        "  skillhub-canonical upgrade caldav-calendar\n"
        "  skillhub-canonical update --all\n"
        "  skillhub-canonical upgrade --check-only\n"
    )
    return parser


def resolve_canonical(args: argparse.Namespace) -> Path:
    canonical = _expand(args.canonical)
    if not canonical.exists() and not args.dry_run:
        raise SystemExit(f"Canonical dir not found: {canonical}")
    return canonical


def resolve_symlink_manager(script_dir: Path) -> Path:
    symlink_manager = script_dir / "skills_symlink_manager.py"
    if not symlink_manager.exists():
        raise SystemExit(f"Missing symlink manager: {symlink_manager}")
    return symlink_manager


def build_link_cmd(
    *,
    symlink_manager: Path,
    canonical: Path,
    agents: Optional[List[str]],
    all_agents: bool,
    force_links: bool,
    skills: List[str],
    all_skills: bool = False,
) -> List[str]:
    cmd: List[str] = [sys.executable, str(symlink_manager)]
    if all_agents:
        cmd.append("--all-agents")
    if agents:
        for item in agents:
            cmd.extend(["--agents", item])
    cmd.append("link")
    if all_skills:
        cmd.append("--all-skills")
    else:
        for skill in skills:
            cmd.extend(["--skill", skill])
    if force_links:
        cmd.append("--force")
    return cmd


def maybe_link_skills(
    *,
    args: argparse.Namespace,
    canonical: Path,
    symlink_manager: Path,
    skills: List[str],
    all_skills: bool = False,
) -> None:
    if args.no_link:
        return
    if not all_skills and not skills:
        return
    cmd = build_link_cmd(
        symlink_manager=symlink_manager,
        canonical=canonical,
        agents=args.agents,
        all_agents=args.all_agents,
        force_links=args.force_links,
        skills=skills,
        all_skills=all_skills,
    )
    run_cmd(cmd, cwd=canonical, dry_run=args.dry_run)


def maybe_git_commit(
    *,
    args: argparse.Namespace,
    canonical: Path,
    tracked_paths: List[str],
    default_message: str,
) -> int:
    if args.no_git:
        return 0

    if not (canonical / ".git").exists() and not args.dry_run:
        print(f"warn: {canonical} is not a git repo; skip git steps", file=sys.stderr)
        return 0

    tracked_paths = unique_keep_order(tracked_paths)
    run_cmd(["git", "add", "--", *tracked_paths], cwd=canonical, dry_run=args.dry_run)

    message = args.commit_message or default_message
    if args.dry_run:
        push_note = " (push skipped by --no-push)" if args.no_push else ""
        print(f"dry-run: would commit with message: {message}{push_note}")
        return 0

    if not has_staged_changes(canonical, tracked_paths):
        print("No staged changes for tracked skill paths; skip commit/push.")
        return 0

    run_cmd(["git", "commit", "-m", message], cwd=canonical)

    if args.no_push:
        return 0

    branch = capture(["git", "branch", "--show-current"], cwd=canonical) or "main"
    run_cmd(["git", "push", args.git_remote, branch], cwd=canonical)
    return 0


def run_install_mode(argv: List[str], script_dir: Path) -> int:
    args = build_install_parser().parse_args(argv)
    canonical = resolve_canonical(args)
    symlink_manager = resolve_symlink_manager(script_dir)

    install_cmd: List[str] = [
        args.skillhub_bin,
        "--dir",
        str(canonical),
        "install",
        args.slug,
    ]
    if args.force_install:
        install_cmd.append("--force")
    run_cmd(install_cmd, dry_run=args.dry_run)

    maybe_link_skills(
        args=args,
        canonical=canonical,
        symlink_manager=symlink_manager,
        skills=[args.slug],
    )

    tracked_paths = [args.slug]
    if lockfile_path(canonical).exists() or args.dry_run:
        tracked_paths.append(LOCKFILE_NAME)
    return maybe_git_commit(
        args=args,
        canonical=canonical,
        tracked_paths=tracked_paths,
        default_message=f"feat(skills): install {args.slug} via skillhub",
    )


def run_upgrade_mode(argv: List[str], script_dir: Path) -> int:
    args = build_upgrade_parser().parse_args(argv)
    canonical = resolve_canonical(args)
    symlink_manager = resolve_symlink_manager(script_dir)

    before_slugs = load_lockfile_slugs(canonical)
    if args.slug and args.all:
        raise SystemExit("Use either a slug or --all, not both.")

    target_slug = None if args.all else args.slug
    upgrade_cmd: List[str] = [args.skillhub_bin, "--dir", str(canonical), "upgrade"]
    if args.check_only:
        upgrade_cmd.append("--check-only")
    if args.timeout:
        upgrade_cmd.extend(["--timeout", str(args.timeout)])
    if target_slug:
        upgrade_cmd.append(target_slug)

    run_cmd(upgrade_cmd, dry_run=args.dry_run, allow_exit_codes={2} if not args.dry_run else None)

    if args.check_only:
        return 0

    after_slugs = load_lockfile_slugs(canonical)
    if target_slug:
        relink_skills = [target_slug]
    else:
        relink_skills = unique_keep_order([*before_slugs, *after_slugs])

    maybe_link_skills(
        args=args,
        canonical=canonical,
        symlink_manager=symlink_manager,
        skills=relink_skills,
    )

    tracked_paths = [*relink_skills]
    if lockfile_path(canonical).exists() or args.dry_run:
        tracked_paths.append(LOCKFILE_NAME)

    message = (
        f"chore(skills): upgrade {target_slug} via skillhub"
        if target_slug
        else "chore(skills): upgrade skills via skillhub"
    )
    return maybe_git_commit(
        args=args,
        canonical=canonical,
        tracked_paths=tracked_paths,
        default_message=message,
    )


def main(argv: List[str]) -> int:
    script_dir = Path(__file__).resolve().parent

    if not argv or argv[0] in {"-h", "--help"}:
        build_root_parser().print_help()
        return 0

    command = argv[0]
    if command in {"upgrade", "update"}:
        return run_upgrade_mode(argv[1:], script_dir)
    if command == "install":
        return run_install_mode(argv[1:], script_dir)

    # Backward compatible default: treat first argument as install slug.
    return run_install_mode(argv, script_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
