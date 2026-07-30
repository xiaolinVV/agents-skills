# Archived: jeecg-db-design

归档日期：2026-07-30。

本目录不再提供可自动发现的 `SKILL.md`。旧规范强制 `org_code`、复数表名和固定文档目录，与当前 JeecgBoot 3.9.x 及项目级官方代码生成规范冲突。CRUD 建表使用项目级 `jeecg-codegen`；如需恢复独立数据库设计能力，必须先按目标版本重写规范，不得直接恢复此入口。

以下内容仅保留用于 Git 历史和人工参考。

---
name: jeecg-db-design
description: "Design or review database tables for the jeecg-boot low-code platform. Use when users ask to design table schemas, define fields/keys/indexes, or validate DB structure against the jeecg-boot database design standard. Typical triggers: ‘设计一张业务表’, ‘给这个模块出数据库表结构’, ‘按照规范检查表设计’."
---

# Jeecg DB Design

## Overview
Use the project’s database design规范 as the single source of truth, then produce a clean, minimal, backward-compatible schema proposal. When the CRUD flow requires DDL artifacts in the repo, write the SQL scripts to the specified directory instead of only printing them.

## Workflow
1. Clarify requirements: entities, ownership, lifecycle, read/write patterns, and existing tables that must remain compatible.
2. Load the规范 reference: `references/database-design-spec.md` and follow it strictly.
3. Propose schema: table names, columns, types, constraints, indexes, and relationships. Prefer simplicity and eliminate special cases.
4. Check compatibility: confirm no existing table/field/behavior breaks.
5. Output:
   - Always provide DDL + a short rationale mapping key choices back to the规范.
   - If working in the jeecg-boot repo and the CRUD flow is in scope, write SQL scripts to:
     - `docs/architecture/database-development/database-ddl-scripts/<模块>_schema.sql`
     - `docs/architecture/database-development/database-ddl-scripts/<模块>_dict.sql`
   - Ask for `<模块>` if not provided. Create the directory if missing.
   - Put only table DDL (and indexes) in `_schema.sql`. Put dictionary insert SQL in `_dict.sql`.
   - If there are no dictionary items, still create `_dict.sql` with a brief comment so the artifact is explicit.

## Notes
- If the规范 conflicts with user requests, call it out and propose the least-breaking alternative.
- If you cannot access the规范 file, ask the user to provide it.
 - If you cannot write files (permissions or missing repo), output SQL in the response and explain why file output was skipped.

## Resources
- `references/database-design-spec.md`
