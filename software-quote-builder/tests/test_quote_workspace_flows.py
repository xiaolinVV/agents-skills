import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / 'software-quote-builder' / 'scripts'
PREPARE = SCRIPTS_DIR / 'prepare_quote_workspace.py'
FIND = SCRIPTS_DIR / 'find_quote_workspace.py'


class QuoteWorkspaceFlowTests(unittest.TestCase):
    maxDiff = None

    def run_json(self, args, env=None):
        cmd = ['python3', *[str(a) for a in args]]
        completed = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def make_history_project(self, root: Path, dir_name: str, project_name: str):
        project_dir = root / dir_name
        (project_dir / 'source').mkdir(parents=True, exist_ok=True)
        (project_dir / 'output').mkdir(parents=True, exist_ok=True)
        (project_dir / 'source' / '需求.docx').write_text('dummy', encoding='utf-8')
        (project_dir / 'quote-project.json').write_text(
            json.dumps(
                {
                    'project_name': project_name,
                    'mode': 'template',
                    'special_notes_enabled': True,
                    'items': [
                        {
                            'module_l1': '基础',
                            'module_l2': '管理',
                            'feature': '列表',
                            'description': '列表展示',
                            'estimated_days': 3,
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )
        (project_dir / 'output' / f'{project_name}功能清单报价表.xlsx').write_text('fake-xlsx', encoding='utf-8')
        return project_dir

    def test_default_root_prefers_wengao_then_wendang_then_documents_then_home(self):
        cases = [
            (['文稿', '文档', 'Documents'], '文稿'),
            (['文档', 'Documents'], '文档'),
            (['Documents'], 'Documents'),
            ([], ''),
        ]

        for present_dirs, expected_parent in cases:
            with self.subTest(present_dirs=present_dirs, expected_parent=expected_parent or '~'):
                with tempfile.TemporaryDirectory() as tmp:
                    home = Path(tmp)
                    for name in present_dirs:
                        (home / name).mkdir(parents=True)
                    env = os.environ.copy()
                    env['HOME'] = str(home)
                    manifest = self.run_json(
                        [PREPARE, '--project-name', '测试项目', '--timestamp', '20260324-180000'],
                        env=env,
                    )
                    if expected_parent:
                        expected_root = home / expected_parent / '功能清单报价'
                    else:
                        expected_root = home / '功能清单报价'
                    self.assertEqual(Path(manifest['root_dir']), expected_root)


    def test_find_history_searches_all_default_roots_for_legacy_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / '文稿').mkdir(parents=True)
            legacy_root = home / '文档' / '功能清单报价'
            legacy_root.mkdir(parents=True)
            legacy = self.make_history_project(
                legacy_root,
                '老项目-20260324-120000',
                '老项目',
            )
            env = os.environ.copy()
            env['HOME'] = str(home)
            manifest = self.run_json([FIND, '老项目报价清单'], env=env)
            self.assertEqual(Path(manifest['candidates'][0]['project_dir']), legacy)

    def test_find_history_prioritizes_project_name_over_source_file_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '功能清单报价'
            root.mkdir(parents=True)
            expected = self.make_history_project(root, '能源监管平台-20260324-090000', '能源监管平台')
            distractor = self.make_history_project(root, '智慧政务平台-20260324-200000', '智慧政务平台')
            (distractor / 'source' / '需求.docx').unlink()
            (distractor / 'source' / '能源监管平台需求说明.docx').write_text('dummy', encoding='utf-8')
            manifest = self.run_json([FIND, '能源监管平台报价清单', '--root-dir', root])
            self.assertEqual(Path(manifest['candidates'][0]['project_dir']), expected)
            self.assertEqual(manifest['candidates'][0]['match_basis'], '能源监管平台')

    def test_prepare_revision_uses_base_project_root_when_root_not_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / '文稿').mkdir(parents=True)
            base_root = home / '文档' / '功能清单报价'
            base_root.mkdir(parents=True)
            base = self.make_history_project(base_root, '跨根项目-20260324-090000', '跨根项目')
            env = os.environ.copy()
            env['HOME'] = str(home)
            manifest = self.run_json(
                [PREPARE, '--project-name', '跨根项目', '--timestamp', '20260324-210000', '--base-project-dir', base],
                env=env,
            )
            self.assertEqual(Path(manifest['root_dir']), base_root)
            self.assertEqual(Path(manifest['project_dir']).parent, base_root)

    def test_prepare_revision_falls_back_to_xlsx_when_base_json_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '报价根'
            base = root / '失效JSON项目-20260324-090000'
            (base / 'source').mkdir(parents=True, exist_ok=True)
            (base / 'output').mkdir(parents=True, exist_ok=True)
            (base / 'source' / '需求.docx').write_text('dummy', encoding='utf-8')
            (base / 'quote-project.json').write_text('{not-json}', encoding='utf-8')

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = '报价表'
            sheet.append(['失效JSON项目功能清单报价表'])
            sheet.append(['序号', '一级模块', '二级模块', '功能点', '功能说明', '预估工时（人天）', '单价（元/人天）', '小计（元）', '备注'])
            sheet.append([1, '系统', '基础', '首页', '首页展示', 2, 800, 1600, '来源: 需求文档'])
            sheet.append(['合计', '', '', '', '', 2, '', 1600, ''])
            workbook.save(base / 'output' / '失效JSON项目功能清单报价表.xlsx')

            manifest = self.run_json(
                [PREPARE, '--project-name', '失效JSON项目', '--root-dir', root, '--timestamp', '20260324-220000', '--base-project-dir', base]
            )
            self.assertEqual(manifest['resume_mode'], 'xlsx_recovered')
            quote_json = json.loads(Path(manifest['quote_json']).read_text(encoding='utf-8'))
            self.assertEqual(quote_json['items'][0]['feature'], '首页')

    def test_find_history_prefers_latest_timestamp_for_same_best_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '功能清单报价'
            root.mkdir(parents=True)
            older = self.make_history_project(
                root,
                '核电项目混凝土全过程管理平台-20260324-094746',
                '核电项目混凝土全过程管理平台',
            )
            newer = self.make_history_project(
                root,
                '核电项目混凝土全过程管理平台-20260324-172539',
                '核电项目混凝土全过程管理平台',
            )
            manifest = self.run_json(
                [FIND, '核电项目xxx报价清单', '--root-dir', root, '--limit', '5']
            )
            self.assertGreaterEqual(len(manifest['candidates']), 2)
            self.assertEqual(Path(manifest['candidates'][0]['project_dir']), newer)
            self.assertEqual(Path(manifest['candidates'][1]['project_dir']), older)

    def test_prepare_revision_copies_base_sources_and_quote_json_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '报价根'
            base = self.make_history_project(
                root,
                '能源监管平台-20260324-090000',
                '能源监管平台',
            )
            manifest = self.run_json(
                [
                    PREPARE,
                    '--project-name',
                    '能源监管平台',
                    '--root-dir',
                    root,
                    '--timestamp',
                    '20260324-200000',
                    '--base-project-dir',
                    base,
                ]
            )
            project_dir = Path(manifest['project_dir'])
            self.assertTrue((project_dir / 'source' / '需求.docx').exists())
            self.assertTrue((project_dir / 'quote-project.json').exists())
            workspace_manifest = json.loads((project_dir / 'workspace-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(workspace_manifest['base_project_dir'], str(base))
            self.assertEqual(workspace_manifest['resume_mode'], 'quote_json')
            self.assertEqual(Path(manifest['quote_json']), project_dir / 'quote-project.json')

    def test_prepare_revision_recovers_quote_json_from_xlsx_when_json_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '报价根'
            base = root / '巡检平台-20260324-090000'
            (base / 'source').mkdir(parents=True, exist_ok=True)
            (base / 'output').mkdir(parents=True, exist_ok=True)
            (base / 'source' / '需求.docx').write_text('dummy', encoding='utf-8')

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = '报价表'
            sheet.append(['巡检平台功能清单报价表'])
            sheet.append(['序号', '一级模块', '二级模块', '功能点', '功能说明', '预估工时（人天）', '单价（元/人天）', '小计（元）', '备注'])
            sheet.append([1, '巡检', '任务管理', '任务列表', '任务列表展示', 4, 800, 3200, '来源: 需求文档'])
            sheet.append(['合计', '', '', '', '', 4, '', 3200, ''])
            workbook.save(base / 'output' / '巡检平台功能清单报价表.xlsx')

            manifest = self.run_json(
                [
                    PREPARE,
                    '--project-name',
                    '巡检平台',
                    '--root-dir',
                    root,
                    '--timestamp',
                    '20260324-210000',
                    '--base-project-dir',
                    base,
                ]
            )

            quote_json = json.loads(Path(manifest['quote_json']).read_text(encoding='utf-8'))
            self.assertEqual(quote_json['mode'], 'template')
            self.assertEqual(len(quote_json['items']), 1)
            self.assertEqual(quote_json['items'][0]['feature'], '任务列表')
            workspace_manifest = json.loads((Path(manifest['project_dir']) / 'workspace-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(workspace_manifest['resume_mode'], 'xlsx_recovered')


if __name__ == '__main__':
    unittest.main()
