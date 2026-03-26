#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def fmt_name(canonical: str, brackets: bool = True) -> str:
    if ' / ' in canonical and brackets:
        return f'【{canonical}】'
    return canonical


def render_ordered(roster, with_zero=True, only_nonzero=False, brackets=True):
    lines = []
    for item in roster:
        count = item['count']
        if only_nonzero and count == 0:
            continue
        if not with_zero and count == 0:
            continue
        lines.append(f'{fmt_name(item["canonical"], brackets=brackets)} {count}')
    return '\n'.join(lines)


def render_summary(state):
    return f"合计：{state['totals']['valid_groups']}组"


def apply_preset(preset):
    presets = {
        'summary': {'style': 'summary'},
        'roster': {'style': 'ordered', 'with_zero': True, 'only_nonzero': False, 'brackets': True},
        'compact': {'style': 'ordered', 'with_zero': False, 'only_nonzero': True, 'brackets': True},
        'submit': {'style': 'plain', 'with_zero': True, 'only_nonzero': False, 'brackets': False},
        'submit-nonzero': {'style': 'plain', 'with_zero': False, 'only_nonzero': True, 'brackets': False},
    }
    return presets[preset]


def main():
    parser = argparse.ArgumentParser(description='Render Xiaohongshu audit results from state JSON.')
    parser.add_argument('--state-file', required=True, help='State JSON file.')
    parser.add_argument('--style', choices=['summary', 'ordered', 'plain', 'json'], default='ordered')
    parser.add_argument('--preset', choices=['summary', 'roster', 'compact', 'submit', 'submit-nonzero'])
    parser.add_argument('--with-zero', action='store_true', help='Include zero-count roster entries.')
    parser.add_argument('--only-nonzero', action='store_true', help='Show only non-zero roster entries.')
    parser.add_argument('--no-brackets', action='store_true', help='Do not wrap alias groups in 【】.')
    args = parser.parse_args()

    state = json.loads(Path(args.state_file).read_text(encoding='utf-8'))

    if args.preset:
        cfg = apply_preset(args.preset)
        style = cfg['style']
        with_zero = cfg.get('with_zero', False)
        only_nonzero = cfg.get('only_nonzero', False)
        brackets = cfg.get('brackets', not args.no_brackets)
    else:
        style = args.style
        with_zero = args.with_zero
        only_nonzero = args.only_nonzero
        brackets = not args.no_brackets if style == 'ordered' else False

    if style == 'summary':
        print(render_summary(state))
        return
    if style == 'json':
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return

    if style in ('ordered', 'plain'):
        print(
            render_ordered(
                state['roster'],
                with_zero=with_zero,
                only_nonzero=only_nonzero,
                brackets=brackets,
            )
        )
        return


if __name__ == '__main__':
    main()
