# Archived: jeecg36-vue2-multi-repo-init

归档日期：2026-07-30。

本目录不再提供可自动发现的 `SKILL.md`，相关 Agent 链接已撤销。内容仅保留 JeecgBoot 3.6.x + Vue2 的 Gitee 多仓流程；其中账号硬编码已清除，远端写操作保留显式 Gate 和 dry-run 约束。

以下内容不得用于 3.9.x、Vue3 或当前项目。

---
name: jeecg36-vue2-multi-repo-init
description: "Initialize legacy JeecgBoot 3.6.x + Vue2 multi-repo workspaces from Gitee jeecg-boot_3, including ant-design-vue-jeecg, BMAD v6 quick-update, multi-root workspace generation, and SSH origin/upstream setup. Use only when the user explicitly requests this legacy Gitee workflow. Do not use for JeecgBoot 3.9.x, jeecgboot-vue3, monorepos, GitHub workflows, or unspecified current-version scaffolds."
---

# JeecgBoot 3.6.x Vue2 Multi Repo Init

## Overview
执行 JeecgBoot 3.6.x + Vue2 遗留多仓脚手架初始化，统一支持两种源组织模式：
- `framework-source`：保持原有流程不变（从 `jeecg-boot_3` 启动，业务命名目录，创建业务组织与仓库）。
- `user-source`：由用户选择任意已有组织作为克隆源，快速落地并回补 `upstream`，最后不自动 push。

全局强制规则：
- **Gitee 一律使用 SSH URL**（克隆、`origin`、`upstream` 全部走 SSH）。
- SSH 失败时立即中止并给修复命令，禁止自动回退 HTTPS。
- `bmad` 与 `bmad-output` 本地目录必须改为 `_bmad`、`_bmad-output`。
- BMAD 初始化固定用 `quick-update` 动作，并且执行后必须验证 `/bmad-help`。

## Compatibility Gate

本 Skill 只处理以下遗留契约：

- 后端版本线为 JeecgBoot 3.6.x。
- PC 前端仓库名和本地目录均为 `ant-design-vue-jeecg`。
- 上游组织是用户明确确认的 `jeecg-boot_3`，Git 托管平台是 Gitee。
- 用户明确要求多仓初始化，而不是当前项目的仓库内初始化。

发现 `jeecgboot-vue3`、JeecgBoot 3.9.x、单体仓库或项目级初始化 Skill 时立即停止。不要猜测新版仓库集合，也不要把本遗留映射套到当前框架。

## Source Mode Decision
先判定模式，再执行对应流程：
1. 用户明确说“按原流程初始化/创建业务组织”时，用 `framework-source`。
2. 用户明确说“从我已有组织克隆”时，用 `user-source`。
3. 用户未说明时，默认 `framework-source`。

## Repository Set
默认仓库集合：
- `jeecg-boot`
- `ant-design-vue-jeecg`
- `docs`
- `bmad`
- `bmad-output`

可选仓库（仅用户明确要求时加入）：
- `jeecg-uniapp`
- `openspec`

## URL Policy (SSH First)
统一 URL 规则：
- 克隆：`git@gitee.com:<org>/<repo>.git`
- `origin`：`git@gitee.com:<org>/<repo>.git`
- `upstream`：`git@gitee.com:jeecg-boot_3/<repo>.git`

SSH 失败时必须中止并提示：
```bash
ssh -T git@gitee.com
ssh-add -l
```

## Flow A: framework-source（原流程保持不变）

### Gate 1（保持原流程）
确认以下项目：
1. 项目简介（用于生成 5 个一级目录候选名）
2. 一级目录名称（从候选中选择）
3. 初始化父目录
4. 仓库集合（默认 5 仓 + 可选仓）

### Gate 1 后自动执行
1. 在目标父目录创建业务一级目录。
2. 从 `git@gitee.com:jeecg-boot_3/<repo>.git` 克隆仓库。
3. 重命名目录：`bmad -> _bmad`，`bmad-output -> _bmad-output`。
4. 执行 BMAD 初始化（固定 quick-update）：
   ```bash
   npx bmad-method@6.0.3 install \
     --directory . \
     --modules bmm \
     --tools codex,claude-code \
     --action quick-update \
     --yes
   ```
5. 执行 `/bmad-help` 验证安装链路。
6. 生成 `<workspace_name>.code-workspace`。

### Gate 2（保持原流程）
确认以下项目：
1. 新业务组织名称
2. 新组织下仓库创建清单（默认私有）
3. remote 改写与自动 push

### Gate 2 后自动执行
1. 用 Playwright 在用户账号下创建业务组织。
2. 在业务组织中创建对应仓库。
3. 批量设置 remote（全部 SSH）：
   - `origin -> git@gitee.com:<business_org>/<repo>.git`
   - `upstream -> git@gitee.com:jeecg-boot_3/<repo>.git`
4. 自动 push 当前分支到新 `origin`。

## Flow B: user-source（新增）

### 组织选择阶段
1. 使用 Playwright 打开 Gitee。
2. 枚举并展示“用户账号下所有组织”。
3. 让用户选择 `source_org`。

### Gate 1（按新规则）
只确认一项：
1. 初始化父目录

> 一级目录不再确认，固定使用 `workspace_name = source_org`。

### Gate 1 后自动执行
1. 在 `parent_dir/source_org` 创建工作区目录。
2. 从 `git@gitee.com:<source_org>/<repo>.git` 克隆仓库。
3. 重命名目录：`bmad -> _bmad`，`bmad-output -> _bmad-output`。
4. 强制执行 BMAD 初始化（quick-update）。
5. 执行 `/bmad-help` 验证。
6. 生成 `<source_org>.code-workspace`。

### Gate 2
确认以下项目：
1. 批量设置 `upstream=jeecg-boot_3`（SSH）
2. `git ls-remote upstream` 校验

> `user-source` 最后一步禁止自动 push，避免把初始化后的本地状态直接写回用户现有组织。

### Gate 2 后自动执行
1. 保持 `origin` 为克隆源组织（SSH），不创建新组织。
2. 批量设置 `upstream -> git@gitee.com:jeecg-boot_3/<repo>.git`。
3. 逐仓执行 `git ls-remote upstream`。
4. 输出完成报告，明确标注 `push=skipped (user-source disabled)`。

## Gitee Login Fallback
登录态失效时按固定顺序执行：
1. 选择短信登录。
2. 要求用户在浏览器中自行输入手机号；禁止从 Skill、日志或仓库读取、保存账号标识。
3. 点击“获取验证码”。
4. 向用户索取验证码。
5. 输入验证码后继续。

## Repository Mapping Rules
保持以下映射，不要把 `_bmad` 当成远程仓名：
- `jeecg-boot` <-> `jeecg-boot`
- `ant-design-vue-jeecg` <-> `ant-design-vue-jeecg`
- `docs` <-> `docs`
- `_bmad` <-> `bmad`
- `_bmad-output` <-> `bmad-output`

## Reporting Rules
每次执行后输出统一报告：
- 已完成动作清单
- 模式与 Gate 关键确认项
- 每仓 `origin` / `upstream`
- 每仓 upstream 校验结果
- 每仓 push 结果（未执行时明确标注 `skipped`）
- `/bmad-help` 验证结果
- 失败步骤与重试命令

## Script Usage
- 候选名：`scripts/generate_workspace_names.py`
- 工作区文件：`scripts/create_multiroot_workspace.py`
- remote 回写：`scripts/rewrite_git_remotes.py`

`rewrite_git_remotes.py` 推荐用法：
```bash
# 所有实际 remote 改写前先增加 --dry-run 检查目标

# framework-source: 更新 origin + upstream（默认SSH）
scripts/rewrite_git_remotes.py \
  --mode framework-source \
  --workspace-root <root> \
  --org <business_org> \
  --verify-upstream-ls-remote \
  --push

# user-source: 保持 origin，仅更新 upstream（默认SSH），最后不 push
scripts/rewrite_git_remotes.py \
  --mode user-source \
  --workspace-root <root> \
  --verify-upstream-ls-remote
```

## References
- `references/workflow-contract.md`
- `references/playwright-gitee-checklist.md`
- 若当前遗留工作区存在 `docs/architecture/development-flows/bmad-v6-multi-repo-initialization-flow.md`，执行前读取它。
