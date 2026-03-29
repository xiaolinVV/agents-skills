# Epic Report Contract

## Purpose

Turn the Epic summary into a final delivery report instead of a sparse queue log.

## Output Targets

The same report structure should be used for:
- terminal final report block
- `epic-summary-*.md`

## Success Report Sections

A successful Epic report should contain these sections in order:

1. **顶部交付完成块**
   - Epic 编号 / 名称
   - 最终结果：`done`
   - formal Epic status: `done`
   - Story 状态清单（done / skipped-already-done）

2. **总计**
   - 完成数 / 总数
   - skipped already-done 数量
   - Epic 状态

3. **功能总结表格**
   - `Story`
   - `功能`
   - `测试数`
   - `Git`

4. **测试总计**
   - Epic 本次新增测试总数
   - 通过数
   - 失败数
   - QA skipped story 数

5. **Epic 能力总结**
   - 4-8 条高层能力结论
   - source should aggregate story-level `delivery_summary`

6. **Retro 提示**
   - retrospective 未自动执行
   - 如需执行，单独运行 retrospective

## Partial / Blocked Report Sections

A partial-completion or blocked Epic report should contain:

1. 顶部部分完成块
2. 已跳过的已完成 Story
3. 本次执行的 Story
4. 首个阻断 Story
5. 当前 formal Epic status（通常仍为 `in-progress`）
6. 恢复入口与说明

## Table Rules

For the 功能总结表格:
- `Story`: show story id
- `功能`: summarize from `delivery_summary`
- `测试数`: use `qa_metrics.tests_total`, or `N/A` for skipped QA
- `Git`: show commit short hash or `push failed` / `skipped`

## Formatting Rules

- use `document_output_language`
- keep terminal and Markdown report sections aligned
- prefer readable Markdown over decorative complexity
