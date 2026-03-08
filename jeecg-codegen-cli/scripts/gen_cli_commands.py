#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from typing import Optional


def find_repo_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    module_root = None
    workspace_root = None
    while True:
        # module root directly (jeecg-boot module)
        if (cur / 'jeecg-codegen-cli').exists() and (cur / 'jeecg-module-system').exists():
            module_root = cur
        # workspace root (contains module dir jeecg-boot)
        if (cur / 'jeecg-boot' / 'jeecg-codegen-cli').exists() and (cur / 'ant-design-vue-jeecg').exists():
            workspace_root = cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # Prefer workspace root if it contains frontend; otherwise fall back to module root
    if workspace_root:
        return workspace_root
    if module_root:
        return module_root
    return None


def build_paths(repo_root: Path):
    # Determine module root (jeecg-boot module) based on repo layout
    if (repo_root / 'jeecg-boot' / 'jeecg-codegen-cli').exists():
        module_root = repo_root / 'jeecg-boot'
    else:
        module_root = repo_root
    # Frontend root usually lives at repo_root/ant-design-vue-jeecg
    if (repo_root / 'ant-design-vue-jeecg').exists():
        frontend_root = repo_root / 'ant-design-vue-jeecg' / 'src' / 'views'
    else:
        frontend_root = module_root / 'ant-design-vue-jeecg' / 'src' / 'views'
    return {
        'REPO_ROOT': repo_root,
        'CLI_JAR': module_root / 'jeecg-codegen-cli' / 'target',
        'BACKEND_OUT': module_root / 'jeecg-module-system' / 'jeecg-system-biz',
        'FRONTEND_ROOT': frontend_root,
        'SPECS_DIR': repo_root / 'specs'
    }


def find_cli_jar(jar_dir: Path) -> Optional[Path]:
    if not jar_dir.exists():
        return None
    jars = sorted(jar_dir.glob('jeecg-codegen-cli-*-jar-with-dependencies.jar'))
    return jars[-1] if jars else None


def quote(path: Path) -> str:
    return f'"{path}"'


def cmd_spec(ddl: Path, spec_out: Path, jsp_mode: str, vue_style: str, one_to_many: bool,
             main_table: Optional[str], sub_tables: Optional[str], bussi_package: str,
             entity_package: str, paths: dict, cli_jar: Optional[Path], no_frontend: bool) -> str:
    jar = quote(cli_jar) if cli_jar else '$CLI_JAR'
    parts = [
        f"java -jar {jar}",
        f"  --ddl {quote(ddl)}",
        f"  --spec-out {quote(spec_out)}",
        f"  --output {quote(paths['BACKEND_OUT'])}",
        f"  --jsp-mode {jsp_mode}",
        f"  --vue-style {vue_style}",
    ]
    if no_frontend:
        parts.append("  --no-frontend")
    else:
        parts.append(f"  --frontend-root {quote(paths['FRONTEND_ROOT'])}")
    if one_to_many:
        parts += [
            "  --one-to-many",
            f"  --main-table {main_table}",
            f"  --sub-tables {sub_tables}",
        ]
    parts += [
        f"  --bussi-package {bussi_package}",
        f"  --entity-package {entity_package}",
    ]
    return " \
".join(parts)


def cmd_dry_run(spec_out: Path, vue_style: str, paths: dict, cli_jar: Optional[Path], no_frontend: bool) -> str:
    jar = quote(cli_jar) if cli_jar else '$CLI_JAR'
    parts = [
        f"java -jar {jar}",
        f"  --input {quote(spec_out)}",
        f"  --output {quote(paths['BACKEND_OUT'])}",
        f"  --vue-style {vue_style}",
        "  --dry-run",
    ]
    if no_frontend:
        parts.append("  --no-frontend")
    else:
        parts.insert(3, f"  --frontend-root {quote(paths['FRONTEND_ROOT'])}")
    return " \
".join(parts)


def cmd_render(spec_out: Path, vue_style: str, paths: dict, cli_jar: Optional[Path], no_frontend: bool) -> str:
    jar = quote(cli_jar) if cli_jar else '$CLI_JAR'
    parts = [
        f"java -jar {jar}",
        f"  --input {quote(spec_out)}",
        f"  --output {quote(paths['BACKEND_OUT'])}",
        f"  --vue-style {vue_style}",
    ]
    if no_frontend:
        parts.append("  --no-frontend")
    else:
        parts.insert(3, f"  --frontend-root {quote(paths['FRONTEND_ROOT'])}")
    return " \
".join(parts)


def main():
    parser = argparse.ArgumentParser(description='Generate jeecg-codegen-cli command templates.')
    parser.add_argument('--ddl', required=True, help='DDL file path (relative or absolute)')
    parser.add_argument('--spec-out', required=True, help='Spec output file name or path')
    parser.add_argument('--jsp-mode', required=True, choices=['one','tree','many','jvxe','erp','innerTable','tab'])
    parser.add_argument('--vue-style', default='vue', choices=['vue','vue3','vue3Native'])
    parser.add_argument('--bussi-package', default='org.jeecg.modules')
    parser.add_argument('--entity-package', default='cli')
    parser.add_argument('--one-to-many', action='store_true')
    parser.add_argument('--main-table')
    parser.add_argument('--sub-tables')
    parser.add_argument('--no-dry-run', action='store_true')
    parser.add_argument('--no-frontend', action='store_true',
                        help='Skip frontend copy (omit --frontend-root, add --no-frontend)')
    args = parser.parse_args()

    cwd = Path(os.getcwd())
    repo_root = find_repo_root(cwd)
    if not repo_root:
        print('[error] REPO_ROOT not found. Provide explicit paths or run from repo subtree.')
        raise SystemExit(2)

    paths = build_paths(repo_root)
    cli_jar = find_cli_jar(paths['CLI_JAR'])

    ddl = (repo_root / args.ddl).resolve() if not Path(args.ddl).is_absolute() else Path(args.ddl).resolve()

    # spec-out resolution: if only filename, place under repo_root/specs
    spec_out_path = Path(args.spec_out)
    if not spec_out_path.is_absolute():
        spec_out_path = (paths['SPECS_DIR'] / spec_out_path).resolve()

    if args.one_to_many:
        if not args.main_table or not args.sub_tables:
            print('[error] --one-to-many requires --main-table and --sub-tables')
            raise SystemExit(2)

    print('# 1) DDL -> spec')
    print(cmd_spec(ddl, spec_out_path, args.jsp_mode, args.vue_style, args.one_to_many,
                   args.main_table, args.sub_tables, args.bussi_package, args.entity_package,
                   paths, cli_jar, args.no_frontend))
    print()
    if not args.no_dry_run:
        print('# 2) dry-run (optional)')
        print(cmd_dry_run(spec_out_path, args.vue_style, paths, cli_jar, args.no_frontend))
        print()
    print('# 3) render')
    print(cmd_render(spec_out_path, args.vue_style, paths, cli_jar, args.no_frontend))


if __name__ == '__main__':
    main()
