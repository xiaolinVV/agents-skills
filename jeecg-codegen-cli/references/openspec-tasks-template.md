# OpenSpec Tasks Template (jeecg-codegen-cli)

Use this checklist in `openspec/changes/<id>/tasks.md` when the proposal requires CLI code generation.

```
## 1. Implementation
- [ ] 1.1 确认 DDL/字典、jspMode、输出路径（后端/前端）与主子表关系
- [ ] 1.2 生成 spec（DDL→spec，spec-out 绝对路径）
- [ ] 1.3 校验 spec（BigDecimal 全限定名、树表 extendParams、外键 foreignKeys）
- [ ] 1.4 dry-run 输出清单核对
- [ ] 1.5 CLI 渲染生成代码（**审批通过后执行**）
- [ ] 1.6 验收要点核对（实体/映射/Vue/字典/树/一对多结构）
```

Notes:
- JVXE/ERP/innerTable/tab: repeat steps 1.2–1.6 per jspMode.
- OpenSpec rule: do not run CLI rendering before proposal approval.
