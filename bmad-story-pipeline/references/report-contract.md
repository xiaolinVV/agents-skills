# Story Report Contract

## Purpose

Turn the final story summary into a delivery report, not just a sparse gate log.

## Output Targets

The same report structure should be used for:
- terminal final report block
- `final-summary-*.md`

## Success Report Sections

A successful story final report should contain these sections in order:

1. **顶部完成块**
   - Story ID / Story Key / title
   - 最终结果：`done`
   - formal story status: `done`

2. **Gate 结果**
   - create
   - validate
   - dev
   - qa
   - review

3. **本次落地内容**
   - 3-6 条能力总结
   - source should prefer the structured `delivery_summary`

4. **测试摘要**
   - 测试总数
   - 通过数
   - 失败数
   - if skipped, show `Skipped` or `N/A` with reason

5. **Git Sync**
   - synced repos
   - commit subjects
   - push success/failure

6. **残留说明**
   - what is intentionally left for later stories or later environments

7. **一句话交付结论**
   - concise sentence describing what the system now gains from this story

## Failure / Blocked Report Sections

A blocked story report should contain:

1. 顶部阻断块
2. 当前 story id / key
3. runtime outcome
4. formal story status (unchanged BMAD status)
5. 当前阻断 gate / clarification scope
6. 已完成的 gates
7. 恢复方式

## Formatting Rules

- use `document_output_language`
- prefer short sections and bullets
- do not invent table-heavy formatting for single-story reports unless the content benefits from it
