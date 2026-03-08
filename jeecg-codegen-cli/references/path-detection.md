# Path Detection Rules (jeecg-codegen-cli)

Use these rules to auto-resolve output paths without asking the user, unless detection fails.

## Supported layouts
1) **Workspace root** (monorepo style)
```
<repo-root>/
  jeecg-boot/              # backend module root
  ant-design-vue-jeecg/    # frontend root
```
2) **Module root** (backend root as repo root)
```
<repo-root>/
  jeecg-codegen-cli/
  jeecg-module-system/
  ant-design-vue-jeecg/    # optional sibling
```

## Detection algorithm (in order)
1) Start from current working directory (cwd).
2) Walk upward until filesystem root:
   - If a directory contains `jeecg-codegen-cli/` and `jeecg-module-system/`, treat it as **module root**.
   - If a directory contains `jeecg-boot/jeecg-codegen-cli/`, treat it as **workspace root**.
3) Prefer **workspace root** when it exists (it implies module is nested in `jeecg-boot/`).
4) If no match is found, **stop and ask the user for explicit paths**.

## Resolved defaults (when root found)
- `CLI_JAR` = `<module-root>/jeecg-codegen-cli/target/jeecg-codegen-cli-*-jar-with-dependencies.jar`
- `BACKEND_OUT` = `<module-root>/jeecg-module-system/jeecg-system-biz`
- `FRONTEND_ROOT` = `<workspace-root>/ant-design-vue-jeecg/src/views` (fallback to `<module-root>/ant-design-vue-jeecg/src/views`)
- `SPEC_OUT` = **absolute** `<workspace-root>/specs/<name>.yaml` (仅是 spec 输出路径；规范文档不参与自动探测)

## Rules
- Always pass `--output`, `--frontend-root`, and **absolute** `--spec-out`.
- Never rely on CLI defaults when repo name differs from `jeecg-boot`.
- If detection fails, ask the user to provide explicit paths.
