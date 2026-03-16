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
- Prefer the compact delivery format in `references/feishu-delivery-template.md`

## Workflow

### 1. Normalize the source files

First decide whether the source is already machine-readable or needs conversion.

- **PDF**: follow the `pdf` skill
- **DOCX**: follow the `docx` skill
- **PPTX**: follow the `pptx` skill
- **XLSX/CSV/TSV**: follow the `xlsx` skill for reading/analyzing
- **Images**: use model vision directly
- **Legacy Office formats** (`.doc/.ppt/.xls`) or OpenDocument files (`.odt/.odp/.ods`): run `scripts/normalize_inputs.py` first

Use this command when legacy files are present:

```bash
python3 scripts/normalize_inputs.py --output-dir workspace/normalized file1.doc file2.ppt file3.xls
```

Read the JSON manifest from stdout and continue with the normalized outputs.

### 2. Decide whether to reuse the original table structure

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

### 3. Extract the feature list

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

### 4. Estimate person-days

Read `references/estimation-rules.md` before estimating.

Rules:

- Estimate **real work**, not whatever number is needed to flatter the target price
- Keep estimates explainable from the materials
- Quote only explicit scope unless the user explicitly asks to add testing, deployment, training, maintenance, PM, or support items
- Use 1 person-day granularity by default

If the materials are clearly incomplete, still produce the quote but record the uncertainty in the **chat explanation** instead of pretending certainty.

### 5. Align to the target price band

After raw effort is estimated:

1. Compute raw total days and raw total amount
2. Compare raw total amount with the user-provided target price
3. Keep the raw estimate if it already falls inside `target ±10%`
4. If it falls outside that band, scale the item day counts proportionally to the **nearest allowed boundary**
5. Round to whole person-days
6. Fix any rounding drift by adjusting the largest items until the workbook total is internally consistent

Do **not** silently add imaginary scope just to hit a number.

### 6. Generate the workbook

Read `references/output-contract.md` when preparing the JSON payload for the bundled workbook generator.

Use this command:

```bash
python3 scripts/build_quote_workbook.py quote-project.json output.xlsx
```

The JSON payload must contain the project-level fields plus either:

- `items` for template mode, or
- `base_columns` + `base_rows` + `items` for reuse mode

The workbook generator writes one client-facing sheet:

- `报价表`

The workbook layout is fixed:

- Row 1: merged title, formatted as `{项目名称}功能清单报价表`
- Row 2: table headers
- Row 3+: detail rows
- Bottom: summary row

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

### Workbook boundaries

Never include these in the workbook:

- 独立的“项目名称”行
- 报价摘要
- 报价说明 sheet
- 目标报价、容差、调整原因、来源文件、关键假设等内部解释信息

## Sanity checks

Before delivering the workbook, verify these points:

- The row list reflects the actual source materials
- The final amount is either the raw estimate or a clamped amount within the allowed tolerance band
- Every line total equals `预估工时 * 单价`
- The bottom summary equals the sum of all quoted rows
- The workbook title uses `{项目名称}功能清单报价表` or `功能清单报价表`
- The workbook contains only one sheet and no internal explanation content

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

### scripts/build_quote_workbook.py
Use this to generate the final quote workbook deterministically from structured JSON.

### assets/standard-quote-template.xlsx
Use this as the default blank quotation template when the source materials do not already provide a reusable structure.

### assets/quote-sample-preview.xlsx
Use this filled example workbook to preview the default client-facing layout with realistic sample rows.
