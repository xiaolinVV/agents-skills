---
name: jeecg-codegen-cli
description: Use when users ask to run Jeecg-boot code generation via jeecg-codegen-cli (DDL→spec→dry-run→template render), especially for single table, tree table, or one-to-many flows (classic/JVXE/ERP/innerTable/tab), and when you must enforce CLI规范与模板生成、校验spec（如BigDecimal全限定名）。
---

# Jeecg Codegen CLI

## Overview
执行 Jeecg-boot 的 CLI 代码生成规范：基于 DDL 生成 spec，再通过模板渲染生成标准 CRUD 代码，并执行必要的 spec 校验（如 BigDecimal 全限定名）。


## Path Resolution
- 自动探测 `REPO_ROOT`（从 cwd 向上找 `jeecg-boot/jeecg-codegen-cli` 或 `jeecg-codegen-cli` 目录）。
- 解析路径规则见 `references/path-detection.md`。
- 若探测失败，必须询问用户提供输出路径。
- 规范文档来源不在此处，见 **Authoritative Spec**。
- 可选脚本：`scripts/gen_cli_commands.py` 生成标准 CLI 命令（只输出，不执行）。

## Workflow (规范流程)

1) 明确模式与输入
- 确认 jspMode：`one` / `tree` / `many` / `jvxe` / `erp` / `innerTable` / `tab`。
- 确认 DDL 文件与输出路径（后端、前端）。
- 若仅需要后端文件（不拷贝前端），使用 `--no-frontend`，并且无需提供 `--frontend-root`。
- 一对多必须指定 `--one-to-many --main-table --sub-tables`。

2) 确认 CLI Jar
- 若 `jeecg-codegen-cli-*-jar-with-dependencies.jar` 不存在，按规范构建。

3) 生成 spec（DDL → spec）
- 一律使用 **绝对路径** `--spec-out`，避免相对路径落到 projectPath 下导致覆盖失败。

4) BigDecimal 校验（仅当使用 --input 既有 spec）
- 既有 spec 中 `fieldType` 必须是 `java.math.BigDecimal`，否则按规范中止并手工修正。
- 若使用 `--ddl` 生成 spec，最新 CLI 会直接输出 `java.math.BigDecimal`，无需脚本修复。

5) dry-run（可选）
- 先 `--dry-run` 获取输出清单，确认目标文件路径。
- 使用 `--no-frontend` 时，dry-run 的 `frontend` 为空，清单归入 `backend`。

6) 模板渲染（spec → 代码）
- 必须通过 CLI 渲染，禁止手工拼代码。

7) 验收要点
- 单表/树表/一对多的关键字段与模板结构匹配。
- 树表：`extendParams.pidField/textField/hasChildren` 必须存在。
- 一对多：`foreignKeys` 应指向子表外键字段。



## OpenSpec Integration

- **OpenSpec 禁用规则**：除非用户明确使用 openspec 指令/关键词（proposal/spec/change/plan）或 `prompts:openspec-proposal`，否则禁止进入 OpenSpec 流程，仅执行 CLI 生成流程。
- 当使用 `prompts:openspec-proposal` 且明确需要 CLI 生成时，tasks.md 必须按 CLI 标准流程拆解（见 `references/openspec-tasks-template.md`）。
- 提案未审批前禁止执行 CLI 渲染（生成代码属于实现阶段）。

## Authoritative Spec
- 规范来源以 references 为唯一权威，不做其它自动探测。
- 默认以 `references/Jeecg-boot代码生成执行规范（CLI）.md` 为唯一权威规范。
- 仅当用户明确提供其它规范文档路径时，才切换为用户指定文档。
- 执行 CLI 生成时，必须严格遵循规范文档要求，禁止自行臆断。

## References
- 命令生成脚本：`scripts/gen_cli_commands.py`
- 规范/用例同步脚本：`scripts/sync_docs_to_references.py`（默认 dry-run，`--apply` 执行）
- 路径解析规则：`references/path-detection.md`
- 单表测试用例：`references/代码生成执行规范测试用例（单表）.md`
- 树表测试用例：`references/代码生成执行规范测试用例（树表）.md`
- 一对多测试用例：`references/代码生成执行规范测试用例（一对多Vue2多风格）.md`
- 命令模板与校验点：见 `references/cli-workflow.md`。
