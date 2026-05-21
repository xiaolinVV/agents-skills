from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(frozen=True)
class OptionEntry:
    section: str
    flags: list[str]
    metavar: str | None = None
    description: str = ""

    @property
    def primary_flag(self) -> str:
        for flag in self.flags:
            if flag.startswith("--"):
                return flag
        return self.flags[0] if self.flags else ""

    def to_dict(self) -> dict[str, object]:
        return {
            "section": self.section,
            "flags": self.flags,
            "metavar": self.metavar,
            "description": self.description,
            "primary_flag": self.primary_flag,
        }


@dataclass(frozen=True)
class HelpSection:
    name: str
    options: list[OptionEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "options": [option.to_dict() for option in self.options]}


SECTION_RE = re.compile(r"^  ([A-Z][A-Za-z0-9 /-]+):\s*$")
OPTION_RE = re.compile(r"^\s{4}((?:-\S|--\S).+?)(?:\s{2,}(.+))?$")


def parse_help_sections(help_text: str) -> list[HelpSection]:
    sections: list[HelpSection] = []
    current_name: str | None = None
    current_options: list[OptionEntry] = []
    pending: OptionEntry | None = None

    def flush_pending() -> None:
        nonlocal pending
        if pending is not None:
            current_options.append(pending)
            pending = None

    def flush_section() -> None:
        nonlocal current_name, current_options
        flush_pending()
        if current_name is not None:
            sections.append(HelpSection(name=current_name, options=current_options))
        current_name = None
        current_options = []

    for line in help_text.splitlines():
        section_match = SECTION_RE.match(line)
        if section_match:
            flush_section()
            current_name = section_match.group(1)
            continue

        if current_name is None:
            continue

        option_match = OPTION_RE.match(line)
        if option_match:
            flush_pending()
            flag_text = option_match.group(1).strip()
            description = (option_match.group(2) or "").strip()
            flags, metavar = _parse_flags(flag_text)
            pending = OptionEntry(
                section=current_name,
                flags=flags,
                metavar=metavar,
                description=description,
            )
            continue

        if pending is not None and line.startswith("                                    "):
            continuation = line.strip()
            if continuation:
                pending = OptionEntry(
                    section=pending.section,
                    flags=pending.flags,
                    metavar=pending.metavar,
                    description=" ".join(part for part in [pending.description, continuation] if part),
                )

    flush_section()
    return sections


def _parse_flags(flag_text: str) -> tuple[list[str], str | None]:
    flags: list[str] = []
    metavars: list[str] = []
    for part in flag_text.split(","):
        token = part.strip()
        if not token:
            continue
        pieces = token.split(None, 1)
        flags.append(pieces[0])
        if len(pieces) > 1:
            metavars.append(pieces[1])
    return flags, " ".join(metavars) if metavars else None


def flatten_options(sections: list[HelpSection]) -> list[OptionEntry]:
    return [option for section in sections for option in section.options]


def search_options(sections: list[HelpSection], query: str) -> list[OptionEntry]:
    needle = query.strip().lower()
    if not needle:
        return flatten_options(sections)

    matches: list[OptionEntry] = []
    for option in flatten_options(sections):
        haystack = " ".join([option.section, *option.flags, option.metavar or "", option.description]).lower()
        if needle in haystack:
            matches.append(option)
    return matches


def find_section(sections: list[HelpSection], name: str) -> HelpSection | None:
    normalized = name.strip().lower()
    for section in sections:
        if section.name.lower() == normalized:
            return section
    for section in sections:
        if normalized in section.name.lower():
            return section
    return None
