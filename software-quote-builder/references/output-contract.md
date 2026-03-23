# Output Contract for build_quote_workbook.py

Prepare a JSON file and pass it to `scripts/build_quote_workbook.py`.

## Top-level fields

```json
{
  "project_name": "客户项目名称",
  "target_amount": 200000,
  "day_rate": 800,
  "tolerance_pct": 10,
  "rounding_unit": 1,
  "mode": "template",
  "source_files": ["需求说明.pdf", "原型图.pptx"],
  "assumptions": [
    "只按材料中明确出现的功能报价",
    "未单列部署、培训、运维"
  ],
  "special_notes_enabled": true,
  "special_notes_merge": "append",
  "special_notes": [
    "如需驻场支持，另行评估"
  ],
  "items": []
}
```

### Required behavior

- `day_rate` defaults to `800` if omitted
- `tolerance_pct` defaults to `10` if omitted
- `rounding_unit` defaults to `1` if omitted
- `mode` may be `template` or `reuse`
- `items` is required in both modes
- `source_files` and `assumptions` may still be provided, but they are for **chat explanation** only, not workbook rendering
- `special_notes_enabled` defaults to `false` inside the generator for backward compatibility
- The bundled skill should explicitly set `special_notes_enabled=true` when it wants the standard client-facing note block

## Special notes fields

These fields control the optional note block appended **inside the main `报价表` sheet**, below the summary row.

- `special_notes_enabled`: `true` or `false`
- `special_notes_merge`: `append` or `replace`
- `special_notes`: string array, each item becomes one numbered line

Behavior:

1. If `special_notes_enabled` is `false`, the note block is omitted entirely
2. If `special_notes_enabled` is `true` and `special_notes` is empty, the generator uses the standard default notes
3. If `special_notes_merge` is `append`, the generator writes the default notes first and then appends custom notes
4. If `special_notes_merge` is `replace`, the generator writes only the custom notes

Standard default notes:

1. `仅为软件功能开发费用。`
2. `默认包含自项目验收之日起一年的维护期。`
3. `服务器及第三方服务相关费用由客户自行支付。`

## Item fields

Each item may contain these fields:

```json
{
  "seq": 1,
  "module_l1": "用户中心",
  "module_l2": "账号管理",
  "feature": "登录/退出",
  "description": "账号密码登录、退出、基础校验",
  "source_ref": "需求说明第 3 页",
  "estimated_days": 3,
  "note": "基础认证，不含单点登录"
}
```

### Required item fields for template mode

- `module_l1`
- `module_l2`
- `feature`
- `description`
- `estimated_days`

### Optional item fields

- `seq`
- `source_ref`
- `note`

If `note` is empty and `source_ref` exists, the generator writes `source_ref` into the 备注 column.

## Reuse mode payload

In `reuse` mode, add the original table structure:

```json
{
  "mode": "reuse",
  "base_columns": ["序号", "模块", "功能点", "说明"],
  "base_rows": [
    ["1", "用户中心", "登录/退出", "基础认证"],
    ["2", "用户中心", "用户资料", "个人信息维护"]
  ],
  "items": [
    {"estimated_days": 3, "note": "需求说明第 3 页"},
    {"estimated_days": 2, "note": "需求说明第 4 页"}
  ]
}
```

### Reuse mode rules

- `base_columns` and `base_rows` must be present
- `len(items)` must equal `len(base_rows)`
- The generator appends quotation columns to the right of the original columns
- The generator adds one summary row at the bottom

## Budget scaling behavior

The generator can rescale item days automatically.
It always:

1. computes the raw amount from `estimated_days * day_rate`
2. compares it against `target_amount ± tolerance_pct`
3. keeps the raw amount if already inside the allowed band
4. otherwise scales all items proportionally to the nearest boundary
5. rounds to `rounding_unit`
6. adjusts the largest items only when needed to remove rounding drift

## Output workbook

The generator writes exactly **one** sheet:

- `报价表`

### Visual layout

- Row 1: merged title, formatted as `{项目名称}功能清单报价表`
- Row 2: table headers
- Row 3+: detail rows
- Detail rows are followed by one summary row
- If enabled, append a client-facing `特殊说明` block below the summary row on the same sheet
- If `project_name` is empty, the title becomes `功能清单报价表`

### Workbook exclusions

The workbook must **not** contain:

- 独立的“项目名称”行
- 报价摘要
- 报价说明 sheet
- 目标报价、容差、调整原因、来源文件、关键假设等内部解释信息

The workbook **may** contain only one client-facing note area:

- 主表底部的 `特殊说明` 区

## Chat explanation contract

The caller should generate a separate chat explanation after the workbook is built.

- In OpenClaw Feishu chats, use the exact template in `references/feishu-delivery-template.md`
- In other channels, use the compact template from the same reference
- The explanation must cover: 项目名称、目标报价、最终报价、总工时、单价、区间调整状态、来源材料、关键假设、最终交付方式
- Keep the explanation outside the workbook

## Minimal template mode example

```json
{
  "project_name": "OA 系统升级",
  "target_amount": 200000,
  "day_rate": 800,
  "mode": "template",
  "special_notes_enabled": true,
  "items": [
    {
      "module_l1": "用户中心",
      "module_l2": "账号管理",
      "feature": "登录/退出",
      "description": "账号密码登录、退出、基础校验",
      "estimated_days": 3,
      "source_ref": "需求说明第 3 页"
    },
    {
      "module_l1": "审批管理",
      "module_l2": "流程发起",
      "feature": "请假申请",
      "description": "发起、保存草稿、提交审批",
      "estimated_days": 5,
      "source_ref": "需求说明第 5-6 页"
    }
  ]
}
```
