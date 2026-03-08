# Workflow Contract

## 1) 双源组织模式

- `framework-source`：原流程，不变。
  - 克隆源固定 `jeecg-boot_3`
  - 业务命名工作区
  - 创建业务组织与仓库
  - `origin` 指向业务组织，`upstream` 指向 `jeecg-boot_3`
- `user-source`：新增流程。
  - 先列出账号组织并由用户选择 `source_org`
  - 一级目录固定为 `source_org`
  - 保持 `origin` 为 `source_org`
  - 回补 `upstream=jeecg-boot_3`

## 2) 默认仓库集合

- 必选仓库（5 个）：
  - `jeecg-boot`
  - `ant-design-vue-jeecg`
  - `docs`
  - `bmad`（本地目录改名为 `_bmad`）
  - `bmad-output`（本地目录改名为 `_bmad-output`）
- 可选仓库（按需显式启用）：
  - `jeecg-uniapp`
  - `openspec`

## 3) 确认闸门

### framework-source（保持原流程）
- Gate 1：
  - 一级目录候选与选定名称
  - 初始化父目录
  - 仓库集合
- Gate 2：
  - 新业务组织与仓库创建
  - remote 改写
  - 自动 push

### user-source（新增）
- Gate 1：
  - 仅确认初始化父目录
  - 一级目录不确认，默认 `source_org`
- Gate 2：
  - 批量设置 upstream
  - `git ls-remote upstream` 校验
  - 自动 push

## 4) SSH URL 规则（强制）

- 所有 Gitee Git 交互一律使用 SSH：`git@gitee.com:<org>/<repo>.git`
- 适用范围：克隆、`origin`、`upstream`
- SSH 失败处理：立即中止，不自动回退 HTTPS

## 5) 本地目录映射规则

| 上游仓库 | 本地目录 |
|---|---|
| `jeecg-boot` | `jeecg-boot` |
| `ant-design-vue-jeecg` | `ant-design-vue-jeecg` |
| `docs` | `docs` |
| `bmad` | `_bmad` |
| `bmad-output` | `_bmad-output` |
| `jeecg-uniapp` | `jeecg-uniapp` |
| `openspec` | `openspec` |

## 6) BMAD 初始化命令（固定 quick-update）

```bash
npx bmad-method@6.0.3 install \
  --directory . \
  --modules bmm \
  --tools codex,claude-code \
  --action quick-update \
  --yes
```

执行前置条件：`_bmad` 与 `_bmad-output` 已存在或已就位。

## 7) BMAD 验证（强制）

每次执行初始化/更新后，必须执行 `/bmad-help` 验证命令链路可用。

## 8) 远程映射规则

- framework-source：
  - `origin = git@gitee.com:<business_org>/<repo>.git`
  - `upstream = git@gitee.com:jeecg-boot_3/<repo>.git`
- user-source：
  - `origin` 保持克隆源组织（SSH）
  - `upstream = git@gitee.com:jeecg-boot_3/<repo>.git`
- BMAD 两仓注意：
  - 本地目录用 `_bmad`、`_bmad-output`
  - 远程仓库名仍用 `bmad`、`bmad-output`

## 9) 输出要求

每次执行完必须输出：
- 已完成动作列表
- 模式与 Gate 确认摘要
- 每仓 remote 检查结果
- 每仓 upstream 校验结果
- push 结果
- `/bmad-help` 验证结果
- 失败清单与重试命令

## 10) 参考流程文档

若本地存在以下文档，先读取并遵循其中约束：
- `/home/fjhc/dev/jeecg-boot/docs/architecture/development-flows/bmad-v6-multi-repo-initialization-flow.md`
