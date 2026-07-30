#!/usr/bin/env python3
"""Rewrite remotes for jeecg multi-repo workspaces.

Supports two source modes:
- framework-source: update origin + upstream
- user-source: keep origin, update upstream

Default git transport is SSH for Gitee.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class RepoSpec:
    local_dir: str
    upstream_repo: str


@dataclass
class RepoResult:
    local_dir: str
    path: str
    origin_url: str
    upstream_url: str
    changed: bool
    pushed: bool
    upstream_verified: bool
    success: bool
    message: str


DEFAULT_REPOS = [
    RepoSpec("jeecg-boot", "jeecg-boot"),
    RepoSpec("ant-design-vue-jeecg", "ant-design-vue-jeecg"),
    RepoSpec("docs", "docs"),
    RepoSpec("_bmad", "bmad"),
    RepoSpec("_bmad-output", "bmad-output"),
]

OPTIONAL_REPOS = {
    "uniapp": RepoSpec("jeecg-uniapp", "jeecg-uniapp"),
    "openspec": RepoSpec("openspec", "openspec"),
}


def run_git(repo_path: Path, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    return subprocess.run(
        cmd,
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=check,
    )


def get_remote_url(repo_path: Path, name: str) -> Optional[str]:
    proc = run_git(repo_path, ["remote", "get-url", name], check=False)
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def current_branch(repo_path: Path) -> str:
    proc = run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
    branch = proc.stdout.strip()
    if proc.returncode != 0 or branch in {"", "HEAD"}:
        raise RuntimeError("Cannot determine current branch (detached HEAD?)")
    return branch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument(
        "--mode",
        choices=["framework-source", "user-source"],
        default="framework-source",
        help="framework-source updates origin+upstream; user-source keeps origin and only updates upstream",
    )
    parser.add_argument("--org", help="Target gitee organization for origin URL updates")
    parser.add_argument(
        "--origin-strategy",
        choices=["update", "keep"],
        help="Override origin behavior. Defaults: framework-source=update, user-source=keep",
    )
    parser.add_argument(
        "--git-transport",
        choices=["ssh", "https"],
        default="ssh",
        help="Remote URL transport. Default is ssh.",
    )
    parser.add_argument(
        "--git-host",
        default="gitee.com",
        help="Git host for SSH URL construction, e.g. gitee.com",
    )
    parser.add_argument(
        "--repo-host",
        default="https://gitee.com",
        help="Base URL for HTTPS transport (kept for compatibility)",
    )
    parser.add_argument("--upstream-org", default="jeecg-boot_3")
    parser.add_argument("--include-uniapp", action="store_true")
    parser.add_argument("--include-openspec", action="store_true")
    parser.add_argument("--verify-upstream-ls-remote", action="store_true")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push current branch to origin (framework-source only; ignored in user-source)",
    )
    parser.add_argument("--branch", help="Explicit branch name for push")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    args = parser.parse_args()

    if args.origin_strategy is None:
        args.origin_strategy = "update" if args.mode == "framework-source" else "keep"

    if args.origin_strategy == "update" and not args.org:
        parser.error("--org is required when origin strategy is 'update'")

    if args.mode == "user-source" and args.push:
        print(
            "warning: --push is ignored in user-source mode; final step must not push",
            file=sys.stderr,
        )
        args.push = False

    return args


def repo_specs(args: argparse.Namespace) -> List[RepoSpec]:
    repos = list(DEFAULT_REPOS)
    if args.include_uniapp:
        repos.append(OPTIONAL_REPOS["uniapp"])
    if args.include_openspec:
        repos.append(OPTIONAL_REPOS["openspec"])
    return repos


def format_remote_url(owner: str, repo: str, args: argparse.Namespace) -> str:
    if args.git_transport == "ssh":
        return f"git@{args.git_host}:{owner}/{repo}.git"

    base = args.repo_host.rstrip("/")
    return f"{base}/{owner}/{repo}.git"


def ensure_remote(repo_path: Path, name: str, target_url: str, dry_run: bool) -> tuple[bool, str]:
    existing = get_remote_url(repo_path, name)
    if existing == target_url:
        return False, "unchanged"

    if dry_run:
        action = "set-url" if existing else "add"
        return True, f"would {action} {name}"

    if existing:
        proc = run_git(repo_path, ["remote", "set-url", name, target_url], check=False)
    else:
        proc = run_git(repo_path, ["remote", "add", name, target_url], check=False)

    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"failed to update remote {name}: {stderr}")

    return True, "updated"


def verify_upstream(repo_path: Path, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "would run git ls-remote upstream"

    proc = run_git(repo_path, ["ls-remote", "upstream"], check=False)
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout).strip()
        return False, stderr or "git ls-remote upstream failed"
    return True, "ok"


def process_repo(root: Path, spec: RepoSpec, args: argparse.Namespace) -> RepoResult:
    repo_path = (root / spec.local_dir).resolve()
    upstream_url = format_remote_url(args.upstream_org, spec.upstream_repo, args)

    if not repo_path.is_dir():
        return RepoResult(
            local_dir=spec.local_dir,
            path=str(repo_path),
            origin_url="",
            upstream_url=upstream_url,
            changed=False,
            pushed=False,
            upstream_verified=False,
            success=False,
            message="local directory missing",
        )

    if not (repo_path / ".git").exists():
        return RepoResult(
            local_dir=spec.local_dir,
            path=str(repo_path),
            origin_url="",
            upstream_url=upstream_url,
            changed=False,
            pushed=False,
            upstream_verified=False,
            success=False,
            message="not a git repository",
        )

    try:
        origin_changed = False
        upstream_changed = False
        verify_msg = "skipped"
        push_msg = "push skipped: not requested"

        current_origin = get_remote_url(repo_path, "origin")

        if args.origin_strategy == "update":
            assert args.org is not None
            target_origin = format_remote_url(args.org, spec.upstream_repo, args)
            origin_changed, _ = ensure_remote(repo_path, "origin", target_origin, args.dry_run)
            final_origin = target_origin
        else:
            final_origin = current_origin or ""
            if not final_origin:
                raise RuntimeError("origin remote missing while origin strategy is keep")

        upstream_changed, _ = ensure_remote(repo_path, "upstream", upstream_url, args.dry_run)

        if args.verify_upstream_ls_remote:
            verify_ok, verify_msg = verify_upstream(repo_path, args.dry_run)
            if not verify_ok:
                raise RuntimeError(f"upstream verify failed: {verify_msg}")

        pushed = False
        if args.push:
            if args.dry_run:
                pushed = True
                push_msg = "push skipped: dry-run"
            else:
                branch = args.branch or current_branch(repo_path)
                proc = run_git(repo_path, ["push", "-u", "origin", branch], check=False)
                if proc.returncode != 0:
                    stderr = (proc.stderr or proc.stdout).strip()
                    raise RuntimeError(f"git push failed: {stderr}")
                pushed = True
                push_msg = "push ok"
        elif args.mode == "user-source":
            push_msg = "push skipped: user-source disabled"

        changed = origin_changed or upstream_changed
        detail_parts = ["ok", push_msg]
        if args.verify_upstream_ls_remote:
            detail_parts.insert(1, f"upstream verify: {verify_msg}")
        detail = ", ".join(detail_parts)

        return RepoResult(
            local_dir=spec.local_dir,
            path=str(repo_path),
            origin_url=final_origin,
            upstream_url=upstream_url,
            changed=changed,
            pushed=pushed,
            upstream_verified=args.verify_upstream_ls_remote,
            success=True,
            message=detail,
        )
    except Exception as exc:  # noqa: BLE001
        return RepoResult(
            local_dir=spec.local_dir,
            path=str(repo_path),
            origin_url=get_remote_url(repo_path, "origin") or "",
            upstream_url=upstream_url,
            changed=False,
            pushed=False,
            upstream_verified=False,
            success=False,
            message=str(exc),
        )


def print_plain(results: List[RepoResult]) -> None:
    for item in results:
        status = "OK" if item.success else "FAIL"
        print(f"[{status}] {item.local_dir}")
        print(f"  path: {item.path}")
        print(f"  origin: {item.origin_url}")
        print(f"  upstream: {item.upstream_url}")
        print(f"  changed: {item.changed}")
        print(f"  pushed: {item.pushed}")
        print(f"  upstream_verified: {item.upstream_verified}")
        print(f"  message: {item.message}")


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).expanduser().resolve()
    results = [process_repo(root, spec, args) for spec in repo_specs(args)]

    if args.json:
        payload = {
            "workspace_root": str(root),
            "mode": args.mode,
            "origin_strategy": args.origin_strategy,
            "org": args.org,
            "upstream_org": args.upstream_org,
            "git_transport": args.git_transport,
            "git_host": args.git_host,
            "verify_upstream_ls_remote": args.verify_upstream_ls_remote,
            "dry_run": args.dry_run,
            "results": [asdict(item) for item in results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_plain(results)

    return 1 if any(not item.success for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
