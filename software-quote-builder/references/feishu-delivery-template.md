# Feishu Delivery Template

Use this reference when the skill is running inside OpenClaw on the Feishu channel.

## Rules

- Send the final `.xlsx` workbook first as the actual Feishu attachment.
- After the attachment succeeds, send **one** internal explanation message using the exact structure below.
- Do **not** send a filesystem path on success.
- Do **not** send a download link on success.
- Keep the wording direct and stable. Do not improvise section titles.
- If a field is unavailable, write `未提供` instead of omitting the field.

## Success template

Use this exact structure:

```text
已为你生成《{title}》，并已作为飞书附件发送。

【报价结果】
- 目标报价：{target_amount_text}
- 最终报价：{final_amount_text}
- 总工时：{final_days_text}
- 单价：{day_rate_text}
- 区间调整：{adjustment_status}

【材料依据】
- 来源材料：
{source_files_bullets}
- 关键假设：
{assumptions_bullets}

【交付说明】
- 交付方式：飞书附件
- 文件名称：{file_name}
```

### Placeholder rules

- `{title}`: use `{project_name}功能清单报价表` or `功能清单报价表`
- `{target_amount_text}`: for example `¥200,000` or `未提供`
- `{final_amount_text}`: for example `¥198,400`
- `{final_days_text}`: for example `248 人天`
- `{day_rate_text}`: for example `¥800/人天`
- `{adjustment_status}`:
  - `未触发，保留真实工作量`
  - `已触发，按目标报价容差区间调整`
  - `未提供目标报价，仅按默认粒度取整`
- `{source_files_bullets}`: one bullet per item, for example:
  - `  - 零售供应链平台需求说明.pdf`
  - `  - 零售供应链平台原型图.pptx`
- `{assumptions_bullets}`: one bullet per item, for example:
  - `  - 仅按原始材料中明确出现的功能范围报价`
  - `  - 未单列实施培训、上线支持、运维保障`
- `{file_name}`: the final workbook file name only, not a full path

## Failure fallback template

If the workbook was generated but Feishu attachment sending failed, use this exact structure:

```text
《{title}》已生成，但飞书附件发送失败。

【报价结果】
- 目标报价：{target_amount_text}
- 最终报价：{final_amount_text}
- 总工时：{final_days_text}
- 单价：{day_rate_text}
- 区间调整：{adjustment_status}

【材料依据】
- 来源材料：
{source_files_bullets}
- 关键假设：
{assumptions_bullets}

【交付说明】
- 交付方式：飞书附件发送失败，改为返回本地路径
- 本地路径：{local_output_path}
- 文件名称：{file_name}
```

### Failure rules

- Include the local output path only in the failure fallback.
- Do not add apology fluff.
- State the failure plainly and keep the rest of the explanation unchanged.

## Non-Feishu compact template

When the runtime is not OpenClaw Feishu, prefer this compact structure:

```text
《{title}》已生成。
- 最终报价：{final_amount_text}
- 总工时：{final_days_text}
- 单价：{day_rate_text}
- 文件路径：{local_output_path}
```

Use the longer success/failure templates only for the Feishu channel.
