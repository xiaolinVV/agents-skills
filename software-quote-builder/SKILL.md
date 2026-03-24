---
name: software-quote-builder
description: Build software-development feature-list quotations from source materials such as PDF, Word, PowerPoint, Excel, images, or mixed requirement packs. Use when the user asks for 软件开发功能清单、报价表、人天估算、工作量报价、需求拆分报价、功能列表转报价单、按总价反推工时, or when raw materials must be converted into an .xlsx quote sheet with 预估工时、单价、总计、汇总.
---

# Software Quote Builder

## Overview

Use this skill to turn raw client requirement materials into a software-development quotation workbook.

This skill is an orchestrator. Reuse existing skills for file extraction, normalize everything into one feature-list model, estimate days conservatively, then generate one final client-facing `.xlsx` quote sheet.

## Default contract

Unless the user overrides it, apply these defaults:

- Quote only **explicit scope** from the provided materials
- Use **800 RMB / person-day** as the day rate
- Use **1 person-day** as the rounding unit
- Produce a **three-level list**: `一级模块 / 二级模块 / 功能点`
- Allow the final quote to stay within **target price ±10%**
- If raw effort falls outside that band, clamp it to the **nearest tolerance boundary** instead of inventing fake scope
- Deliver **one `.xlsx` workbook directly**, not a markdown draft first
- Keep the workbook **client-safe**: no pricing rationale, no tolerance notes, no source-file analysis inside the workbook
- Create a default project workspace under `~/文稿/功能清单报价`, falling back to `~/文档/功能清单报价`, then `~/Documents/功能清单报价`, and finally `~/功能清单报价`
- Copy original source files into the workspace `source/` directory, but **never** move or delete the user’s originals
- Enable the standard client-facing `特殊说明` block by default, unless the user explicitly disables or replaces it
- When the user wants to revise a previously generated quote, find historical workspaces first and continue from the matched latest version instead of rebuilding from scratch

## Delivery mode

### OpenClaw + Feishu channel

When the runtime context clearly indicates the request is running inside OpenClaw on the Feishu channel:

- Send the **actual final `.xlsx` file** back as a Feishu attachment
- Send **only the final quote workbook**, not the template, sample preview, JSON, or intermediate files
- After the attachment is sent, send a **full internal explanation message** to the user in chat
- Read `references/feishu-delivery-template.md` and follow its **exact success template**
- Do **not** send a filesystem path
- Do **not** send a download link
- If attachment sending fails, report the failure clearly and then provide the **local output path** as fallback
- In that case, read `references/feishu-delivery-template.md` and follow its **exact failure fallback template**

### Other channels

When the runtime is not OpenClaw Feishu:

- Return the final generated workbook path
- Return the project workspace directory so the user can find archived source files
- Prefer the compact delivery format in `references/feishu-delivery-template.md`

## Workflow

### 0. Find historical workspaces when the request is a revision

If the user is asking to **修改 / 微调 / 整改 / 续改** a quote that was generated earlier:

1. Search the historical workspace root first:

```bash
python3 scripts/find_quote_workspace.py "报价表名称或项目名"
```

The finder searches across all compatible default roots that exist on the machine, so legacy workspaces under `~/文档` or `~/Documents` still remain discoverable even after `~/文稿` support is added.

2. Show the top candidates with:
   - `project_name`
   - `timestamp`
   - `project_dir`
   - `resume_capability`
3. **Ask the user to confirm the candidate** before modifying anything, even if one candidate scores highest
4. After confirmation, create a **new timestamped revision workspace** from the matched historical project:

```bash
python3 scripts/prepare_quote_workspace.py \
  --project-name "项目名称" \
  --base-project-dir "/path/to/历史项目目录"
```

Historical revision rules:

- Never overwrite the old project directory in place
- Prefer copying the historical `quote-project.json` into the new revision workspace
- If the historical project has no `quote-project.json`, recover a new one from `output/*.xlsx`
- If the workbook also cannot be reused, fall back to `source/` materials and mark the new workspace as source-based regeneration
- If `--root-dir` is not provided, place the new revision workspace under the **same root** as the matched historical project
- The new workspace writes `workspace-manifest.json` so future sessions can find it again without relying on chat context

### 1. Prepare the project workspace

Always prepare a stable workspace before extraction or generation.

Use this command:

```bash
python3 scripts/prepare_quote_workspace.py --project-name "项目名称" file1.pdf file2.docx
```

Read the JSON manifest from stdout and use these paths consistently:

- `source_dir`: archived original materials
- `normalized_dir`: normalized intermediate files
- `output_dir`: final delivery directory
- `output_xlsx`: final workbook path
- `quote_json`: structured base payload to continue editing from
- `workspace_manifest`: persisted project metadata for future lookup

Workspace rules:

- Default root resolution order:
  1. `~/文稿/功能清单报价`
  2. `~/文档/功能清单报价`
  3. `~/Documents/功能清单报价`
  4. `~/功能清单报价`
- Each run creates one timestamped project directory
- Original materials are copied into `source/`
- Never modify or delete the originals in place
- Historical revisions create a **new** timestamped directory and keep the old one untouched

### 2. Normalize the source files

First decide whether the source is already machine-readable or needs conversion.

- **PDF**: follow the `pdf` skill
- **DOCX**: follow the `docx` skill
- **PPTX**: follow the `pptx` skill
- **XLSX/CSV/TSV**: follow the `xlsx` skill for reading/analyzing
- **Images**: use model vision directly
- **Legacy Office formats** (`.doc/.ppt/.xls`) or OpenDocument files (`.odt/.odp/.ods`): run `scripts/normalize_inputs.py` first

Use this command when legacy files are present:

```bash
python3 scripts/normalize_inputs.py --output-dir "$NORMALIZED_DIR" file1.doc file2.ppt file3.xls
```

Read the JSON manifest from stdout and continue with the normalized outputs.

### 3. Decide whether to reuse the original table structure

Use this decision rule:

- **Reuse mode** if the source already contains a stable feature list or requirement table
- **Template mode** if the source is narrative, fragmented, image-heavy, or missing a usable feature table

Choose **reuse mode** when most rows already map cleanly to software features and the table has stable headers such as:

- 模块 / 子模块 / 功能 / 功能点 / 需求项 / 页面 / 描述 / 备注 / 序号

In reuse mode:

- Keep the original functional columns and row order
- Append quotation columns only:
  - `预估工时（人天）`
  - `单价（元/人天）`
  - `小计（元）`
- Add one summary row at the bottom
- If the original file is already an `.xlsx` and formatting preservation matters, follow the `xlsx` skill to update that workbook directly
- If formatting preservation does **not** matter, or the source table came from PDF/DOCX/PPTX extraction, rebuild the table with this skill's workbook generator

Choose **template mode** when the original materials do not already provide a clean feature table.

### 4. Extract the feature list

Reduce every source into the same logical model before quoting:

- `一级模块`
- `二级模块`
- `功能点`
- `功能说明`
- `来源依据`
- `预估工时（人天）`
- `单价（元/人天）`
- `小计（元）`
- `备注`

Do not quote paragraphs. Quote **features**.

Do not create fake precision. Merge tiny related items when the material is too vague to support fine-grained rows.

When multiple files overlap:

- merge duplicates
- keep the clearest wording
- keep internal conflicts or assumptions in the **chat explanation**, not in the workbook

### 5. Estimate person-days

Read `references/estimation-rules.md` before estimating.

Rules:

- Estimate **real work**, not whatever number is needed to flatter the target price
- Keep estimates explainable from the materials
- Quote only explicit scope unless the user explicitly asks to add testing, deployment, training, maintenance, PM, or support items
- Use 1 person-day granularity by default

If the materials are clearly incomplete, still produce the quote but record the uncertainty in the **chat explanation** instead of pretending certainty.

### 6. Align to the target price band

After raw effort is estimated:

1. Compute raw total days and raw total amount
2. Compare raw total amount with the user-provided target price
3. Keep the raw estimate if it already falls inside `target ±10%`
4. If it falls outside that band, scale the item day counts proportionally to the **nearest allowed boundary**
5. Round to whole person-days
6. Fix any rounding drift by adjusting the largest items until the workbook total is internally consistent

Do **not** silently add imaginary scope just to hit a number.

### 7. Generate the workbook

Read `references/output-contract.md` when preparing the JSON payload for the bundled workbook generator.

Use this command:

```bash
python3 scripts/build_quote_workbook.py quote-project.json "$OUTPUT_XLSX"
```

The JSON payload must contain the project-level fields plus either:

- `items` for template mode, or
- `base_columns` + `base_rows` + `items` for reuse mode
- When using the default skill behavior, set:
  - `"special_notes_enabled": true`
  - optionally `"special_notes_merge": "append"` or `"replace"`
  - optionally `"special_notes": ["客户特有说明"]`

The workbook generator writes one client-facing sheet:

- `报价表`

The workbook layout is fixed:

- Row 1: merged title, formatted as `{项目名称}功能清单报价表`
- Row 2: table headers
- Row 3+: detail rows
- Detail rows are followed by one summary row
- If `special_notes_enabled=true`, append a `特殊说明` block below the summary row on the same sheet
- Long-text cells such as `功能说明` and `备注` should keep `wrapText` enabled; the bundled generator estimates row height from the visible text and column width so multiline content is not collapsed by a fixed short row height
- In template mode, keep `功能说明` readable as a client-facing narrative column; prefer concise but complete wording rather than packing multiple unrelated features into one cell

If `project_name` is empty, the title becomes `功能清单报价表`.

## Internal explanation output

After the workbook is created, prepare a chat explanation for the user.

- In OpenClaw Feishu chats, read `references/feishu-delivery-template.md` and use its **exact success or failure template**
- In other channels, prefer the compact template from the same reference
- Do not invent new section titles or reorder the fields casually
- Do not write this explanation into the workbook

## Output requirements

### Template mode columns

Use this exact header order:

1. 序号
2. 一级模块
3. 二级模块
4. 功能点
5. 功能说明
6. 预估工时（人天）
7. 单价（元/人天）
8. 小计（元）
9. 备注

### Reuse mode columns

Keep the original functional columns in front.
Append quotation columns at the right edge in this order:

1. 预估工时（人天）
2. 单价（元/人天）
3. 小计（元）

### Summary row

Always append one bottom summary row containing:

- total days
- total amount

### Special notes block

By default, append these client-facing notes below the summary row:

1. `仅为软件功能开发费用。`
2. `默认包含自项目验收之日起一年的维护期。`
3. `服务器及第三方服务相关费用由客户自行支付。`

Allow the caller to:

- disable the block entirely
- append custom notes
- replace the default notes with custom notes

### Workbook boundaries

Never include these in the workbook:

- 独立的“项目名称”行
- 报价摘要
- 报价说明 sheet
- 目标报价、容差、调整原因、来源文件、关键假设等内部解释信息

The only allowed explanatory content inside the workbook is the client-facing `特殊说明` block at the bottom of the main sheet.

## Sanity checks

Before delivering the workbook, verify these points:

- The row list reflects the actual source materials
- The final amount is either the raw estimate or a clamped amount within the allowed tolerance band
- Every line total equals `预估工时 * 单价`
- The bottom summary equals the sum of all quoted rows
- The workbook title uses `{项目名称}功能清单报价表` or `功能清单报价表`
- The workbook contains only one sheet and no internal explanation content
- If special notes are enabled, they appear below the summary row and do not alter pricing formulas

## Resources

### references/estimation-rules.md
Read this before assigning days.
It contains reusable heuristics for common software feature types and scope boundaries.

### references/output-contract.md
Read this before building the final workbook payload.
It defines the JSON structure expected by `scripts/build_quote_workbook.py`.

### references/feishu-delivery-template.md
Read this before sending the final result back to the user. It defines the fixed chat explanation template for OpenClaw Feishu success, Feishu failure fallback, and non-Feishu delivery.

### scripts/normalize_inputs.py
Use this to normalize legacy Office or OpenDocument inputs into modern formats before extraction.

### scripts/prepare_quote_workspace.py
Use this first to create a stable project workspace, archive original materials, or create a new revision workspace from a historical quote.

### scripts/find_quote_workspace.py
Use this when the user refers to a previously generated quote by name and you need to locate the best historical candidates before continuing.

### scripts/build_quote_workbook.py
Use this to generate the final quote workbook deterministically from structured JSON.

### assets/standard-quote-template.xlsx
Use this as the default blank quotation template when the source materials do not already provide a reusable structure.

### assets/quote-sample-preview.xlsx
Use this filled example workbook to preview the default client-facing layout with realistic sample rows.
