#!/usr/bin/env python3
"""Git quick sync helper for single repos and multi-repo workspaces."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc"}
DOC_NAMES = {"readme", "changelog", "license", "notice", "contributing"}
GENERIC_SCOPE_PARTS = {
    "src",
    "lib",
    "app",
    "apps",
    "server",
    "client",
    "main",
    "test",
    "tests",
    "docs",
    "doc",
    "pkg",
    "packages",
    "module",
    "modules",
    "api",
    "config",
    "configs",
}
CONFLICT_SENTINELS = [
    "MERGE_HEAD",
    "REBASE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
]
AUTO_STASH_MESSAGE = "git-quick-sync:auto-stash-before-pull"
BMAD_MARKER_DIRS = ("_bmad", "_bmad-output")
BMAD_PROJECT_CONTEXT = Path("_bmad-output/project-context.md")
BMAD_REASON_LABELS = {
    "workspace_bmad_dirs": "检测到 BMAD 工作区目录",
    "project_context_rules": "命中 BMAD project-context Git/Story 规则",
    "branch_story_id": "分支名提取到 story-id",
}


class GitCommandError(RuntimeError):
    def __init__(self, repo: Path, args: Sequence[str], returncode: int, stdout: str, stderr: str):
        self.repo = repo
        self.args = list(args)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        cmd_text = "git -C {} {}".format(repo, " ".join(args))
        super().__init__(f"Command failed ({returncode}): {cmd_text}\n{stderr.strip()}")


def run_git(repo: Path, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", "-C", str(repo), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise GitCommandError(repo, args, proc.returncode, proc.stdout, proc.stderr)
    return proc


def is_git_repo(path: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def to_repo_root(path: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return path.resolve()
    return Path(proc.stdout.strip()).resolve()


def discover_repos(root: Path, max_depth: int) -> List[Path]:
    root = root.resolve()
    found: List[Path] = []
    seen = set()

    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        rel_parts = current_path.relative_to(root).parts
        if len(rel_parts) > max_depth:
            dirs[:] = []
            continue

        has_git_dir = ".git" in dirs
        has_git_file = ".git" in files
        if has_git_dir or has_git_file:
            repo_root = current_path.resolve()
            key = str(repo_root)
            if key not in seen and is_git_repo(repo_root):
                seen.add(key)
                found.append(to_repo_root(repo_root))
            # Skip descending inside an already discovered repo.
            dirs[:] = []
            continue

        if ".git" in dirs:
            dirs.remove(".git")

    deduped = sorted({str(repo) for repo in found})
    return [Path(path) for path in deduped]


def parse_status_counts(porcelain_lines: Sequence[str]) -> Dict[str, int]:
    counts = {"modified": 0, "deleted": 0, "untracked": 0, "staged": 0}
    for line in porcelain_lines:
        if not line:
            continue
        status = line[:2]
        if status == "??":
            counts["untracked"] += 1
            continue

        if "M" in status:
            counts["modified"] += 1
        if "D" in status:
            counts["deleted"] += 1
        if status[0] not in {" ", "?"}:
            counts["staged"] += 1
    return counts


def get_branch(repo: Path) -> str:
    proc = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    return proc.stdout.strip()


def get_upstream(repo: Path) -> Optional[str]:
    proc = run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def get_repo_status(repo: Path) -> Dict[str, object]:
    repo = to_repo_root(repo)
    porcelain = run_git(repo, ["status", "--porcelain"]).stdout.splitlines()
    counts = parse_status_counts(porcelain)
    branch = get_branch(repo)
    upstream = get_upstream(repo)
    bmad_context = detect_bmad_context(repo, branch)
    return {
        "repo_path": str(repo),
        "repo_name": repo.name,
        "branch": branch,
        "upstream": upstream,
        "has_upstream": upstream is not None,
        "dirty": bool(porcelain),
        "counts": counts,
        **bmad_context,
    }


def find_in_progress_states(repo: Path) -> List[str]:
    states: List[str] = []
    for sentinel in CONFLICT_SENTINELS:
        proc = run_git(repo, ["rev-parse", "--git-path", sentinel])
        sentinel_path = Path(proc.stdout.strip())
        if sentinel_path.exists():
            states.append(sentinel)
    return states


def has_unresolved_conflicts(repo: Path) -> bool:
    conflicts = run_git(repo, ["diff", "--name-only", "--diff-filter=U"]).stdout.strip()
    return bool(conflicts)


def assert_clean_git_state(repo: Path, action: str) -> None:
    states = find_in_progress_states(repo)
    if states:
        raise RuntimeError(f"仓库存在未完成的 Git 状态: {', '.join(states)}，请先处理后再{action}")

    if has_unresolved_conflicts(repo):
        raise RuntimeError(f"仓库存在未解决冲突，请先处理后再{action}")


def assert_clean_git_state_for_commit(repo: Path) -> None:
    assert_clean_git_state(repo, "提交")


def assert_clean_git_state_for_pull(repo: Path) -> None:
    assert_clean_git_state(repo, "拉取")


def is_repo_dirty(repo: Path) -> bool:
    porcelain = run_git(repo, ["status", "--porcelain"]).stdout.strip()
    return bool(porcelain)


def remote_exists(repo: Path, remote: str) -> bool:
    proc = run_git(repo, ["remote", "get-url", remote], check=False)
    return proc.returncode == 0


def parse_upstream_ref(upstream: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not upstream:
        return (None, None)

    if "/" not in upstream:
        return (upstream, None)

    remote, branch = upstream.split("/", 1)
    return (remote or None, branch or None)


def git_error_text(proc: subprocess.CompletedProcess, default: str) -> str:
    stderr = proc.stderr.strip()
    stdout = proc.stdout.strip()
    return stderr or stdout or default


def read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return ""


def find_bmad_workspace_root(repo: Path) -> Optional[Path]:
    resolved_repo = repo.resolve()
    for current in (resolved_repo, *resolved_repo.parents):
        if any((current / marker).exists() for marker in BMAD_MARKER_DIRS):
            return current
    return None


def project_context_has_bmad_rules(project_context_path: Path) -> bool:
    content = read_text_if_exists(project_context_path)
    if not content:
        return False

    has_bmad_section = "BMAD" in content or "BMad" in content or "Story Execution Rules" in content
    has_branch_rule = "分支命名" in content and "story-id" in content.lower()
    has_commit_rule = "提交信息" in content and "scope" in content.lower()
    return has_bmad_section and has_branch_rule and has_commit_rule


def extract_story_id_from_branch(branch: str) -> Optional[str]:
    branch = branch.strip()
    if not branch:
        return None

    candidates = [branch]
    if "/" in branch:
        candidates.insert(0, branch.split("/", 1)[1])

    patterns = [
        r"((?:story|task|epic)-\d+(?:-(?:story|task|epic)-\d+)*)",
        r"\b([A-Z]+-\d+)\b",
    ]
    for candidate in candidates:
        for pattern in patterns:
            match = re.search(pattern, candidate, re.IGNORECASE)
            if not match:
                continue
            story_id = match.group(1)
            if story_id.lower().startswith(("story", "task", "epic")):
                return story_id.lower()
            return story_id
    return None


def detect_bmad_context(repo: Path, branch: str) -> Dict[str, object]:
    repo = to_repo_root(repo)
    workspace_root = find_bmad_workspace_root(repo)
    project_context_path: Optional[Path] = None
    reasons: List[str] = []

    if workspace_root is not None:
        reasons.append("workspace_bmad_dirs")
        candidate = workspace_root / BMAD_PROJECT_CONTEXT
        if candidate.exists():
            project_context_path = candidate
            if project_context_has_bmad_rules(candidate):
                reasons.append("project_context_rules")

    story_id = extract_story_id_from_branch(branch)
    if story_id:
        reasons.append("branch_story_id")

    unique_reasons: List[str] = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)

    bmad_detected = workspace_root is not None and (
        "project_context_rules" in unique_reasons or "branch_story_id" in unique_reasons
    )
    commit_mode = "bmad" if bmad_detected and story_id else "default"

    return {
        "bmad_detected": bmad_detected,
        "story_id": story_id,
        "commit_mode": commit_mode,
        "bmad_detection_reasons": unique_reasons,
        "bmad_workspace_root": str(workspace_root) if workspace_root else None,
        "bmad_project_context": str(project_context_path) if project_context_path else None,
    }


def format_bmad_reasons(reasons: Sequence[str]) -> str:
    if not reasons:
        return "(无)"
    return "、".join(BMAD_REASON_LABELS.get(reason, reason) for reason in reasons)


def build_apply_next_action_hint(result: Dict[str, object]) -> Optional[str]:
    if not result.get("commit_created"):
        if result.get("error"):
            return "检查错误信息，处理后重新执行 apply。"
        return "当前没有可提交改动，无需进一步操作。"
    if result.get("push_succeeded"):
        return "提交和推送已完成，可继续下一个仓库或发起 PR。"
    return "提交已创建但推送失败，请先修复 upstream/远端问题后重新推送。"


def build_pull_next_action_hint(result: Dict[str, object]) -> Optional[str]:
    if result.get("skipped"):
        if result.get("skip_reason") == "no_upstream":
            return "先为当前分支建立 upstream，再重新执行 pull。"
        if result.get("skip_reason") == "remote_not_found":
            return "检查 remote 名称是否正确，必要时先执行 `git remote -v`。"
        return "当前仓库已跳过，无需额外操作。"
    if result.get("pull_succeeded") and result.get("stash_restore_succeeded"):
        updated_commits = result.get("updated_commits", [])
        if updated_commits:
            return "拉取完成，建议快速检查最新变更后继续工作。"
        return "当前分支已与远端同步，无需额外操作。"
    if result.get("stash_created") and not result.get("stash_restore_succeeded"):
        return "先处理冲突并检查 `git stash list`，确认后再手动恢复 stash。"
    return "根据错误信息处理拉取失败原因后再重试。"


def stage_changes(repo: Path, stage_mode: str) -> None:
    if stage_mode == "all":
        run_git(repo, ["add", "-A"])
        return
    if stage_mode == "tracked":
        run_git(repo, ["add", "-u"])
        return
    if stage_mode == "none":
        return
    raise ValueError(f"Unsupported stage mode: {stage_mode}")


def parse_name_status(repo: Path) -> List[Dict[str, str]]:
    lines = run_git(repo, ["diff", "--cached", "--name-status", "--find-renames"]).stdout.splitlines()
    result: List[Dict[str, str]] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        code = parts[0]
        status = code[0]
        entry: Dict[str, str] = {"status": status}
        if status in {"R", "C"} and len(parts) >= 3:
            entry["old_path"] = parts[1]
            entry["path"] = parts[2]
        elif len(parts) >= 2:
            entry["path"] = parts[1]
        else:
            entry["path"] = ""
        result.append(entry)
    return result


def top_path_segments(paths: Sequence[str], limit: int = 5) -> List[str]:
    freq: Dict[str, int] = {}
    for path in paths:
        normalized = path.strip()
        if not normalized:
            continue
        first = normalized.split("/", 1)[0].lower()
        if first in {".", ".."}:
            continue
        freq[first] = freq.get(first, 0) + 1

    ordered = sorted(freq.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _ in ordered[:limit]]


def normalize_scope(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", text.lower())
    normalized = normalized.strip("-")
    if not normalized:
        return "repo"
    return normalized


def is_docs_path(path: str) -> bool:
    p = Path(path)
    if p.suffix.lower() in DOC_EXTENSIONS:
        return True

    stem = p.stem.lower()
    name = p.name.lower()
    if stem in DOC_NAMES or name in {"readme", "changelog", "license", "notice", "contributing"}:
        return True

    lowered = path.lower()
    return lowered.startswith("docs/") or "/docs/" in lowered


def detect_commit_type(branch: str, changed_paths: Sequence[str]) -> str:
    if changed_paths and all(is_docs_path(path) for path in changed_paths):
        return "docs"

    lower_branch = branch.lower()
    if any(token in lower_branch for token in ["fix", "bug", "hotfix", "issue"]):
        return "fix"
    if any(token in lower_branch for token in ["feat", "feature"]):
        return "feat"
    if any(token in lower_branch for token in ["refactor", "cleanup", "tidy"]):
        return "refactor"
    if any(token in lower_branch for token in ["chore", "build", "deps", "ci"]):
        return "chore"

    # If only engineering meta files changed, classify as chore.
    if changed_paths and all(
        path.endswith((".lock", ".yml", ".yaml", ".toml", ".json"))
        or path.startswith((".github/", ".gitlab/", ".idea/", ".vscode/"))
        or Path(path).name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pom.xml"}
        for path in changed_paths
    ):
        return "chore"

    return "feat"


def detect_area(repo_name: str, top_paths: Sequence[str]) -> str:
    for item in top_paths:
        if item not in GENERIC_SCOPE_PARTS:
            return item
    return repo_name


def build_subject(commit_type: str, scope: str, area: str, story_id: Optional[str] = None) -> str:
    if commit_type == "docs":
        text = f"更新{area}文档与说明"
    elif commit_type == "fix":
        text = f"修复{area}相关缺陷"
    elif commit_type == "refactor":
        text = f"重构{area}相关实现"
    elif commit_type == "chore":
        text = f"更新{area}工程配置"
    else:
        text = f"完善{area}相关功能"
    if story_id:
        text = f"[{story_id}] {text}"
    return f"{commit_type}({scope}): {text}"


def count_status(name_status: Sequence[Dict[str, str]]) -> Dict[str, int]:
    counts = {"added": 0, "modified": 0, "deleted": 0, "renamed": 0, "other": 0}
    for item in name_status:
        status = item.get("status", "")
        if status == "A":
            counts["added"] += 1
        elif status == "M":
            counts["modified"] += 1
        elif status == "D":
            counts["deleted"] += 1
        elif status == "R":
            counts["renamed"] += 1
        else:
            counts["other"] += 1
    return counts


def build_body(
    name_status: Sequence[Dict[str, str]],
    top_paths: Sequence[str],
    stat_summary: str,
    bmad_context: Optional[Dict[str, object]] = None,
) -> str:
    status_counts = count_status(name_status)
    changed_file_count = len(name_status)
    top_paths_text = ", ".join(top_paths) if top_paths else "(根目录)"

    lines = [
        f"- 变更文件: {changed_file_count}",
        (
            "- 变更分布: "
            f"新增{status_counts['added']} / 修改{status_counts['modified']} / "
            f"删除{status_counts['deleted']} / 重命名{status_counts['renamed']}"
        ),
        f"- 主要路径: {top_paths_text}",
    ]
    if stat_summary:
        lines.append(f"- 差异统计: {stat_summary}")
    if bmad_context and bmad_context.get("bmad_detected"):
        lines.append(f"- BMad 上下文: {format_bmad_reasons(bmad_context.get('bmad_detection_reasons', []))}")
        story_id = bmad_context.get("story_id")
        if story_id:
            lines.append(f"- Story ID: {story_id}")
        else:
            lines.append("- Story ID: (未识别，标题回退普通模板)")
    return "\n".join(lines)


def summarize_repo(repo: Path, stage_mode: str) -> Dict[str, object]:
    repo = to_repo_root(repo)
    assert_clean_git_state_for_commit(repo)
    stage_changes(repo, stage_mode)

    staged_files = [
        line.strip()
        for line in run_git(repo, ["diff", "--cached", "--name-only"]).stdout.splitlines()
        if line.strip()
    ]
    name_status = parse_name_status(repo)
    stat_summary = run_git(repo, ["diff", "--cached", "--shortstat"]).stdout.strip()
    top_paths = top_path_segments([item.get("path", "") for item in name_status], limit=5)

    branch = get_branch(repo)
    upstream = get_upstream(repo)
    bmad_context = detect_bmad_context(repo, branch)
    commit_type = detect_commit_type(branch, staged_files)
    scope = normalize_scope(repo.name)
    area = detect_area(repo.name, top_paths)
    story_id = bmad_context.get("story_id") if bmad_context.get("commit_mode") == "bmad" else None
    suggested_subject = build_subject(commit_type, scope, area, story_id=story_id)
    suggested_body = build_body(name_status, top_paths, stat_summary, bmad_context=bmad_context)

    return {
        "repo_path": str(repo),
        "repo_name": repo.name,
        "branch": branch,
        "upstream": upstream,
        "staged_files": staged_files,
        "name_status": name_status,
        "status_counts": count_status(name_status),
        "stat_summary": stat_summary,
        "top_paths": top_paths,
        **bmad_context,
        "suggested_subject": suggested_subject,
        "suggested_body": suggested_body,
    }


def commit_and_push(repo: Path, subject: str, body: str) -> Dict[str, object]:
    message = subject.strip()
    if body.strip():
        message = f"{message}\n\n{body.strip()}\n"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fp:
        fp.write(message)
        temp_path = Path(fp.name)

    try:
        commit_proc = run_git(repo, ["commit", "-F", str(temp_path)], check=False)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    if commit_proc.returncode != 0:
        text = git_error_text(commit_proc, "git commit 执行失败")
        if "nothing to commit" in text.lower():
            return {
                "repo_path": str(repo),
                "commit_created": False,
                "commit_hash": None,
                "push_attempted": False,
                "push_succeeded": False,
                "error": "没有可提交的暂存改动",
            }
        return {
            "repo_path": str(repo),
            "commit_created": False,
            "commit_hash": None,
            "push_attempted": False,
            "push_succeeded": False,
            "error": text,
        }

    commit_hash = run_git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    push_proc = run_git(repo, ["push"], check=False)
    if push_proc.returncode == 0:
        return {
            "repo_path": str(repo),
            "commit_created": True,
            "commit_hash": commit_hash,
            "push_attempted": True,
            "push_succeeded": True,
            "error": None,
        }

    push_error = git_error_text(push_proc, "git push 执行失败")

    lowered = push_error.lower()
    if "no upstream branch" in lowered or "has no upstream branch" in lowered:
        branch = get_branch(repo)
        push_error = (
            f"{push_error}\n提示: 先执行 `git push -u origin {branch}` 建立 upstream，再重新运行。"
        )
    elif "no configured push destination" in lowered:
        branch = get_branch(repo)
        push_error = (
            f"{push_error}\n提示: 先执行 `git remote add origin <url>`，再执行 "
            f"`git push -u origin {branch}` 建立推送目标。"
        )

    return {
        "repo_path": str(repo),
        "commit_created": True,
        "commit_hash": commit_hash,
        "push_attempted": True,
        "push_succeeded": False,
        "error": push_error,
    }


def list_updated_commits(repo: Path, head_before: str, head_after: str, limit: int = 100) -> List[str]:
    if not head_before or not head_after or head_before == head_after:
        return []
    proc = run_git(
        repo,
        ["log", "--oneline", "--no-decorate", f"{head_before}..{head_after}", f"--max-count={limit}"],
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def build_pull_args(strategy: str, remote: Optional[str], remote_branch: Optional[str]) -> List[str]:
    args = ["pull"]
    if strategy == "rebase":
        args.append("--rebase")
    elif strategy == "ff-only":
        args.append("--ff-only")
    elif strategy != "merge":
        raise ValueError(f"Unsupported pull strategy: {strategy}")

    if remote:
        args.append(remote)
        if remote_branch:
            args.append(remote_branch)
    return args


def restore_stash(repo: Path) -> subprocess.CompletedProcess:
    return run_git(repo, ["stash", "pop"], check=False)


def pull_repo(
    repo: Path,
    strategy: str,
    remote: Optional[str],
    remote_branch: Optional[str],
    auto_stash: bool,
) -> Dict[str, object]:
    repo = to_repo_root(repo)
    assert_clean_git_state_for_pull(repo)

    branch = get_branch(repo)
    tracking_upstream = get_upstream(repo)
    dirty_before_pull = is_repo_dirty(repo)
    head_before = run_git(repo, ["rev-parse", "HEAD"]).stdout.strip()

    remote_used: Optional[str] = None
    remote_branch_used: Optional[str] = None
    if remote:
        remote_used = remote.strip() or None
        remote_branch_used = (remote_branch or "").strip() or branch
    else:
        remote_used, remote_branch_used = parse_upstream_ref(tracking_upstream)

    base_result: Dict[str, object] = {
        "repo_path": str(repo),
        "branch": branch,
        "upstream": tracking_upstream,
        "pull_strategy": strategy,
        "remote_used": remote_used,
        "remote_branch_used": remote_branch_used,
        "dirty_before_pull": dirty_before_pull,
        "stash_created": False,
        "stash_restore_succeeded": True,
        "head_before": head_before,
        "head_after": head_before,
        "updated_commits": [],
        "pull_attempted": False,
        "pull_succeeded": False,
        "skipped": False,
        "skip_reason": None,
        "error": None,
    }

    if remote_used:
        if not remote_exists(repo, remote_used):
            base_result["skipped"] = True
            base_result["skip_reason"] = "remote_not_found"
            base_result["error"] = f"未找到远程仓库 `{remote_used}`，已跳过"
            return base_result
    elif tracking_upstream is None:
        base_result["skipped"] = True
        base_result["skip_reason"] = "no_upstream"
        base_result["error"] = "当前分支未配置 upstream，已跳过"
        return base_result

    if dirty_before_pull and not auto_stash:
        base_result["error"] = "工作区有未提交改动，请先清理或启用 --auto-stash"
        return base_result

    if dirty_before_pull and auto_stash:
        stash_proc = run_git(repo, ["stash", "push", "-u", "-m", AUTO_STASH_MESSAGE], check=False)
        if stash_proc.returncode != 0:
            base_result["error"] = git_error_text(stash_proc, "创建 stash 失败")
            return base_result
        stash_output = f"{stash_proc.stdout}\n{stash_proc.stderr}".lower()
        stash_created = "no local changes to save" not in stash_output
        base_result["stash_created"] = stash_created

    pull_args = build_pull_args(strategy, remote_used, remote_branch_used)
    pull_proc = run_git(repo, pull_args, check=False)
    base_result["pull_attempted"] = True
    if pull_proc.returncode != 0:
        base_result["error"] = git_error_text(pull_proc, "git pull 执行失败")
        if base_result["stash_created"]:
            states = find_in_progress_states(repo)
            if states or has_unresolved_conflicts(repo):
                base_result["stash_restore_succeeded"] = False
                base_result["error"] = (
                    f"{base_result['error']}\n提示: 拉取失败且仓库处于冲突状态，已保留 stash。"
                    "请先解决冲突，再手动 `git stash pop`。"
                )
            else:
                pop_proc = restore_stash(repo)
                if pop_proc.returncode == 0:
                    base_result["stash_restore_succeeded"] = True
                else:
                    base_result["stash_restore_succeeded"] = False
                    pop_error = git_error_text(pop_proc, "恢复 stash 失败")
                    base_result["error"] = (
                        f"{base_result['error']}\n提示: 拉取失败后自动恢复 stash 失败：{pop_error}\n"
                        "请执行 `git stash list` 检查并手动恢复。"
                    )
        return base_result

    base_result["pull_succeeded"] = True
    head_after = run_git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    base_result["head_after"] = head_after
    base_result["updated_commits"] = list_updated_commits(repo, head_before, head_after)

    if base_result["stash_created"]:
        pop_proc = restore_stash(repo)
        if pop_proc.returncode != 0:
            base_result["stash_restore_succeeded"] = False
            base_result["pull_succeeded"] = False
            pop_error = git_error_text(pop_proc, "恢复 stash 失败")
            base_result["error"] = (
                "拉取成功，但恢复 stash 失败，请手动处理冲突并执行 `git stash list` 检查。"
                f"\n详情: {pop_error}"
            )
            return base_result
        base_result["stash_restore_succeeded"] = True

    return base_result


def resolve_repos(root: Path, mode: str, max_depth: int) -> List[Path]:
    root = root.resolve()
    if mode == "single":
        if not is_git_repo(root):
            raise RuntimeError(f"{root} 不是 Git 仓库")
        return [to_repo_root(root)]

    if mode == "multi":
        repos = discover_repos(root, max_depth=max_depth)
        if is_git_repo(root):
            root_repo = to_repo_root(root)
            if root_repo not in repos:
                repos.insert(0, root_repo)
        return sorted({repo.resolve() for repo in repos})

    # auto mode
    if is_git_repo(root):
        return [to_repo_root(root)]
    return discover_repos(root, max_depth=max_depth)


def print_human_scan(items: Sequence[Dict[str, object]]) -> None:
    if not items:
        print("未发现仓库")
        return
    dirty_count = 0
    bmad_count = 0
    for item in items:
        dirty = "dirty" if item.get("dirty") else "clean"
        counts = item.get("counts", {})
        if item.get("dirty"):
            dirty_count += 1
        if item.get("bmad_detected"):
            bmad_count += 1
        print(f"- repo: {item.get('repo_name')} [{dirty}]")
        print(f"  path: {item.get('repo_path')}")
        print(f"  branch: {item.get('branch')}")
        print(f"  upstream: {item.get('upstream') or '(none)'}")
        print(
            "  changes: "
            f"modified={counts.get('modified', 0)} deleted={counts.get('deleted', 0)} "
            f"untracked={counts.get('untracked', 0)} staged={counts.get('staged', 0)}"
        )
        print(
            f"  commit_mode: {item.get('commit_mode')}"
            f" | story_id: {item.get('story_id') or '(none)'}"
        )
        print(f"  bmad_reasons: {format_bmad_reasons(item.get('bmad_detection_reasons', []))}")
    print(
        f"summary: total={len(items)} dirty={dirty_count} clean={len(items) - dirty_count} bmad_context={bmad_count}"
    )


def print_human_summary(data: Dict[str, object]) -> None:
    print(f"repo: {data['repo_path']}")
    print(f"repo_name: {data['repo_name']}")
    print(f"branch: {data['branch']}")
    print(f"upstream: {data['upstream'] or '(none)'}")
    print(f"staged files: {len(data['staged_files'])}")
    print(f"commit_mode: {data['commit_mode']}")
    print(f"bmad_detected: {data['bmad_detected']}")
    print(f"story_id: {data['story_id'] or '(none)'}")
    print(f"bmad_reasons: {format_bmad_reasons(data.get('bmad_detection_reasons', []))}")
    print(f"top_paths: {', '.join(data['top_paths']) if data['top_paths'] else '(根目录)'}")
    print(f"stat_summary: {data['stat_summary'] or '(none)'}")
    counts = data.get("status_counts", {})
    print(
        "change_distribution: "
        f"added={counts.get('added', 0)} modified={counts.get('modified', 0)} "
        f"deleted={counts.get('deleted', 0)} renamed={counts.get('renamed', 0)} other={counts.get('other', 0)}"
    )
    print(f"suggested subject: {data['suggested_subject']}")
    print("suggested body:")
    print(data["suggested_body"])


def print_human_apply(result: Dict[str, object], verbose: bool) -> None:
    print(f"repo: {result['repo_path']}")
    print(f"branch: {result.get('branch')}")
    print(f"upstream: {result.get('upstream') or '(none)'}")
    print(f"commit_mode: {result.get('commit_mode')}")
    print(f"bmad_detected: {result.get('bmad_detected')}")
    print(f"story_id: {result.get('story_id') or '(none)'}")
    print(f"bmad_reasons: {format_bmad_reasons(result.get('bmad_detection_reasons', []))}")
    print(f"commit_created: {result['commit_created']}")
    if result.get("commit_hash"):
        print(f"commit_hash: {result['commit_hash']}")
    if result.get("commit_subject"):
        print(f"commit_subject: {result['commit_subject']}")
    if result.get("staged_file_count") is not None:
        print(f"staged_file_count: {result['staged_file_count']}")
    if result.get("top_paths") is not None:
        top_paths = result.get("top_paths") or []
        print(f"top_paths: {', '.join(top_paths) if top_paths else '(根目录)'}")
    if result.get("stat_summary") is not None:
        print(f"stat_summary: {result.get('stat_summary') or '(none)'}")
    print(f"push_attempted: {result['push_attempted']}")
    print(f"push_succeeded: {result['push_succeeded']}")
    if verbose and result.get("staged_files"):
        print("staged_files:")
        for item in result["staged_files"]:
            print(f"- {item}")
    if result.get("error"):
        print(f"error: {result['error']}")
    if result.get("next_action_hint"):
        print(f"next_action: {result['next_action_hint']}")


def print_human_pull(result: Dict[str, object], verbose: bool) -> None:
    print(f"repo: {result['repo_path']}")
    print(f"branch: {result['branch']}")
    print(f"upstream: {result['upstream'] or '(none)'}")
    print(f"pull_strategy: {result['pull_strategy']}")
    if result.get("remote_used"):
        print(f"remote_used: {result['remote_used']}")
    if result.get("remote_branch_used"):
        print(f"remote_branch_used: {result['remote_branch_used']}")
    print(f"dirty_before_pull: {result['dirty_before_pull']}")
    print(f"stash_created: {result['stash_created']}")
    print(f"stash_restore_succeeded: {result['stash_restore_succeeded']}")
    print(f"pull_attempted: {result['pull_attempted']}")
    print(f"pull_succeeded: {result['pull_succeeded']}")
    print(f"skipped: {result['skipped']}")
    if result.get("skip_reason"):
        print(f"skip_reason: {result['skip_reason']}")

    updated_commits = result.get("updated_commits", [])
    print(f"updated_commit_count: {len(updated_commits)}")
    if updated_commits:
        print(f"latest_updated_commit: {updated_commits[0]}")
    if verbose:
        print(f"head_before: {result['head_before']}")
        print(f"head_after: {result['head_after']}")
        if updated_commits:
            print("updated_commits:")
            for line in updated_commits:
                print(f"- {line}")

    if result.get("error"):
        print(f"error: {result['error']}")
    if result.get("next_action_hint"):
        print(f"next_action: {result['next_action_hint']}")


def cmd_scan(args: argparse.Namespace) -> int:
    repos = resolve_repos(Path(args.root), args.mode, args.max_depth)
    items = [get_repo_status(repo) for repo in repos]
    if args.dirty_only:
        items = [item for item in items if item["dirty"]]

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print_human_scan(items)
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    data = summarize_repo(Path(args.repo), args.stage_mode)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_human_summary(data)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    summary = summarize_repo(Path(args.repo), args.stage_mode)
    if not summary["staged_files"]:
        result = {
            "repo_path": summary["repo_path"],
            "branch": summary["branch"],
            "upstream": summary["upstream"],
            "commit_mode": summary["commit_mode"],
            "bmad_detected": summary["bmad_detected"],
            "story_id": summary["story_id"],
            "bmad_detection_reasons": summary["bmad_detection_reasons"],
            "commit_created": False,
            "commit_hash": None,
            "commit_subject": None,
            "staged_file_count": 0,
            "staged_files": [],
            "top_paths": summary["top_paths"],
            "stat_summary": summary["stat_summary"],
            "push_attempted": False,
            "push_succeeded": False,
            "error": "没有可提交改动",
        }
        result["next_action_hint"] = build_apply_next_action_hint(result)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human_apply(result, args.verbose)
        return 0

    subject = args.subject.strip() if args.subject else str(summary["suggested_subject"])
    body = args.body if args.body is not None else str(summary["suggested_body"])

    result = commit_and_push(Path(summary["repo_path"]), subject, body)
    result["branch"] = summary["branch"]
    result["upstream"] = summary["upstream"]
    result["commit_mode"] = summary["commit_mode"]
    result["bmad_detected"] = summary["bmad_detected"]
    result["story_id"] = summary["story_id"]
    result["bmad_detection_reasons"] = summary["bmad_detection_reasons"]
    result["commit_subject"] = subject
    result["staged_file_count"] = len(summary["staged_files"])
    result["top_paths"] = summary["top_paths"]
    result["stat_summary"] = summary["stat_summary"]
    result["next_action_hint"] = build_apply_next_action_hint(result)
    if args.verbose:
        result["staged_files"] = summary["staged_files"]

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human_apply(result, args.verbose)

    if result["commit_created"] and result["push_succeeded"]:
        return 0
    if result["commit_created"] and not result["push_succeeded"]:
        return 3
    return 2


def cmd_pull(args: argparse.Namespace) -> int:
    result = pull_repo(
        Path(args.repo),
        strategy=args.strategy,
        remote=args.remote,
        remote_branch=args.remote_branch,
        auto_stash=args.auto_stash,
    )
    result["next_action_hint"] = build_pull_next_action_hint(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human_pull(result, args.verbose)

    if result["skipped"]:
        return 0
    if result["pull_succeeded"] and result["stash_restore_succeeded"]:
        return 0
    return 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Conventional Commit messages and run quick commit/push/pull for Git repos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover repositories and show git status summary")
    scan.add_argument("--root", default=".", help="Root path to inspect")
    scan.add_argument("--mode", choices=["auto", "single", "multi"], default="auto")
    scan.add_argument("--max-depth", type=int, default=4, help="Max directory depth when scanning")
    scan.add_argument("--dirty-only", action="store_true", help="Only output dirty repositories")
    scan.add_argument("--json", action="store_true", help="Output JSON")
    scan.set_defaults(func=cmd_scan)

    summarize = subparsers.add_parser(
        "summarize",
        help="Stage changes and summarize diff for one repository",
    )
    summarize.add_argument("--repo", required=True, help="Repository path")
    summarize.add_argument("--stage-mode", choices=["all", "tracked", "none"], default="all")
    summarize.add_argument("--json", action="store_true", help="Output JSON")
    summarize.set_defaults(func=cmd_summarize)

    apply_parser = subparsers.add_parser(
        "apply",
        help="Stage, generate message, commit, and push to current upstream",
    )
    apply_parser.add_argument("--repo", required=True, help="Repository path")
    apply_parser.add_argument("--stage-mode", choices=["all", "tracked", "none"], default="all")
    apply_parser.add_argument("--subject", help="Commit subject. Auto-generated when omitted")
    apply_parser.add_argument("--body", help="Commit body. Auto-generated when omitted")
    apply_parser.add_argument("--verbose", action="store_true", help="Show expanded staged file details")
    apply_parser.add_argument("--json", action="store_true", help="Output JSON")
    apply_parser.set_defaults(func=cmd_apply)

    pull_parser = subparsers.add_parser(
        "pull",
        help="Quick pull from tracking upstream or a specified remote branch",
    )
    pull_parser.add_argument("--repo", required=True, help="Repository path")
    pull_parser.add_argument("--strategy", choices=["merge", "rebase", "ff-only"], default="merge")
    pull_parser.add_argument("--remote", help="Optional remote name, for example upstream")
    pull_parser.add_argument(
        "--remote-branch",
        help="Optional branch on remote. Defaults to current local branch when --remote is set",
    )
    pull_stash_group = pull_parser.add_mutually_exclusive_group()
    pull_stash_group.add_argument(
        "--auto-stash",
        dest="auto_stash",
        action="store_true",
        help="Auto stash dirty changes before pull",
    )
    pull_stash_group.add_argument(
        "--no-auto-stash",
        dest="auto_stash",
        action="store_false",
        help="Disable auto stash for dirty working tree",
    )
    pull_parser.set_defaults(auto_stash=True)
    pull_parser.add_argument("--verbose", action="store_true", help="Show pull commit details")
    pull_parser.add_argument("--json", action="store_true", help="Output JSON")
    pull_parser.set_defaults(func=cmd_pull)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except GitCommandError as exc:
        message = {
            "error": str(exc),
            "repo_path": str(exc.repo),
            "returncode": exc.returncode,
        }
        print(json.dumps(message, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
