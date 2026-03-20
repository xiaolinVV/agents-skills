#!/usr/bin/env python3
"""
Canonical SkillHub workflow helper.

Default behavior preserves backward compatibility:
- `skillhub-canonical <slug>` => install into ~/.agents/skills

Extended behavior:
- `skillhub-canonical install <slug>`
- `skillhub-canonical upgrade [slug]`
- `skillhub-canonical update [slug]`

Behavior summary:
- Prefer SkillHub first.
- If SkillHub install/upgrade is unavailable or fails, fallback to ClawHub.
- Keep ~/.agents/skills as the canonical repo.
- Relink changed skills into detected agent skill directories.
- Git add / commit / push the canonical repo.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


DEFAULT_CANONICAL = "~/.agents/skills"
DEFAULT_SKILLHUB_BIN = "skillhub"
DEFAULT_CLAWHUB_BIN = "auto"
DEFAULT_GIT_REMOTE = "origin"
LOCKFILE_NAME = ".skills_store_lock.json"
CLAWHUB_LOCKFILE_NAME = ".clawhub/lock.json"


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def sh(cmd: Sequence[str]) -> str:
    return shlex.join(list(cmd))


def run_attempt(cmd: Sequence[str], *, cwd: Optional[Path] = None, dry_run: bool = False) -> int:
    location = f" (cwd={cwd})" if cwd else ""
    print(f"+ {sh(cmd)}{location}")
    if dry_run:
        return 0
    try:
        completed = subprocess.run(list(cmd), cwd=str(cwd) if cwd else None)
        return completed.returncode
    except FileNotFoundError:
        print(f"warn: command not found: {cmd[0]}", file=sys.stderr)
        return 127


def run_cmd(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    dry_run: bool = False,
    allow_exit_codes: Optional[Iterable[int]] = None,
) -> int:
    allow = set(allow_exit_codes or [])
    code = run_attempt(cmd, cwd=cwd, dry_run=dry_run)
    if code != 0 and code not in allow:
        raise SystemExit(code)
    return code


def capture(cmd: Sequence[str], *, cwd: Optional[Path] = None) -> str:
    return subprocess.check_output(list(cmd), cwd=str(cwd) if cwd else None, text=True).strip()


def unique_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def lockfile_path(canonical: Path) -> Path:
    return canonical / LOCKFILE_NAME


def clawhub_lockfile_path(canonical: Path) -> Path:
    return canonical / ".clawhub" / "lock.json"


def load_skillhub_lock_slugs(canonical: Path) -> List[str]:
    raw = load_json(lockfile_path(canonical))
    skills = raw.get("skills", {})
    if not isinstance(skills, dict):
        return []
    return sorted(str(k).strip() for k in skills.keys() if str(k).strip())


def load_clawhub_lock_slugs(canonical: Path) -> List[str]:
    raw = load_json(clawhub_lockfile_path(canonical))
    skills = raw.get("skills", {})
    if not isinstance(skills, dict):
        return []
    return sorted(str(k).strip() for k in skills.keys() if str(k).strip())


def has_staged_changes(repo: Path, paths: Sequence[str]) -> bool:
    result = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=str(repo))
    return result.returncode == 1


def split_cmd(spec: str) -> List[str]:
    return [part for part in shlex.split(spec) if part]


def resolve_clawhub_cmd(spec: str) -> List[str]:
    raw = (spec or "").strip()
    if raw and raw.lower() != "auto":
        return split_cmd(raw)
    if shutil.which("clawhub"):
        return ["clawhub"]
    if shutil.which("npx"):
        return ["npx", "-y", "clawhub"]
    return []


def build_common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--canonical", default=DEFAULT_CANONICAL, help=f"Canonical skills repository (default: {DEFAULT_CANONICAL})")
    parser.add_argument("--skillhub-bin", default=DEFAULT_SKILLHUB_BIN, help=f"SkillHub CLI binary (default: {DEFAULT_SKILLHUB_BIN})")
    parser.add_argument(
        "--clawhub-bin",
        default=DEFAULT_CLAWHUB_BIN,
        help='ClawHub CLI command for fallback: "auto" (default), "clawhub", or e.g. "npx -y clawhub"',
    )
    parser.add_argument("--no-fallback", action="store_true", help="Disable fallback to ClawHub when SkillHub fails or is unavailable")
    parser.add_argument("--agents", action="append", help="Comma-separated list of agent keys to target during linking")
    parser.add_argument("--all-agents", action="store_true", help="Link to all known agents instead of only detected ones")
    parser.add_argument("--force-links", action="store_true", help="Replace conflicting link targets when linking")
    parser.add_argument("--no-link", action="store_true", help="Skip the symlink step")
    parser.add_argument("--no-git", action="store_true", help="Skip git add/commit/push")
    parser.add_argument("--no-push", action="store_true", help="Commit locally but do not push")
    parser.add_argument("--git-remote", default=DEFAULT_GIT_REMOTE, help=f"Git remote to push to (default: {DEFAULT_GIT_REMOTE})")
    parser.add_argument("--commit-message", help="Custom git commit message")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands without making changes")
    return parser


def build_install_parser() -> argparse.ArgumentParser:
    parser = build_common_parser(
        "Install a skill into ~/.agents/skills. Prefer SkillHub first and fallback to ClawHub if needed; then relink and git commit/push."
    )
    parser.add_argument("slug", help="Skill slug to install")
    parser.add_argument("--force-install", action="store_true", help="Overwrite existing folder when supported by the source CLI")
    return parser


def build_upgrade_parser() -> argparse.ArgumentParser:
    parser = build_common_parser(
        "Upgrade installed skills inside ~/.agents/skills. Prefer SkillHub-managed entries, fallback to ClawHub-managed entries, then relink and git commit/push."
    )
    parser.add_argument("slug", nargs="?", help="Optional skill slug to upgrade. If omitted, upgrade all installed skills.")
    parser.add_argument("--all", action="store_true", help="Upgrade all installed skills (same as omitting slug)")
    parser.add_argument("--check-only", action="store_true", help="Only check available SkillHub upgrades without installing changes")
    parser.add_argument("--timeout", type=int, default=20, help="Timeout in seconds for SkillHub manifest fetch (default: 20)")
    parser.add_argument("--force-upgrade", action="store_true", help="Pass --force to ClawHub update when fallback is used")
    return parser


def build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillhub-canonical",
        description=(
            "Canonical SkillHub helper for ~/.agents/skills.\n\n"
            "Default usage is backward-compatible: `skillhub-canonical <slug>` installs a skill.\n"
            "Explicit subcommands are also supported: install / upgrade / update.\n"
            "SkillHub is preferred first; ClawHub is used as fallback when needed."
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
        "  skillhub-canonical install some-skill --no-fallback\n"
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


def maybe_link_skills(*, args: argparse.Namespace, canonical: Path, symlink_manager: Path, skills: List[str], all_skills: bool = False) -> None:
    if args.no_link:
        return
    if not all_skills and not skills:
        return
    cmd = build_link_cmd(
        symlink_manager=symlink_manager,
        agents=args.agents,
        all_agents=args.all_agents,
        force_links=args.force_links,
        skills=skills,
        all_skills=all_skills,
    )
    run_cmd(cmd, cwd=canonical, dry_run=args.dry_run)


def maybe_git_commit(*, args: argparse.Namespace, canonical: Path, tracked_paths: List[str], default_message: str) -> int:
    if args.no_git:
        return 0
    if not (canonical / ".git").exists() and not args.dry_run:
        print(f"warn: {canonical} is not a git repo; skip git steps", file=sys.stderr)
        return 0

    tracked_paths = unique_keep_order(tracked_paths)
    if not args.dry_run:
        tracked_paths = [p for p in tracked_paths if (canonical / p).exists()]
    if not tracked_paths:
        print("No tracked paths changed; skip git add/commit/push.")
        return 0

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


def build_skillhub_install_cmd(args: argparse.Namespace, canonical: Path) -> List[str]:
    cmd = [args.skillhub_bin, "--dir", str(canonical), "install", args.slug]
    if getattr(args, "force_install", False):
        cmd.append("--force")
    return cmd


def build_clawhub_install_cmd(args: argparse.Namespace, canonical: Path, clawhub_cmd: List[str]) -> List[str]:
    cmd = [*clawhub_cmd, "--workdir", str(canonical), "--dir", ".", "--no-input", "install", args.slug]
    if getattr(args, "force_install", False):
        cmd.append("--force")
    return cmd


def build_skillhub_upgrade_cmd(args: argparse.Namespace, canonical: Path, target_slug: Optional[str]) -> List[str]:
    cmd = [args.skillhub_bin, "--dir", str(canonical), "upgrade"]
    if args.check_only:
        cmd.append("--check-only")
    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])
    if target_slug:
        cmd.append(target_slug)
    return cmd


def build_clawhub_upgrade_cmd(
    args: argparse.Namespace,
    canonical: Path,
    clawhub_cmd: List[str],
    target_slug: Optional[str],
) -> List[str]:
    cmd = [*clawhub_cmd, "--workdir", str(canonical), "--dir", ".", "--no-input", "update"]
    if target_slug:
        cmd.append(target_slug)
    else:
        cmd.append("--all")
    if getattr(args, "force_upgrade", False):
        cmd.append("--force")
    return cmd


def run_install_mode(argv: List[str], script_dir: Path) -> int:
    args = build_install_parser().parse_args(argv)
    canonical = resolve_canonical(args)
    symlink_manager = resolve_symlink_manager(script_dir)

    used_source: Optional[str] = None
    skillhub_code = run_attempt(build_skillhub_install_cmd(args, canonical), dry_run=args.dry_run)
    if skillhub_code == 0:
        used_source = "skillhub"
    elif args.no_fallback:
        raise SystemExit(skillhub_code)
    else:
        clawhub_cmd = resolve_clawhub_cmd(args.clawhub_bin)
        if not clawhub_cmd:
            print("warn: SkillHub install failed and ClawHub fallback command is unavailable.", file=sys.stderr)
            raise SystemExit(skillhub_code)
        print(f"info: SkillHub install failed (exit={skillhub_code}); fallback to ClawHub: {sh(clawhub_cmd)}")
        clawhub_code = run_attempt(build_clawhub_install_cmd(args, canonical, clawhub_cmd), dry_run=args.dry_run)
        if clawhub_code != 0:
            raise SystemExit(clawhub_code)
        used_source = "clawhub-fallback"

    maybe_link_skills(args=args, canonical=canonical, symlink_manager=symlink_manager, skills=[args.slug])

    tracked_paths = [args.slug]
    if lockfile_path(canonical).exists() or args.dry_run:
        tracked_paths.append(LOCKFILE_NAME)
    if clawhub_lockfile_path(canonical).exists() or args.dry_run:
        tracked_paths.append(CLAWHUB_LOCKFILE_NAME)

    source_label = "via clawhub fallback" if used_source == "clawhub-fallback" else "via skillhub"
    return maybe_git_commit(
        args=args,
        canonical=canonical,
        tracked_paths=tracked_paths,
        default_message=f"feat(skills): install {args.slug} {source_label}",
    )


def run_upgrade_mode(argv: List[str], script_dir: Path) -> int:
    args = build_upgrade_parser().parse_args(argv)
    canonical = resolve_canonical(args)
    symlink_manager = resolve_symlink_manager(script_dir)

    if args.slug and args.all:
        raise SystemExit("Use either a slug or --all, not both.")

    target_slug = None if args.all else args.slug
    skillhub_before = load_skillhub_lock_slugs(canonical)
    clawhub_before = load_clawhub_lock_slugs(canonical)

    used_sources: List[str] = []

    if target_slug:
        skillhub_tracks = target_slug in skillhub_before
        clawhub_tracks = target_slug in clawhub_before

        if skillhub_tracks or not clawhub_tracks:
            code = run_attempt(build_skillhub_upgrade_cmd(args, canonical, target_slug), dry_run=args.dry_run)
            if code == 0:
                used_sources.append("skillhub")
            elif args.no_fallback:
                raise SystemExit(code)
            elif args.check_only:
                print("info: SkillHub check-only failed; ClawHub fallback skipped because ClawHub has no check-only mode.")
                raise SystemExit(code)
            else:
                clawhub_cmd = resolve_clawhub_cmd(args.clawhub_bin)
                if clawhub_tracks and clawhub_cmd:
                    print(f"info: SkillHub upgrade failed (exit={code}); fallback to ClawHub: {sh(clawhub_cmd)}")
                    fallback_code = run_attempt(
                        build_clawhub_upgrade_cmd(args, canonical, clawhub_cmd, target_slug),
                        dry_run=args.dry_run,
                    )
                    if fallback_code != 0:
                        raise SystemExit(fallback_code)
                    used_sources.append("clawhub-fallback")
                else:
                    raise SystemExit(code)
        elif clawhub_tracks:
            if args.check_only:
                print(f"info: {target_slug} is ClawHub-managed; ClawHub has no check-only mode, so nothing was changed.")
                return 0
            clawhub_cmd = resolve_clawhub_cmd(args.clawhub_bin)
            if not clawhub_cmd:
                raise SystemExit("ClawHub fallback command unavailable for upgrade")
            code = run_attempt(build_clawhub_upgrade_cmd(args, canonical, clawhub_cmd, target_slug), dry_run=args.dry_run)
            if code != 0:
                raise SystemExit(code)
            used_sources.append("clawhub")
    else:
        if not skillhub_before and not clawhub_before:
            print("No installed skills found in either SkillHub or ClawHub lockfiles.")
            return 0

        if skillhub_before:
            code = run_attempt(build_skillhub_upgrade_cmd(args, canonical, None), dry_run=args.dry_run)
            if code == 0:
                used_sources.append("skillhub")
            elif args.no_fallback:
                raise SystemExit(code)
            elif args.check_only:
                print("info: SkillHub check-only failed; ClawHub fallback skipped because ClawHub has no check-only mode.")
                raise SystemExit(code)
            else:
                print(f"warn: SkillHub bulk upgrade failed (exit={code}); will continue with ClawHub-managed skills if any.")

        if clawhub_before:
            if args.check_only:
                print("info: ClawHub-managed skills exist, but ClawHub has no check-only mode; skipped fallback check.")
            else:
                clawhub_cmd = resolve_clawhub_cmd(args.clawhub_bin)
                if not clawhub_cmd:
                    print("warn: ClawHub fallback command unavailable; skipped ClawHub-managed skill updates.", file=sys.stderr)
                else:
                    code = run_attempt(build_clawhub_upgrade_cmd(args, canonical, clawhub_cmd, None), dry_run=args.dry_run)
                    if code != 0:
                        raise SystemExit(code)
                    used_sources.append("clawhub")

    if args.check_only:
        return 0

    skillhub_after = load_skillhub_lock_slugs(canonical)
    clawhub_after = load_clawhub_lock_slugs(canonical)

    if target_slug:
        relink_skills = [target_slug]
    else:
        relink_skills = unique_keep_order([*skillhub_before, *clawhub_before, *skillhub_after, *clawhub_after])

    maybe_link_skills(args=args, canonical=canonical, symlink_manager=symlink_manager, skills=relink_skills)

    tracked_paths = [*relink_skills]
    if lockfile_path(canonical).exists() or args.dry_run:
        tracked_paths.append(LOCKFILE_NAME)
    if clawhub_lockfile_path(canonical).exists() or args.dry_run:
        tracked_paths.append(CLAWHUB_LOCKFILE_NAME)

    if target_slug:
        if any(src.startswith("clawhub") for src in used_sources) and not any(src == "skillhub" for src in used_sources):
            message = f"chore(skills): upgrade {target_slug} via clawhub"
        elif any(src.startswith("clawhub") for src in used_sources):
            message = f"chore(skills): upgrade {target_slug} via skillhub+clawhub"
        else:
            message = f"chore(skills): upgrade {target_slug} via skillhub"
    else:
        if used_sources == ["clawhub"]:
            message = "chore(skills): upgrade skills via clawhub"
        elif any(src.startswith("clawhub") for src in used_sources):
            message = "chore(skills): upgrade skills via skillhub+clawhub"
        else:
            message = "chore(skills): upgrade skills via skillhub"

    return maybe_git_commit(args=args, canonical=canonical, tracked_paths=tracked_paths, default_message=message)


def main(argv: List[str]) -> int:
    script_dir = Path(__file__).resolve().parent

    if not argv or argv[0] in {"-h", "--help"}:
        build_root_parser().print_help()
        return 0

    for idx, token in enumerate(argv):
        if token in {"install", "upgrade", "update"}:
            sub_argv = [*argv[:idx], *argv[idx + 1 :]]
            if token == "install":
                return run_install_mode(sub_argv, script_dir)
            return run_upgrade_mode(sub_argv, script_dir)

    # Backward-compatible default: treat argv as install mode without explicit subcommand.
    return run_install_mode(argv, script_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
