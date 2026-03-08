# Conventional Commit 约定（中文）

## 目标

- 保持标题统一：`type(scope): subject`
- `type` 固定英文，`subject` 使用中文一句话
- 每个仓库独立生成消息，避免跨仓复用同一描述

## type 判定顺序

1. `docs`：所有改动均为文档类文件
2. `fix`：分支名包含 `fix/bug/hotfix/issue`
3. `feat`：分支名包含 `feat/feature`
4. `refactor`：分支名包含 `refactor/cleanup/tidy`
5. `chore`：分支名包含 `chore/build/deps/ci` 或改动仅为工程元文件
6. 兜底：`feat`

## subject 模板

- `docs(scope): 更新{area}文档与说明`
- `fix(scope): 修复{area}相关缺陷`
- `feat(scope): 完善{area}相关功能`
- `refactor(scope): 重构{area}相关实现`
- `chore(scope): 更新{area}工程配置`

## BMad 约定

- 仅当同时满足以下条件时启用 BMAD 提交模式：
  - 位于 BMAD 工作区（存在 `_bmad` 或 `_bmad-output`）
  - 当前分支可提取 `story-id`，例如 `feat/story-123-add-login`
- BMAD 标题格式：`type(scope): [story-id] 中文一句话`
- `scope` 继续保留仓库/模块语义，不要直接把 `scope` 全部替换成 `story-id`
- 如果命中 BMAD 工作区但没有识别出 `story-id`：
  - 标题回退为普通 Conventional Commit
  - body 增加一行提示，说明已检测到 BMAD 上下文但未识别到 `story-id`

## body 模板

建议 3-4 行即可，优先给出可核对的信息：

- 变更文件数量
- 新增/修改/删除/重命名分布
- 主要路径
- 可选：`git diff --cached --shortstat` 统计信息

如果启用 BMAD 模式，再追加：

- BMad 上下文识别依据
- `story-id`

## 多仓策略

- 每个仓库单独生成标题和正文
- 不要在多个仓库之间复用同一条 subject
- 先 commit，再立即 push 到当前分支 upstream
- 默认输出详细总结，至少包含提交模式、story-id、主要路径、差异统计、成功/失败状态和下一步建议
