from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_STATE_ROOT = Path.home() / ".local" / "share" / "cli-anything-yt-dlp"


class SessionStore:
    def __init__(self, root: Path | None = None, name: str = "default") -> None:
        self.root = Path(root or DEFAULT_STATE_ROOT).expanduser()
        self.name = _clean_name(name)
        self.path = self.root / "sessions" / self.name
        self.path.mkdir(parents=True, exist_ok=True)
        self.state_path = self.path / "state.json"
        self.history_path = self.path / "history.json"

    def load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save_state(self, state: dict[str, Any]) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def reset(self) -> None:
        for path in (self.state_path, self.history_path):
            if path.exists():
                path.unlink()

    def load_history(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        return json.loads(self.history_path.read_text(encoding="utf-8"))

    def append_history(self, command: str, inputs: dict[str, Any], result: dict[str, Any]) -> None:
        history = self.load_history()
        history.append(
            {
                "command": command,
                "inputs": inputs,
                "status": result.get("status"),
                "result": result,
            }
        )
        self.history_path.write_text(json.dumps(history[-200:], ensure_ascii=False, indent=2), encoding="utf-8")

    def archive_dir(self) -> Path:
        path = self.path / "archives"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "path": str(self.path),
            "state_path": str(self.state_path),
            "history_path": str(self.history_path),
            "archive_dir": str(self.archive_dir()),
        }


def _clean_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in name.strip())
    return cleaned.strip("-") or "default"
