#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path

from render_report import render_ordered, render_summary


def main():
    parser = argparse.ArgumentParser(description='Export a ready-to-deliver result pack from XHS audit state.')
    parser.add_argument('--state-file', required=True, help='State JSON file.')
    parser.add_argument('--output-dir', required=True, help='Target directory for exported files.')
    parser.add_argument('--name', default='delivery-pack', help='Optional pack name prefix.')
    parser.add_argument('--only-nonzero-submit', action='store_true', help='Also write a submit-nonzero file.')
    args = parser.parse_args()

    state_path = Path(args.state_file).expanduser().resolve()
    state = json.loads(state_path.read_text(encoding='utf-8'))

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.name

    summary_txt = render_summary(state) + '\n'
    roster_txt = render_ordered(state['roster'], with_zero=True, only_nonzero=False, brackets=True) + '\n'
    compact_txt = render_ordered(state['roster'], with_zero=False, only_nonzero=True, brackets=True) + '\n'
    submit_txt = render_ordered(state['roster'], with_zero=True, only_nonzero=False, brackets=False) + '\n'
    submit_nonzero_txt = render_ordered(state['roster'], with_zero=False, only_nonzero=True, brackets=False) + '\n'

    files = {
        f'{prefix}-summary.txt': summary_txt,
        f'{prefix}-roster.txt': roster_txt,
        f'{prefix}-compact.txt': compact_txt,
        f'{prefix}-submit.txt': submit_txt,
    }

    if args.only_nonzero_submit:
        files[f'{prefix}-submit-nonzero.txt'] = submit_nonzero_txt

    for filename, content in files.items():
        (out_dir / filename).write_text(content, encoding='utf-8')

    metadata = {
        'session_name': state.get('session_name', ''),
        'total_valid_groups': state.get('totals', {}).get('valid_groups', 0),
        'roster_meta': state.get('roster_meta', {}),
        'exported_files': sorted(files.keys()) + [f'{prefix}-state.json'],
    }
    (out_dir / f'{prefix}-meta.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    shutil.copy2(state_path, out_dir / f'{prefix}-state.json')
    print(out_dir)


if __name__ == '__main__':
    main()
