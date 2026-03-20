#!/usr/bin/env python3
"""
Manage symlinks from ~/.agents/skills to multiple agent skill directories.

Default behavior is non-destructive. Use --force to replace conflicts.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AgentConfig:
    key: str
    display: str
    global_skills_dir: Path
    detect_paths: Tuple[Path, ...]
    detect_cwd_paths: Tuple[Path, ...] = ()


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def build_agents(home: Path, cwd: Path) -> Dict[str, AgentConfig]:
    codex_home = _expand(os.environ.get("CODEX_HOME", str(home / ".codex")))

    def cfg(
        key: str,
        display: str,
        global_skills_dir: str,
        detect: List[str],
        detect_cwd: Optional[List[str]] = None,
    ) -> AgentConfig:
        detect_cwd = detect_cwd or []
        return AgentConfig(
            key=key,
            display=display,
            global_skills_dir=_expand(global_skills_dir),
            detect_paths=tuple(_expand(p) for p in detect),
            detect_cwd_paths=tuple((cwd / p).resolve() for p in detect_cwd),
        )

    return {
        "amp": cfg(
            "amp",
            "Amp",
            "~/.config/agents/skills",
            ["~/.config/amp"],
        ),
        "antigravity": cfg(
            "antigravity",
            "Antigravity",
            "~/.gemini/antigravity/global_skills",
            ["~/.gemini/antigravity"],
            [".agent"],
        ),
        "claude-code": cfg(
            "claude-code",
            "Claude Code",
            "~/.claude/skills",
            ["~/.claude"],
        ),
        "openclaw-workspace": cfg(
            "openclaw-workspace",
            "OpenClaw Workspace",
            "~/.openclaw/workspace/skills",
            ["~/.openclaw/workspace", "~/.openclaw/openclaw.json"],
        ),
        "clawdbot": cfg(
            "clawdbot",
            "Clawdbot",
            "~/.clawdbot/skills",
            ["~/.clawdbot"],
        ),
        "cline": cfg(
            "cline",
            "Cline",
            "~/.cline/skills",
            ["~/.cline"],
        ),
        "codebuddy": cfg(
            "codebuddy",
            "CodeBuddy",
            "~/.codebuddy/skills",
            ["~/.codebuddy"],
            [".codebuddy"],
        ),
        "codex": AgentConfig(
            key="codex",
            display="Codex",
            global_skills_dir=(codex_home / "skills").resolve(),
            detect_paths=(codex_home.resolve(), Path("/etc/codex")),
        ),
        "command-code": cfg(
            "command-code",
            "Command Code",
            "~/.commandcode/skills",
            ["~/.commandcode"],
        ),
        "continue": cfg(
            "continue",
            "Continue",
            "~/.continue/skills",
            ["~/.continue"],
            [".continue"],
        ),
        "crush": cfg(
            "crush",
            "Crush",
            "~/.config/crush/skills",
            ["~/.config/crush"],
        ),
        "cursor": cfg(
            "cursor",
            "Cursor",
            "~/.cursor/skills",
            ["~/.cursor"],
        ),
        "droid": cfg(
            "droid",
            "Droid",
            "~/.factory/skills",
            ["~/.factory"],
        ),
        "gemini-cli": cfg(
            "gemini-cli",
            "Gemini CLI",
            "~/.gemini/skills",
            ["~/.gemini"],
        ),
        "github-copilot": cfg(
            "github-copilot",
            "GitHub Copilot",
            "~/.copilot/skills",
            ["~/.copilot"],
            [".github"],
        ),
        "goose": cfg(
            "goose",
            "Goose",
            "~/.config/goose/skills",
            ["~/.config/goose"],
        ),
        "kilo": cfg(
            "kilo",
            "Kilo Code",
            "~/.kilocode/skills",
            ["~/.kilocode"],
        ),
        "kiro-cli": cfg(
            "kiro-cli",
            "Kiro CLI",
            "~/.kiro/skills",
            ["~/.kiro"],
        ),
        "mcpjam": cfg(
            "mcpjam",
            "MCPJam",
            "~/.mcpjam/skills",
            ["~/.mcpjam"],
        ),
        "mux": cfg(
            "mux",
            "Mux",
            "~/.mux/skills",
            ["~/.mux"],
        ),
        "opencode": cfg(
            "opencode",
            "OpenCode",
            "~/.config/opencode/skills",
            ["~/.config/opencode", "~/.claude/skills"],
        ),
        "openhands": cfg(
            "openhands",
            "OpenHands",
            "~/.openhands/skills",
            ["~/.openhands"],
        ),
        "pi": cfg(
            "pi",
            "Pi",
            "~/.pi/agent/skills",
            ["~/.pi/agent"],
        ),
        "qoder": cfg(
            "qoder",
            "Qoder",
            "~/.qoder/skills",
            ["~/.qoder"],
        ),
        "qwen-code": cfg(
            "qwen-code",
            "Qwen Code",
            "~/.qwen/skills",
            ["~/.qwen"],
        ),
        "roo": cfg(
            "roo",
            "Roo Code",
            "~/.roo/skills",
            ["~/.roo"],
        ),
        "trae": cfg(
            "trae",
            "Trae",
            "~/.trae/skills",
            ["~/.trae"],
        ),
        "windsurf": cfg(
            "windsurf",
            "Windsurf",
            "~/.codeium/windsurf/skills",
            ["~/.codeium/windsurf"],
        ),
        "zencoder": cfg(
            "zencoder",
            "Zencoder",
            "~/.zencoder/skills",
            ["~/.zencoder"],
        ),
        "neovate": cfg(
            "neovate",
            "Neovate",
            "~/.neovate/skills",
            ["~/.neovate"],
        ),
    }


def detect_installed_agents(agents: Dict[str, AgentConfig], all_agents: bool) -> List[str]:
    if all_agents:
        return list(agents.keys())

    installed = []
    for key, cfg in agents.items():
        detected = any(p.exists() for p in cfg.detect_paths) or any(
            p.exists() for p in cfg.detect_cwd_paths
        )
        if detected:
            installed.append(key)
    return installed


def canonical_skills(canonical_dir: Path) -> Dict[str, Path]:
    skills = {}
    if not canonical_dir.exists():
        return skills

    for entry in canonical_dir.iterdir():
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if skill_md.is_file():
            skills[entry.name] = entry.resolve()
    return skills


def filter_skills_by_prefix(
    skills: Dict[str, Path],
    include_prefixes: List[str],
    exclude_prefixes: List[str],
) -> Dict[str, Path]:
    filtered = skills
    if include_prefixes:
        filtered = {
            name: path
            for name, path in filtered.items()
            if any(name.startswith(prefix) for prefix in include_prefixes)
        }
    if exclude_prefixes:
        filtered = {
            name: path
            for name, path in filtered.items()
            if not any(name.startswith(prefix) for prefix in exclude_prefixes)
        }
    return filtered


def split_list(values: Optional[List[str]]) -> List[str]:
    if not values:
        return []
    result = []
    for v in values:
        for part in v.split(","):
            part = part.strip()
            if part:
                result.append(part)
    return result


def path_status(link_path: Path, canonical_path: Path) -> Tuple[str, Optional[Path]]:
    if os.path.lexists(link_path):
        if link_path.is_symlink():
            try:
                target = (link_path.parent / link_path.readlink()).resolve()
            except OSError:
                return "broken", None
            if target == canonical_path:
                return "linked", target
            return "wrong-link", target
        if link_path.is_dir():
            return "dir", None
        return "file", None
    return "missing", None


def ensure_symlink(
    canonical_path: Path, link_path: Path, force: bool, dry_run: bool
) -> Tuple[bool, str]:
    status, _ = path_status(link_path, canonical_path)
    if status == "linked":
        return True, "linked"
    if status in {"dir", "file", "wrong-link", "broken"} and not force:
        return False, f"conflict:{status}"

    if dry_run:
        return True, f"create:{status}"

    if os.path.lexists(link_path):
        if link_path.is_symlink() or link_path.is_file():
            link_path.unlink()
        elif link_path.is_dir():
            shutil.rmtree(link_path)
        else:
            link_path.unlink(missing_ok=True)

    link_path.parent.mkdir(parents=True, exist_ok=True)
    rel_target = os.path.relpath(canonical_path, link_path.parent)
    link_path.symlink_to(rel_target)
    return True, "linked"


def format_agent(cfg: AgentConfig) -> str:
    return f"{cfg.display} ({cfg.key})"


def output_mode(args: argparse.Namespace) -> str:
    if args.json and args.json_lines:
        return "invalid"
    if args.json_lines:
        return "jsonl"
    if args.json:
        return "json"
    return "text"


def emit_error(message: str, mode: str, extra: Optional[Dict[str, object]] = None) -> None:
    payload = {"error": message}
    if extra:
        payload.update(extra)
    if mode == "jsonl" or mode == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(message)


def run_status(
    args: argparse.Namespace, agents: Dict[str, AgentConfig], selected_agents: List[str]
) -> int:
    mode = output_mode(args)
    if mode == "invalid":
        emit_error("Use only one of --json or --json-lines.", "json")
        return 1

    canonical_dir = _expand(args.canonical)
    skills = canonical_skills(canonical_dir)
    include_prefixes = split_list(args.prefix)
    exclude_prefixes = split_list(args.exclude_prefix)
    skills = filter_skills_by_prefix(skills, include_prefixes, exclude_prefixes)
    if args.skill:
        requested = split_list(args.skill)
        skills = {k: v for k, v in skills.items() if k in requested}

    if not skills:
        emit_error(
            f"No skills found under {canonical_dir}",
            mode,
            {
                "canonical": str(canonical_dir),
                "includePrefixes": include_prefixes,
                "excludePrefixes": exclude_prefixes,
            },
        )
        return 1

    result = {
        "canonical": str(canonical_dir),
        "includePrefixes": include_prefixes,
        "excludePrefixes": exclude_prefixes,
        "agents": [],
    }

    for key in selected_agents:
        cfg = agents[key]
        counts = {
            "linked": 0,
            "missing": 0,
            "wrong-link": 0,
            "broken": 0,
            "dir": 0,
            "file": 0,
        }
        skill_entries = []
        for skill_name, canonical_path in sorted(skills.items()):
            link_path = cfg.global_skills_dir / skill_name
            status, target = path_status(link_path, canonical_path)
            counts[status] = counts.get(status, 0) + 1
            if args.verbose:
                entry = {"name": skill_name, "status": status}
                if status == "wrong-link" and target:
                    entry["target"] = str(target)
                skill_entries.append(entry)

        if mode == "json":
            agent_entry = {
                "key": cfg.key,
                "display": cfg.display,
                "skillsDir": str(cfg.global_skills_dir),
                "summary": {k: v for k, v in counts.items() if v},
            }
            if args.verbose:
                agent_entry["skills"] = skill_entries
            result["agents"].append(agent_entry)
        elif mode == "jsonl":
            agent_entry = {
                "canonical": str(canonical_dir),
                "includePrefixes": include_prefixes,
                "excludePrefixes": exclude_prefixes,
                "key": cfg.key,
                "display": cfg.display,
                "skillsDir": str(cfg.global_skills_dir),
                "summary": {k: v for k, v in counts.items() if v},
            }
            if args.verbose:
                agent_entry["skills"] = skill_entries
            print(json.dumps(agent_entry, ensure_ascii=False))
        else:
            print(f"\n[{format_agent(cfg)}]")
            if args.verbose:
                for entry in skill_entries:
                    if entry["status"] == "wrong-link" and "target" in entry:
                        print(f"- {entry['name']}: wrong-link -> {entry['target']}")
                    else:
                        print(f"- {entry['name']}: {entry['status']}")
            summary = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
            print(f"summary: {summary}")

    if mode == "json":
        print(json.dumps(result, ensure_ascii=False))

    return 0


def run_link(
    args: argparse.Namespace,
    agents: Dict[str, AgentConfig],
    selected_agents: List[str],
    force: bool,
) -> int:
    mode = output_mode(args)
    if mode == "invalid":
        emit_error("Use only one of --json or --json-lines.", "json")
        return 1

    canonical_dir = _expand(args.canonical)
    skills = canonical_skills(canonical_dir)
    include_prefixes = split_list(args.prefix)
    exclude_prefixes = split_list(args.exclude_prefix)
    skills = filter_skills_by_prefix(skills, include_prefixes, exclude_prefixes)

    if args.all_skills:
        selected_skills = list(skills.keys())
    else:
        selected_skills = split_list(args.skill)

    if not selected_skills:
        emit_error(
            "No skills selected. Use --skill <name> or --all-skills.",
            mode,
            {
                "canonical": str(canonical_dir),
                "includePrefixes": include_prefixes,
                "excludePrefixes": exclude_prefixes,
            },
        )
        return 1

    missing = [s for s in selected_skills if s not in skills]
    if missing:
        emit_error(
            f"Skills not found in {canonical_dir}: {', '.join(missing)}",
            mode,
            {
                "canonical": str(canonical_dir),
                "missing": missing,
                "includePrefixes": include_prefixes,
                "excludePrefixes": exclude_prefixes,
            },
        )
        return 1

    result = {
        "canonical": str(canonical_dir),
        "includePrefixes": include_prefixes,
        "excludePrefixes": exclude_prefixes,
        "dryRun": bool(args.dry_run),
        "force": bool(force),
        "agents": [],
    }
    exit_code = 0
    for key in selected_agents:
        cfg = agents[key]
        agent_results = []
        for skill_name in selected_skills:
            canonical_path = skills[skill_name]
            link_path = cfg.global_skills_dir / skill_name
            ok, msg = ensure_symlink(
                canonical_path, link_path, force=force, dry_run=args.dry_run
            )
            action = "dry-run" if args.dry_run else "apply"
            agent_results.append(
                {
                    "name": skill_name,
                    "ok": ok,
                    "action": action,
                    "message": msg,
                }
            )
            if not ok:
                exit_code = 2

        if mode == "json":
            result["agents"].append(
                {
                    "key": cfg.key,
                    "display": cfg.display,
                    "skillsDir": str(cfg.global_skills_dir),
                    "results": agent_results,
                }
            )
        elif mode == "jsonl":
            print(
                json.dumps(
                    {
                        "canonical": str(canonical_dir),
                        "includePrefixes": include_prefixes,
                        "excludePrefixes": exclude_prefixes,
                        "dryRun": bool(args.dry_run),
                        "force": bool(force),
                        "key": cfg.key,
                        "display": cfg.display,
                        "skillsDir": str(cfg.global_skills_dir),
                        "results": agent_results,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"\n[{format_agent(cfg)}]")
            for entry in agent_results:
                prefix = "OK" if entry["ok"] else "SKIP"
                print(
                    f"- {entry['name']}: {prefix} ({entry['action']}, {entry['message']})"
                )

    if mode == "json":
        print(json.dumps(result, ensure_ascii=False))
    return exit_code


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage symlinks from ~/.agents/skills to multiple agent skill directories."
    )
    parser.add_argument(
        "--canonical",
        default="~/.agents/skills",
        help="Canonical skills directory (default: ~/.agents/skills)",
    )
    parser.add_argument(
        "--prefix",
        action="append",
        help="Only include skills with this prefix",
    )
    parser.add_argument(
        "--exclude-prefix",
        action="append",
        help="Exclude skills with this prefix",
    )
    parser.add_argument(
        "--agents",
        action="append",
        help="Comma-separated list of agent keys to target",
    )
    parser.add_argument(
        "--all-agents",
        action="store_true",
        help="Target all known agents (ignore detection)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--json-lines",
        action="store_true",
        help="Output one JSON object per agent",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show symlink status")
    status.add_argument("--skill", action="append", help="Limit to specific skill(s)")
    status.add_argument("--verbose", action="store_true", help="Show per-skill status")

    link = subparsers.add_parser("link", help="Create symlinks")
    link.add_argument("--skill", action="append", help="Skill name (repeatable)")
    link.add_argument("--all-skills", action="store_true", help="Link all skills")
    link.add_argument("--dry-run", action="store_true", help="Show actions without changes")
    link.add_argument("--force", action="store_true", help="Replace conflicting paths")

    fix = subparsers.add_parser("fix", help="Force repair of symlinks")
    fix.add_argument("--skill", action="append", help="Skill name (repeatable)")
    fix.add_argument("--all-skills", action="store_true", help="Fix all skills")
    fix.add_argument("--dry-run", action="store_true", help="Show actions without changes")

    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    home = Path.home()
    cwd = Path.cwd()
    agents = build_agents(home, cwd)

    selected = split_list(args.agents)
    if selected:
        unknown = [a for a in selected if a not in agents]
        if unknown:
            mode = output_mode(args)
            if mode == "invalid":
                emit_error("Use only one of --json or --json-lines.", "json")
                return 1
            emit_error(
                "Unknown agents",
                mode,
                {
                    "unknown": unknown,
                    "known": sorted(agents.keys()),
                },
            )
            return 1
        selected_agents = selected
    else:
        selected_agents = detect_installed_agents(agents, all_agents=args.all_agents)

    if not selected_agents:
        mode = output_mode(args)
        if mode == "invalid":
            emit_error("Use only one of --json or --json-lines.", "json")
            return 1
        emit_error("No agents detected. Use --all-agents or --agents.", mode)
        return 1

    if args.command == "status":
        return run_status(args, agents, selected_agents)

    if args.command == "link":
        return run_link(args, agents, selected_agents, force=args.force)

    if args.command == "fix":
        return run_link(args, agents, selected_agents, force=True)

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
