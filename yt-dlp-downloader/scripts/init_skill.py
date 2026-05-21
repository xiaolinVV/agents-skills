#!/usr/bin/env python3
"""Initialize the yt-dlp-downloader skill after copying it to a new machine."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


SKILL_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = SKILL_ROOT / "agent-harness"
CLI_NAME = "cli-anything-yt-dlp"


def run_command(cmd: Sequence[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(arg) for arg in cmd], capture_output=True, text=True, errors="replace", env=env)


def tail_text(text: str, max_chars: int = 4000) -> str:
    stripped = text.strip()
    return stripped[-max_chars:] if len(stripped) > max_chars else stripped


def in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def user_scripts_dir() -> Path:
    suffix = "Scripts" if os.name == "nt" else "bin"
    return Path(site.USER_BASE) / suffix


def command_step(name: str, cmd: Sequence[str], dry_run: bool, env: dict[str, str] | None = None) -> dict[str, Any]:
    step = {"name": name, "command": [str(arg) for arg in cmd], "dry_run": dry_run}
    if dry_run:
        step.update({"ok": True, "skipped": True, "returncode": None, "stdout_tail": "", "stderr_tail": ""})
        return step
    proc = run_command(cmd, env=env)
    step.update(
        {
            "ok": proc.returncode == 0,
            "skipped": False,
            "returncode": proc.returncode,
            "stdout_tail": tail_text(proc.stdout),
            "stderr_tail": tail_text(proc.stderr),
        }
    )
    return step


def harness_install_commands() -> list[list[str]]:
    base = [sys.executable, "-m", "pip", "install"]
    if in_virtualenv():
        return [[*base, "-e", str(HARNESS_ROOT)]]
    return [
        [*base, "--user", "-e", str(HARNESS_ROOT)],
        [*base, "--user", "--break-system-packages", "-e", str(HARNESS_ROOT)],
    ]


def install_harness(dry_run: bool) -> dict[str, Any]:
    commands = harness_install_commands()
    first = command_step("install cli-anything harness", commands[0], dry_run)
    if dry_run or first["ok"]:
        first["attempts"] = [first["command"]]
        return first

    stderr = str(first.get("stderr_tail") or "").lower()
    if "externally-managed-environment" not in stderr or len(commands) == 1:
        first["attempts"] = [first["command"]]
        return first

    retry = command_step("install cli-anything harness", commands[1], dry_run=False)
    retry["attempts"] = [first["command"], retry["command"]]
    retry["first_error_tail"] = first.get("stderr_tail")
    return retry


def module_env() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(HARNESS_ROOT) if not current else f"{HARNESS_ROOT}{os.pathsep}{current}"
    return env


def module_command(*args: str) -> list[str]:
    return [sys.executable, "-m", "cli_anything.yt_dlp.yt_dlp_cli", *args]


def check_cli_command(dry_run: bool) -> dict[str, Any]:
    script_path = shutil.which(CLI_NAME)
    user_bin_candidate = user_scripts_dir() / CLI_NAME
    available = script_path is not None
    if not available and user_bin_candidate.exists():
        script_path = str(user_bin_candidate)
    return {
        "name": "check cli command",
        "ok": available,
        "dry_run": dry_run,
        "skipped": False,
        "command": ["command", "-v", CLI_NAME],
        "returncode": 0 if available else 1,
        "stdout_tail": script_path or "",
        "stderr_tail": "" if available else f"{CLI_NAME} is not on PATH",
        "path": script_path,
        "user_scripts_dir": str(user_scripts_dir()),
        "path_ready": available,
    }


def run_status(dry_run: bool) -> tuple[dict[str, Any], dict[str, Any] | None]:
    cmd = module_command("--json", "system", "status")
    step = command_step("system status", cmd, dry_run, env=module_env())
    if dry_run or not step["ok"]:
        return step, None
    try:
        return step, json.loads(step["stdout_tail"])
    except json.JSONDecodeError:
        step["ok"] = False
        step["stderr_tail"] = "system status returned invalid JSON"
        return step, None


def maybe_bootstrap_yt_dlp(dry_run: bool, enabled: bool, status_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not enabled:
        return None
    yt_dlp_available = bool(((status_payload or {}).get("dependencies") or {}).get("yt_dlp", {}).get("available"))
    if yt_dlp_available:
        return {"name": "bootstrap yt-dlp", "ok": True, "skipped": True, "dry_run": dry_run, "reason": "yt-dlp already available"}
    return command_step("bootstrap yt-dlp", module_command("--json", "system", "bootstrap", "--channel", "stable"), dry_run, env=module_env())


def next_actions(payload: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if payload["status"] == "dry_run":
        actions.append("Run python3 scripts/init_skill.py --json to install the harness and check the host.")
        actions.append("Add --bootstrap-yt-dlp if the target host should install yt-dlp automatically.")
        return actions

    cli = payload.get("cli") or {}
    if not cli.get("path_ready"):
        actions.append(f"Add {cli.get('user_scripts_dir')} to PATH or call the CLI through python3 -m cli_anything.yt_dlp.yt_dlp_cli.")

    status_payload = payload.get("system_status") or {}
    deps = status_payload.get("dependencies") or {}
    if not (deps.get("yt_dlp") or {}).get("available"):
        actions.append("Run python3 scripts/init_skill.py --json --bootstrap-yt-dlp to install yt-dlp.")
    if not (deps.get("ffmpeg") or {}).get("available"):
        hint = status_payload.get("ffmpeg_install_hint") or "install ffmpeg with the system package manager"
        actions.append(hint)
    if not actions:
        actions.append("The skill is initialized. Use cli-anything-yt-dlp --json system status to verify later.")
    return actions


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    install_step = install_harness(args.dry_run or args.skip_harness_install)
    if args.skip_harness_install:
        install_step["skipped"] = True
        install_step["reason"] = "--skip-harness-install"
    steps.append(install_step)

    cli_step = check_cli_command(args.dry_run)
    steps.append(cli_step)

    status_step: dict[str, Any]
    status_payload: dict[str, Any] | None
    if not args.dry_run and not install_step["ok"]:
        status_step = {
            "name": "system status",
            "ok": False,
            "skipped": True,
            "dry_run": False,
            "reason": "harness installation failed",
            "command": module_command("--json", "system", "status"),
        }
        status_payload = None
    else:
        status_step, status_payload = run_status(args.dry_run)
    steps.append(status_step)

    bootstrap_step = maybe_bootstrap_yt_dlp(args.dry_run, args.bootstrap_yt_dlp, status_payload)
    if bootstrap_step is not None:
        steps.append(bootstrap_step)
        if not args.dry_run and bootstrap_step.get("ok") and not bootstrap_step.get("skipped"):
            status_step, status_payload = run_status(False)
            status_step["name"] = "system status after bootstrap"
            steps.append(status_step)

    ready = bool((status_payload or {}).get("ready_for_download"))
    status = "dry_run" if args.dry_run else "success" if ready and install_step["ok"] else "partial_error" if install_step["ok"] else "error"
    payload = {
        "command": "init_skill",
        "status": status,
        "skill_root": str(SKILL_ROOT),
        "harness_root": str(HARNESS_ROOT),
        "python": sys.executable,
        "steps": steps,
        "cli": {
            "name": CLI_NAME,
            "path": cli_step.get("path"),
            "path_ready": cli_step.get("path_ready"),
            "user_scripts_dir": cli_step.get("user_scripts_dir"),
            "module_command": module_command(),
        },
        "system_status": status_payload,
        "ready_for_download": ready,
    }
    payload["next_actions"] = next_actions(payload)
    return payload


def print_human(payload: dict[str, Any]) -> None:
    print(f"yt-dlp-downloader init: {payload['status']}")
    for step in payload["steps"]:
        label = "ok" if step.get("ok") else "failed"
        if step.get("skipped"):
            label = "skipped"
        print(f"- {step['name']}: {label}")
        if step.get("stderr_tail") and not step.get("ok"):
            print(f"  {step['stderr_tail']}")
    print("next actions:")
    for action in payload["next_actions"]:
        print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize yt-dlp-downloader after copying the skill to a host.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without changing the host.")
    parser.add_argument("--skip-harness-install", action="store_true", help="Skip pip install -e for the harness.")
    parser.add_argument("--bootstrap-yt-dlp", action="store_true", help="Install yt-dlp if system status reports it missing.")
    args = parser.parse_args()

    payload = build_payload(args)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print_human(payload)
    return 0 if payload["status"] in {"success", "dry_run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
