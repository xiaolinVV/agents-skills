from __future__ import annotations

from pathlib import Path


class ReplSkin:
    """Small CLI-Anything-style REPL skin.

    The marketplace version is larger and prettier. This local copy keeps the
    harness self-contained without making terminal styling part of the logic.
    """

    def __init__(self, software: str, version: str = "1.0.0") -> None:
        self.software = software
        self.version = version
        self.history_file = Path.home() / f".cli-anything-{software.replace('-', '_')}" / "history"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def print_banner(self) -> None:
        print(f"cli-anything-{self.software} {self.version}")
        print("Type commands without the cli-anything prefix. Type exit to quit.")

    def create_prompt_session(self):
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory

            return PromptSession(history=FileHistory(str(self.history_file)))
        except Exception:  # noqa: BLE001
            return None

    def get_input(self, session) -> str:
        prompt = f"{self.software}> "
        if session is not None:
            return session.prompt(prompt)
        return input(prompt)

    def print_goodbye(self) -> None:
        print("bye")
