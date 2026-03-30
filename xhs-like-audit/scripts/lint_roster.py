#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from parse_roster import normalize_alias, parse_roster_text


COMMON_CORE_PREFIXES = ('是',)
COMMON_CORE_SUFFIXES = ('呀', '啊', '吖')
STATUS_SUFFIX_RE = re.compile(r'[（(][^()（）]{0,20}[)）]')


def clean_similarity_text(value: str) -> str:
    value = normalize_alias(value).lower()
    value = STATUS_SUFFIX_RE.sub('', value)
    value = re.sub(r'\s+', '', value)
    return ''.join(ch for ch in value if ch.isalnum() or '\u4e00' <= ch <= '\u9fff')


def extract_core(value: str) -> str:
    core = clean_similarity_text(value)
    for prefix in COMMON_CORE_PREFIXES:
        if core.startswith(prefix) and len(core) - len(prefix) >= 2:
            core = core[len(prefix) :]
    for suffix in COMMON_CORE_SUFFIXES:
        if core.endswith(suffix) and len(core) - len(suffix) >= 2:
            core = core[: -len(suffix)]
    return core


def has_unbalanced_brackets(value: str) -> bool:
    pairs = (('(', ')'), ('（', '）'), ('[', ']'), ('【', '】'))
    for left, right in pairs:
        if value.count(left) != value.count(right):
            return True
    return False


def build_warning(code: str, message: str, groups: list[dict], aliases: list[str]):
    return {
        'code': code,
        'severity': 'warning',
        'message': message,
        'groups': groups,
        'aliases': aliases,
    }


def lint_roster(roster):
    warnings = []
    seen = set()
    alias_entries = []

    for item in roster:
        group_info = {
            'index': item['index'],
            'canonical': item['canonical'],
        }
        for alias in item['aliases']:
            alias_entries.append(
                {
                    'group': group_info,
                    'alias': alias,
                    'normalized': clean_similarity_text(alias),
                    'core': extract_core(alias),
                }
            )
            if has_unbalanced_brackets(alias):
                key = ('unbalanced-brackets', item['index'], alias)
                if key not in seen:
                    seen.add(key)
                    warnings.append(
                        build_warning(
                            'unbalanced-brackets',
                            f'Alias looks malformed or truncated: {alias}',
                            [group_info],
                            [alias],
                        )
                    )

    for index, left in enumerate(alias_entries):
        for right in alias_entries[index + 1 :]:
            if left['group']['index'] == right['group']['index']:
                continue

            left_norm = left['normalized']
            right_norm = right['normalized']
            left_core = left['core']
            right_core = right['core']

            if left_norm and right_norm and min(len(left_norm), len(right_norm)) >= 4:
                if left_norm in right_norm or right_norm in left_norm:
                    key = (
                        'similar-name-cross-group',
                        left['group']['index'],
                        right['group']['index'],
                        left['alias'],
                        right['alias'],
                    )
                    if key not in seen:
                        seen.add(key)
                        warnings.append(
                            build_warning(
                                'similar-name-cross-group',
                                (
                                    'Different roster groups look very similar. Keep them separate unless you '
                                    f'explicitly merge them in one quoted block: {left["alias"]} <-> {right["alias"]}'
                                ),
                                [left['group'], right['group']],
                                [left['alias'], right['alias']],
                            )
                        )
                    continue

            if not left_core or not right_core:
                continue

            same_core = left_core == right_core and len(left_core) >= 2
            short_overlap = (
                min(len(left_core), len(right_core)) >= 2
                and min(len(left_core), len(right_core)) <= 3
                and (left_core in right_core or right_core in left_core)
            )

            if same_core or short_overlap:
                key = (
                    'ambiguous-core-cross-group',
                    left['group']['index'],
                    right['group']['index'],
                    left['alias'],
                    right['alias'],
                )
                if key not in seen:
                    seen.add(key)
                    warnings.append(
                        build_warning(
                            'ambiguous-core-cross-group',
                            (
                                'Different roster groups share a fuzzy core name. Do not auto-merge them; '
                                f'require an active heart and a unique visible match: {left["alias"]} <-> {right["alias"]}'
                            ),
                            [left['group'], right['group']],
                            [left['alias'], right['alias']],
                        )
                    )

    return {
        'summary': {
            'group_count': len(roster),
            'warning_count': len(warnings),
        },
        'warnings': warnings,
    }


def lint_roster_text(text: str):
    roster = parse_roster_text(text)
    report = lint_roster(roster)
    report['summary']['group_count'] = len(roster)
    return report


def render_lint_report_text(report):
    lines = [
        'Roster lint summary:',
        f"- groups: {report['summary']['group_count']}",
        f"- warnings: {report['summary']['warning_count']}",
    ]

    if not report['warnings']:
        lines.append('')
        lines.append('No roster warnings found.')
        return '\n'.join(lines) + '\n'

    lines.append('')
    for index, warning in enumerate(report['warnings'], start=1):
        groups = ', '.join(
            f"#{group['index']} {group['canonical']}" for group in warning.get('groups', [])
        )
        aliases = ' <-> '.join(warning.get('aliases', []))
        lines.extend(
            [
                f"{index}. [{warning['code']}] {warning['message']}",
                f'   groups: {groups}',
                f'   aliases: {aliases}',
            ]
        )

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Lint Xiaohongshu roster text for risky alias groups and malformed names.')
    parser.add_argument('--input-file', help='Path to raw roster text file. Reads stdin if omitted.')
    parser.add_argument('--output-file', help='Optional report output path.')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    args = parser.parse_args()

    if args.input_file:
        text = Path(args.input_file).read_text(encoding='utf-8')
    else:
        text = sys.stdin.read()

    report = lint_roster_text(text)
    if args.format == 'json':
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    else:
        rendered = render_lint_report_text(report)

    if args.output_file:
        Path(args.output_file).write_text(rendered, encoding='utf-8')
    else:
        print(rendered, end='')


if __name__ == '__main__':
    main()
