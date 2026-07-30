#!/usr/bin/env python3
"""Generate deterministic workspace name candidates for jeecg bootstrap flows."""

from __future__ import annotations

import argparse
import datetime as _dt
import re
from typing import List

KEYWORD_MAP = [
    ("电商", "ecommerce"),
    ("商城", "ecommerce"),
    ("供应链", "supply-chain"),
    ("物流", "logistics"),
    ("财务", "finance"),
    ("医疗", "healthcare"),
    ("医院", "healthcare"),
    ("教育", "education"),
    ("政务", "gov"),
    ("制造", "manufacturing"),
    ("crm", "crm"),
    ("erp", "erp"),
    ("oa", "oa"),
    ("saas", "saas"),
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


def derive_base(brief: str) -> str:
    ascii_slug = slugify(brief)
    if ascii_slug:
        return ascii_slug

    hits = [name for keyword, name in KEYWORD_MAP if keyword in brief.lower()]
    if hits:
        # Preserve deterministic order and uniqueness.
        ordered: List[str] = []
        for h in hits:
            if h not in ordered:
                ordered.append(h)
        return "-".join(ordered)

    return "business-project"


def cap_name(name: str, max_len: int = 48) -> str:
    return name[:max_len].rstrip("-")


def build_candidates(base: str, count: int) -> List[str]:
    today = _dt.datetime.now().strftime("%Y%m%d")
    raw = [
        base,
        f"jeecg-{base}",
        f"{base}-workspace",
        f"{base}-platform",
        f"{base}-{today}",
        f"jeecg-{base}-{today}",
        f"{base}-suite",
        f"{base}-system",
    ]
    candidates: List[str] = []
    for name in raw:
        final = cap_name(slugify(name))
        if not final:
            continue
        if final not in candidates:
            candidates.append(final)
        if len(candidates) >= count:
            break
    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", help="Project brief text used to derive workspace names")
    parser.add_argument("--count", type=int, default=5, help="Number of candidates (default: 5)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    count = max(1, min(args.count, 8))
    base = derive_base(args.brief)
    candidates = build_candidates(base, count)
    for idx, name in enumerate(candidates, 1):
        print(f"{idx}. {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
