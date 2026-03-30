#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def normalize_alias(value: str) -> str:
    return value.strip().strip('"').strip()


def parse_roster_text(text: str):
    groups = []
    in_quote = False
    current = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if in_quote:
            end_quote = line.endswith('"')
            body = line[:-1] if end_quote else line
            body = normalize_alias(body)
            if body:
                current.append(body)
            if end_quote:
                if current:
                    groups.append(current)
                current = []
                in_quote = False
            continue

        if line.startswith('"'):
            line = line[1:]
            end_quote = line.endswith('"')
            body = line[:-1] if end_quote else line
            body = normalize_alias(body)
            current = [body] if body else []
            if end_quote:
                if current:
                    groups.append(current)
                current = []
            else:
                in_quote = True
            continue

        alias = normalize_alias(line)
        if alias:
            groups.append([alias])

    if in_quote and current:
        groups.append(current)

    roster = []
    for idx, aliases in enumerate(groups, start=1):
        aliases = [a for a in aliases if a]
        canonical = ' / '.join(aliases)
        roster.append(
            {
                'index': idx,
                'canonical': canonical,
                'aliases': aliases,
                'count': 0,
            }
        )
    return roster


def main():
    parser = argparse.ArgumentParser(description='Parse Xiaohongshu roster text into ordered alias groups.')
    parser.add_argument('--input-file', help='Path to raw roster text file. Reads stdin if omitted.')
    parser.add_argument('--output-file', help='Optional JSON output path. Prints to stdout if omitted.')
    args = parser.parse_args()

    if args.input_file:
        text = Path(args.input_file).read_text(encoding='utf-8')
    else:
        text = sys.stdin.read()

    roster = parse_roster_text(text)
    payload = {
        'roster': roster,
        'total_groups': len(roster),
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output_file:
        Path(args.output_file).write_text(rendered + '\n', encoding='utf-8')
    else:
        print(rendered)


if __name__ == '__main__':
    main()
