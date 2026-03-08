# Jeecg-boot代码生成执行规范（CLI）

> 目标：跳过 Jeecg-boot Online 表单配置 UI，保留 FreeMarker 模板生成逻辑，让 AI 直接从 DDL/业务描述生成标准代码。

---

## 0. 强约束与目标（必须遵守）

1. **模板驱动不可替代**：最终代码**必须通过官方 FreeMarker 模板渲染生成**，禁止“AI 直接拼代码”替代模板输出。
2. **唯一数据模型**：生成入口只允许使用 `jeecg-codegen-cli` 的 `CodegenSpec`；`TableVo/ColumnVo/SubTableVo` 仅为 CLI 内部构造，不允许自行维护影子模型。
3. **控件白名单**：仅允许使用 Vue2 模板已显式支持的控件类型；若需新增控件类型，必须先扩展模板并走 OpenSpec proposal。
4. **失败优先**：控件不支持、字段不完整、关系不确定时必须**阻断生成**，禁止“自动退化/默认兜底”。
5. **输出一致性**：生成结果需与官方 Online 表单生成器输出保持结构与风格一致（路径、命名、注解、权限编码、Vue 组件引用）。
6. **“不用 UI，但遵循 UI 规则”**：不再手工配置 Online 表单，但其元数据规则仍是唯一规范。
7. **布尔字段规范**：模板判断全部基于字符串，`Y/N` 是唯一合法值（如 `isShow/isQuery/isShowList/isKey/readonly/sort/nullable` 等）。

## 1. 模板语义提取

### 1.1 模板目录结构

模板根路径：`jeecg-module-system/jeecg-system-biz/src/main/resources/jeecg/code-template-online/`

| jspMode | 结构类型 | stylePath | 输出 |
|---------|---------|-----------|------|
| `one` | 单表 | `default/one` | Controller/Service/Mapper/Entity/Vue |
| `tree` | 树表 | `default/tree` | 同上 + 树查询逻辑 |
| `many` | 一对多(经典) | `default/onetomany` | 主表 + 子表全套 |
| `jvxe` | 一对多(JVXE) | `jvxe/onetomany` | JVXE 子表编辑 |
| `erp` | 一对多(ERP) | `erp/onetomany` | 子表列表 + 弹窗 |
| `innerTable` | 一对多(内嵌) | `inner-table/onetomany` | 子表内嵌组件 |
| `tab` | 一对多(Tab) | `tab/onetomany` | 子表 Tab 切换 |

### 1.2 核心配置对象模型（唯一入口：CodegenSpec）

FreeMarker 模板不直接吃“自定义结构”，**唯一合法入口**是 `jeecg-codegen-cli` 的 `CodegenSpec`。你要做的，只是把 DDL/描述映射成这个结构。

#### CodegenSpec（全局配置）
```java
class CodegenSpec {
  String jspMode;              // one/tree/many/jvxe/erp/innerTable/tab
  String projectPath;          // 输出目录
  String templatePath;         // 可选，空则用内置模板
  String bussiPackage;         // 可选
  String sourceRootPackage;    // 可选
  String webRootPackage;       // 可选
  String primaryKeyField;      // 可选
  String vueStyle;             // 可选
  String frontendRoot;         // 可选，前端输出根目录（Vue 输出重定向）；空则跳过前端拷贝

  TableSpec table;             // 必填
  List<ColumnSpec> columns;    // 必填
  List<SubTableSpec> subTables;// 一对多必填
}
```

#### TableSpec（表级配置）
```java
class TableSpec {
  String tableName;            // 物理表名
  String entityPackage;        // 包路径（如 demo）
  String entityName;           // 实体类名（大驼峰）
  String ftlDescription;       // 功能描述
  String primaryKeyPolicy;     // 主键策略
  String sequenceCode;         // 序列（如有）
  Integer fieldRowNum;         // 表单列数
  Integer searchFieldNum;      // 查询字段数
  Integer fieldRequiredNum;    // 必填字段数
  Map<String, Object> extendParams; // 扩展参数
}
```

#### ColumnSpec（字段级配置）
```java
class ColumnSpec {
  // === 数据库属性 ===
  String fieldDbName;          // 物理字段名（下划线）
  String fieldName;            // Java属性名（小驼峰）
  String fieldType;            // Java类型（String/Integer/Long/BigDecimal/Date）
  String fieldDbType;          // DB类型（string/int/double/BigDecimal/Datetime/Date/Blob）
  String charmaxLength;        // 长度
  String precision;            // 精度
  String scale;                // 小数位
  String nullable;             // 是否允许空（Y/N）
  String classType;            // 控件类型（核心）
  String classTypeRow;         // 特殊场景（可空）
  String optionType;           // 选项类型（可空）

  // === 表单/查询属性 ===
  Integer fieldLength;         // 表单展示长度
  String fieldHref;            // Href配置
  String fieldValidType;       // 校验规则编码
  String fieldDefault;         // 数据库默认值
  String fieldShowType;        // 控件类型（建议与 classType 一致）
  Integer fieldOrderNum;       // 排序号
  String isKey;                // 是否主键（Y/N）
  String isShow;               // 表单是否显示（Y/N）
  String isShowList;           // 列表是否显示（Y/N）
  String isQuery;              // 是否查询条件（Y/N）
  String queryMode;            // single/group
  String dictField;            // 字典Code
  String dictTable;            // 字典表名
  String dictText;             // 字典显示字段
  String sort;                 // 是否排序（Y/N）
  String readonly;             // 是否只读（Y/N）
  String defaultVal;           // 表单默认值
  String uploadnum;            // 上传数量限制
  Map<String, Object> extendParams; // 扩展参数
}
```

> **注意**：当使用 `--input` 读取既有 spec 时，`BigDecimal` 必须写成 `java.math.BigDecimal`（全限定名），否则生成的 VO 可能缺少 import 而导致编译失败。若使用 `--ddl` 重新生成 spec，则会自动输出正确类型。

#### SubTableSpec（一对多子表配置）
```java
class SubTableSpec {
  String tableName;
  String entityPackage;        // 可空，默认主表包
  String entityName;
  String ftlDescription;
  String primaryKeyPolicy;
  String sequenceCode;
  String foreignRelationType;  // 0/1
  List<String> foreignKeys;    // 必填
  List<String> foreignMainKeys;// 必填
  List<ColumnSpec> columns;    // 必填
  List<ColumnSpec> originalColumns; // 可空
  Map<String, Object> extendParams;
}
```

**结论**：`TableVo/ColumnVo/SubTableVo` 只存在于 CLI 内部构造，外部输入必须是 `CodegenSpec`。

### 1.3 控件类型清单（classType）

| 控件类型 | Vue组件 | 适用场景 |
|---------|--------|---------|
| `default` | `<a-input />` | 普通文本（**显式映射为默认分支**） |
| `date` | `<j-date />` | 日期选择 |
| `datetime` | `<j-date :show-time="true" />` | 日期时间 |
| `time` | `<j-time />` | 时间选择 |
| `textarea` | `<a-textarea />` | 多行文本 |
| `password` | `<a-input-password />` | 密码输入 |
| `list` | `<j-dict-select-tag type="list" />` | 下拉选择 |
| `radio` | `<j-dict-select-tag type="radio" />` | 单选框 |
| `checkbox` | `<j-multi-select-tag type="checkbox" />` | 复选框 |
| `list_multi` | `<j-multi-select-tag type="list_multi" />` | 多选下拉 |
| `sel_search` | `<j-search-select-tag />` | 搜索下拉 |
| `sel_user` | `<j-select-user-by-dep />` | 用户选择 |
| `sel_depart` | `<j-select-depart />` | 部门选择 |
| `sel_tree` | `<j-tree-select />` | 树形下拉 |
| `cat_tree` | `<j-category-select />` | 分类字典树 |
| `popup` | `<j-popup />` | 弹窗选择 |
| `switch` | `<j-switch />` | 开关 |
| `file` | `<j-upload />` | 文件上传 |
| `image` | `<j-image-upload />` | 图片上传 |
| `umeditor` | `<j-editor />` | 富文本 |
| `markdown` | `<j-markdown-editor />` | Markdown |
| `pca` | `<j-area-linkage />` | 省市区 |

> **注意**：UI 可选控件 ≠ 模板可生成控件。**只允许上述控件类型**；其余类型必须阻断并给出错误。  
> `default` 是唯一允许的“普通输入”映射，不把未知控件当默认。

### 1.4 校验规则编码

| 编码 | 含义 | 正则/逻辑 |
|-----|------|----------|
| `*` | 必填 | `required: true` |
| `only` | 唯一 | 远程校验 |
| `n6-16` | 6-16位数字 | `/^\d{6,16}$/` |
| `*6-16` | 6-16位任意 | `/^.{6,16}$/` |
| `e` | 邮箱 | 邮箱正则 |
| `m` | 手机 | `/^1[3456789]\d{9}$/` |
| `url` | 网址 | URL正则 |
| `n` | 数字 | `/^-?\d+\.?\d*$/` |
| `z` | 整数 | `/^-?\d+$/` |
| `money` | 金额 | 金额正则 |

---

### 1.5 字段值规范（必须）

**字符串枚举值（模板硬编码判断）**  
- `isShow/isShowList/isQuery/isKey/readonly/sort/nullable`：仅允许 `Y` 或 `N`  
- `queryMode`：`single` 或 `group`  
- `jspMode`：`one/tree/many/jvxe/erp/innerTable/tab`  

**必填与默认值**  
- `columns` 不能为空；一对多模式 `subTables` 不能为空且每个子表必须有 `foreignKeys/foreignMainKeys`。  
- `classType` 必须在模板支持列表内，否则直接失败。  
- `fieldDbType` 必须与 `fieldType` 语义一致（如 `Datetime` → `Date`）。  

## 2. 元数据映射机制

### 2.1 DDL → 配置对象的自动推导

AI 需要从 DDL 自动推导出 `CodegenSpec.TableSpec` 和 `ColumnSpec[]`，核心映射规则：

#### 2.1.1 表级推导

```
DDL: CREATE TABLE `order_main` (...)
     ↓
CodegenSpec.table:
  tableName = "order_main"
  entityName = "OrderMain"          // 下划线转大驼峰
  entityPackage = "order"           // 取表名前缀或由AI推断
  ftlDescription = "订单主表"        // 从COMMENT或AI推断
  fieldRowNum = 2                   // 默认2列，可配置
```

#### 2.1.2 字段级推导（核心智能映射）

```yaml
# 数据库类型 → Java类型
VARCHAR/CHAR      → String
INT/TINYINT       → Integer
BIGINT            → Long
DECIMAL/NUMERIC   → BigDecimal
DOUBLE/FLOAT      → Double
DATE              → Date (fieldDbType=Date)
DATETIME/TIMESTAMP→ Date (fieldDbType=Datetime)
TEXT/LONGTEXT     → String (fieldDbType=Text)
BLOB              → byte[] (fieldDbType=Blob)

# 字段名 → 控件类型（语义推断）
*_status/*_state  → list + 字典
*_type/*_category → list + 字典
*_time/*_date     → date/datetime
create_time       → datetime + 隐藏
update_time       → datetime + 隐藏
create_by         → default + 隐藏
update_by         → default + 隐藏
*_id (外键)       → popup/sel_search
sex/gender        → radio + sex字典
phone/mobile      → default + 手机校验(m)
email             → default + 邮箱校验(e)
*_url/*_link      → default + URL校验
*_file/*_attach   → file
*_img/*_image/*_pic → image
*_content/*_desc  → textarea/umeditor
*_remark/*_note   → textarea
*_money/*_amount/*_price → default + money校验（由 fieldDbType 触发数字控件）
is_*              → switch
sort/*_order      → default（由 fieldDbType 触发数字控件）
```

**字段落地到 ColumnSpec（必须）**  
- `fieldDbName`：DDL 字段名  
- `fieldName`：下划线转小驼峰  
- `fieldDbType`：按 DB 类型映射（`Datetime/Date/BigDecimal` 等）  
- `fieldType`：Java 类型（String/Integer/Long/BigDecimal/Date）  
- `charmaxLength/precision/scale`：来自 DDL 长度/精度  
- `nullable`：`NOT NULL` → `N`，否则 `Y`  
- `isKey`：主键字段 → `Y`  
- `isShow/isShowList/isQuery`：默认 `Y/Y/N`，系统字段按规则隐藏  
- `classType/fieldShowType`：控件类型（**必须**在白名单内）  

**优先级规则（必须）**  
1) **DB 类型优先**：`fieldDbType` 决定基础输入控件（如数字控件），`classType` 仅用于模板显式分支。  
2) **控件白名单校验**：若语义推断出的 `classType` 不在模板支持列表中，必须**阻断生成**并给出原因。  
3) **字段一致性**：`classType` 与 `fieldShowType` 必须保持一致（若无特殊原因），避免模板分支与校验规则割裂。  
4) **字典/校验/扩展参数**：仅在模板会消费的字段范围内生成，避免“写了但模板不读”的假配置。

### 2.2 业务描述增强

AI 可从自然语言描述中提取更精确的配置：

```
用户输入："status字段用下拉框，选项有：待审核、已通过、已拒绝"
     ↓
ColumnSpec:
  classType = "list"
  dictField = "order_status"  // AI生成字典编码
  // 同时生成字典SQL
```

### 2.3 智能推断规则表

| 字段特征 | 推断结果 |
|---------|---------|
| 字段名含 `status/state/type` | `classType=list` + 需要字典 |
| 字段名含 `time/date` | `classType=date/datetime` |
| 字段名含 `by` 且为系统字段 | `isShow=N` |
| 字段名含 `id` 且非主键 | 可能是外键，`classType=popup` |
| 字段类型 `TEXT` | `classType=textarea/umeditor` |
| 字段名含 `file/attach` | `classType=file` |
| 字段名含 `img/image/pic/photo` | `classType=image` |
| 字段名以 `is_` 开头 | `classType=switch` |
| 字段类型 `DECIMAL` + 名含 `money/amount` | `fieldValidType=money` |
| `NOT NULL` 约束 | `nullable=N` |
| 有 `DEFAULT` 值 | `fieldDefault=xxx` |
| 有 `COMMENT` | `filedComment=xxx` |

---

## 3. 模拟生成引擎

### 3.1 生成流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI 代码生成流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  DDL    │───▶│  元数据推导  │───▶│ CodegenSpec │             │
│  │  输入   │    │  (AI智能)   │    │(Table/Cols) │             │
│  └─────────┘    └─────────────┘    └──────┬──────┘             │
│                                           │                     │
│  ┌─────────┐                              ▼                     │
│  │ 业务描述 │──────────────────▶  ┌─────────────┐               │
│  │ (可选)  │                     │  配置增强   │               │
│  └─────────┘                     │  (字典/校验) │               │
│                                  └──────┬──────┘               │
│                                         │                       │
│                                         ▼                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   模板选择                               │   │
│  │  jspMode: one/tree/many/jvxe/erp/innerTable/tab        │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                FreeMarker 渲染                           │   │
│  │  读取 code-template-online/{stylePath}/ 下模板          │   │
│  │  注入 tableVo + columns + subTables 上下文              │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   输出文件                               │   │
│  │  - Entity.java        - Controller.java                 │   │
│  │  - Service.java       - ServiceImpl.java                │   │
│  │  - Mapper.java        - Mapper.xml                      │   │
│  │  - List.vue           - Form.vue                        │   │
│  │  - Modal.vue          - menu.sql                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 AI 模拟 FreeMarker 渲染

AI 有两种实现路径：

#### 方案A：通过 Codegen CLI 调用官方模板引擎（**唯一允许**）

- **入口**：本项目模块 `jeecg-boot/jeecg-codegen-cli`，执行 `jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar`  
- **输入**：YAML/JSON（**CodegenSpec**）  
- **核心**：直接调用 `codegenerate` 模块的 `CodeGenerateOne/CodeGenerateOneToMany`，与 Online 生成逻辑一致  
- **模板路径**：`/jeecg/code-template-online`（与 Online 表单一致）
- **Jar 不存在时先构建**：在 `jeecg-boot/` 内执行  
  `mvn -pl jeecg-codegen-cli -am clean package`  
  生成 `jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar`

**新增：DDL → CodegenSpec（CLI 子入口）**  
为减少手工编写 spec，CLI 支持从 DDL 直接生成 `CodegenSpec`（单表原型）。

示意（只生成 spec，不渲染）：
```
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_products.sql \
  --spec-out specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode one
```

直接输出到 stdout：
```
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_products.sql > specs/cli_products.yaml
```

> 约束：`--ddl` 仅生成 spec，不触发模板渲染；后续仍需走 `--input` 执行生成。

示意（CLI 执行）：
```
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue
```

**完整流程示例：DDL → spec → 模板渲染**
```
# 1) DDL 转 spec（输出到文件）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_products.sql \
  --spec-out specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode one \
  --bussi-package org.jeecg.modules \
  --entity-package cli \
  --field-row-num 2

# 2) spec 渲染生成代码
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue
```

参数说明（最小必要）：
- `--ddl`：DDL 文件路径（支持多条 `CREATE TABLE`）  
- `--spec-out`：输出 spec 的路径（YAML）  
- `--output`：最终生成代码落盘目录（也会写入 spec.projectPath）  
- `--jsp-mode`：模板风格（`one/tree/many/jvxe/erp/innerTable/tab`）  
- `--bussi-package`：业务包前缀（可选）  
- `--entity-package`：实体包路径（可选；不填则用表名前缀）  
- `--field-row-num`：表单列数（可选，默认 2）
- `--frontend-root`：前端输出根目录（可选，默认 `ant-design-vue-jeecg/src/views`）
- `--no-frontend`：跳过前端拷贝（仅生成后端文件；Vue 文件保留在后端模块内，不复制到前端项目）
- `--vue-style`：前端代码风格（`vue`/`vue3`/`vue3Native`，需与 `jsp-mode` 支持范围匹配）  
- `--one-to-many`：显式启用一对多 spec 生成（必填配合 `--main-table`/`--sub-tables`）  
- `--main-table`：主表表名（多表 DDL 必填）  
- `--sub-tables`：子表表名列表（逗号分隔，一对多必填）  
- `--tree-pid-field`：树父节点字段（可选，默认 `parent_id`）  
- `--tree-text-field`：树显示字段（可选，默认 `name`/`title`）  
- `--tree-has-children`：树子节点标识字段（可选，默认 `has_child`/`is_leaf`）  

约束说明：
- 多表 DDL 未指定 `--main-table` 将直接失败。  
- `jsp-mode` 为一对多模板时必须显式 `--one-to-many`，否则拒绝生成。  
- `jsp-mode=tree` 必须具备 `parent_id` 与 `name/title`（或通过 `--tree-*` 指定）。  
- `--no-frontend` 将导致 dry-run 的 `frontend` 为空，所有输出归为 `backend`。  
- `jsp-mode` 与 `--vue-style` 的匹配规则：
  - `many`：仅 `vue`  
  - `jvxe` / `erp`：`vue` / `vue3` / `vue3Native`  
  - `innerTable` / `tab`：`vue` / `vue3`  
  - `tree` / `one`：`vue` / `vue3` / `vue3Native`  

## 3.6 标准 CLI 操作范式（建议直接复用）

> 以下命令默认在仓库根目录执行。

### 3.6.1 单表（Vue2）
```bash
# 1) DDL → spec
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_products.sql \
  --spec-out specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode one \
  --vue-style vue \
  --bussi-package org.jeecg.modules \
  --entity-package cli

# 2) spec → 模板渲染
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue
```

#### 3.6.1（扩展）单表后端-only（跳过前端拷贝）
> 场景：表是单表生成，但不需要把 Vue 代码复制到前端工程，只保留后端文件（Vue 仍生成在后端模块内）。

```bash
# 1) DDL → spec（显式跳过前端拷贝）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_products.sql \
  --spec-out specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --jsp-mode one \
  --vue-style vue \
  --no-frontend

# 2) spec → 模板渲染（后端-only）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --vue-style vue \
  --no-frontend
```

### 3.6.2 一对多（Vue2 多风格）
```bash
# 1) DDL → spec（多表 / many）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_contracts.sql \
  --spec-out specs/cli_contracts_many.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode many \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli

# 2) spec → 模板渲染（many）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_many.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue

# 3) 其他风格（每个风格各生成一份 spec 再渲染）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_contracts.sql \
  --spec-out specs/cli_contracts_jvxe.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode jvxe \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_jvxe.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue

java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_contracts.sql \
  --spec-out specs/cli_contracts_erp.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode erp \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_erp.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue

java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_contracts.sql \
  --spec-out specs/cli_contracts_innerTable.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode innerTable \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_innerTable.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue

java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_contracts.sql \
  --spec-out specs/cli_contracts_tab.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode tab \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_tab.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue
```

### 3.6.3 树表（Vue2）
```bash
# 1) DDL → spec
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --ddl specs/cli_categories.sql \
  --spec-out specs/cli_categories.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --jsp-mode tree \
  --vue-style vue \
  --bussi-package org.jeecg.modules \
  --entity-package cli

# 2) spec → 模板渲染
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_categories.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue
```

### 3.6.4 规划模式（dry-run，仅 --input）
> 仅输出将生成的文件清单，不落盘，便于 AI/脚本规划后续改动。

```bash
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --dry-run
```

输出示例（结构化，区分前端/后端）：
```json
{
  "dryRun": true,
  "backend": [
    "/abs/path/jeecg-boot/jeecg-module-system/jeecg-system-biz/src/main/java/org/jeecg/modules/xxx/entity/Xxx.java"
  ],
  "frontend": [
    "/abs/path/jeecg-boot/ant-design-vue-jeecg/src/views/xxx/XxxList.vue"
  ]
}
```

> 使用 `--no-frontend` 时，dry-run 的 `frontend` 为空，原本前端清单会归入 `backend`（因为不再做前端拷贝）。

```bash
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_products.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --no-frontend \
  --dry-run
```

输出示例（只含 backend）：
```json
{
  "dryRun": true,
  "backend": [
    "/abs/path/jeecg-boot/jeecg-module-system/jeecg-system-biz/src/main/java/org/jeecg/modules/xxx/entity/Xxx.java",
    "/abs/path/jeecg-boot/jeecg-module-system/jeecg-system-biz/src/main/java/org/jeecg/modules/xxx/vo/XxxPage.java"
  ],
  "frontend": []
}
```

## 3.7 必须手工覆盖的控件清单（DDL 无法可靠推断）

以下控件需要在 `spec.yaml` 中显式设置 `classType/fieldShowType`，并补齐字典或扩展参数：
- `sel_user`（用户选择）
- `sel_depart`（部门选择）
- `sel_search`（搜索下拉）
- `sel_tree`（树形下拉）
- `cat_tree`（分类字典树）
- `popup`（弹窗选择）

最小示例（片段）：
```yaml
columns:
  - fieldDbName: owner_user_id
    fieldName: ownerUserId
    classType: sel_user
    fieldShowType: sel_user
  - fieldDbName: dept_id
    fieldName: deptId
    classType: sel_depart
    fieldShowType: sel_depart
```

## 3.8 失败优先清单（必须阻断）
- 多表 DDL 未指定主表。  
- 一对多模式未显式 `--one-to-many`。  
- 一对多外键无法唯一匹配或主键复合。  
- 树表缺 `parent_id` 或 `name/title`。  
- 控件类型不在模板白名单或字典控件缺 `dictField/dictTable`。

## 3.9 参数速查表

### 通用参数
| 参数 | 说明 | 是否必填 | 备注 |
| --- | --- | --- | --- |
| `--ddl` | DDL 文件路径 | 条件必填 | 仅用于 DDL→spec |
| `--input` | spec 文件路径 | 条件必填 | 仅用于 spec→渲染 |
| `--spec-out` | spec 输出路径 | 可选 | 未指定时输出到默认目录 |
| `--output` | 后端输出目录 | 可选 | 默认 `jeecg-boot/jeecg-module-system/jeecg-system-biz` |
| `--frontend-root` | 前端输出根目录 | 可选 | 默认 `ant-design-vue-jeecg/src/views` |
| `--no-frontend` | 跳过前端拷贝 | 可选 | **仅影响前端拷贝**，不影响模板渲染 |
| `--jsp-mode` | 模板风格 | 必填 | one/tree/many/jvxe/erp/innerTable/tab |
| `--vue-style` | 前端风格 | 可选 | vue/vue3/vue3Native（须匹配 jsp-mode） |
| `--bussi-package` | 业务包前缀 | 可选 | 默认 `org.jeecg.modules` |
| `--entity-package` | 实体包 | 可选 | 默认表名前缀 |
| `--field-row-num` | 表单列数 | 可选 | 未指定自动推断 |
| `--query-fields` | 查询字段 | 可选 | 形如 `name,status,create_time:group` |
| `--template` | 自定义模板路径 | 可选 | 覆盖默认模板目录 |
| `--dry-run` | 规划模式 | 可选 | **仅 `--input` 生效**，不落盘，仅输出前/后端清单 |

### 一对多参数
| 参数 | 说明 | 是否必填 | 备注 |
| --- | --- | --- | --- |
| `--one-to-many` | 启用一对多 | 必填 | 仅在一对多模式使用 |
| `--main-table` | 主表名 | 必填 | 多表 DDL 必填 |
| `--sub-tables` | 子表名列表 | 必填 | 逗号分隔 |

### 树表参数
| 参数 | 说明 | 是否必填 | 备注 |
| --- | --- | --- | --- |
| `--tree-pid-field` | 父节点字段 | 可选 | 默认 parent_id |
| `--tree-text-field` | 文本字段 | 可选 | 默认 name/title |
| `--tree-has-children` | 子节点标识 | 可选 | 默认 has_child/is_leaf |

## 3.10 spec 字段最小模板

### 单表最小模板
```yaml
jspMode: one
projectPath: /abs/path/jeecg-boot/jeecg-module-system/jeecg-system-biz
bussiPackage: org.jeecg.modules
table:
  tableName: cli_products
  entityPackage: cli
  entityName: CliProducts
  ftlDescription: 产品
  fieldRowNum: 2
columns:
  - fieldDbName: id
    fieldName: id
    fieldType: String
    fieldDbType: string
    isKey: Y
    isShow: N
    isShowList: N
    isQuery: N
    nullable: N
    classType: default
    fieldShowType: default
  - fieldDbName: name
    fieldName: name
    fieldType: String
    fieldDbType: string
    isShow: Y
    isShowList: Y
    isQuery: Y
    queryMode: single
    nullable: Y
    classType: default
    fieldShowType: default
```

### 一对多最小模板
```yaml
jspMode: many
projectPath: /abs/path/jeecg-boot/jeecg-module-system/jeecg-system-biz
bussiPackage: org.jeecg.modules
table:
  tableName: cli_contracts
  entityPackage: cli
  entityName: CliContracts
  ftlDescription: 合同
  fieldRowNum: 2
columns: [ ...主表字段... ]
subTables:
  - tableName: cli_contract_items
    entityName: CliContractItems
    ftlDescription: 合同明细
    foreignRelationType: "0"
    foreignKeys: [contract_id]
    foreignMainKeys: [id]
    columns: [ ...子表字段... ]
```

### 树表最小模板
```yaml
jspMode: tree
projectPath: /abs/path/jeecg-boot/jeecg-module-system/jeecg-system-biz
bussiPackage: org.jeecg.modules
table:
  tableName: cli_categories
  entityPackage: cli
  entityName: CliCategories
  ftlDescription: 分类树
  fieldRowNum: 2
  extendParams:
    pidField: parent_id
    textField: name
    hasChildren: has_child
columns: [ ...字段... ]
```

默认值策略（CLI 内置）：
- `projectPath`：优先 `--output`；否则默认 `jeecg-boot/jeecg-module-system/jeecg-system-biz`（存在时）；再否则当前目录  
- `bussiPackage`：默认 `org.jeecg.modules`  
- `entityPackage`：默认取表名前缀（如 `order_main` → `order`，无前缀则 `demo`）  
- `frontendRoot`：优先 `--no-frontend`（强制为空，跳过前端拷贝）；否则 `--frontend-root`；再否则默认 `ant-design-vue-jeecg/src/views`（存在时）

### 3.3 模板上下文变量清单

> 说明：以下上下文由 CLI 内部从 `CodegenSpec` 构造，外部不直接生成它们。

| 变量名 | 类型 | 说明 |
|-------|------|------|
| `tableVo` | TableVo | 表配置对象 |
| `tableName` | String | 物理表名 |
| `entityName` | String | 实体类名 |
| `entityPackage` | String | 包路径 |
| `bussiPackage` | String | 业务包前缀 |
| `columns` | List | 字段列表（过滤后） |
| `originalColumns` | List | 原始字段列表 |
| `primaryKeyField` | String | 主键字段名 |
| `subTables` | List | 子表列表（一对多） |

---

## 4. 风格对齐与可控性

### 4.1 代码风格对齐清单

#### Entity 层
- [x] `@Data` + `@TableName` + `@Accessors(chain=true)` + `@EqualsAndHashCode`
- [x] `@ApiModel` + `@ApiModelProperty`
- [x] 主键：`@TableId(type = IdType.ASSIGN_ID)`
- [x] 日期：`@JsonFormat` + `@DateTimeFormat`
- [x] 字典：`@Dict(dicCode=xxx)` 或 `@Dict(dictTable,dicText,dicCode)`
- [x] Excel：`@Excel(name=xxx, width=15)`

#### Controller 层
- [x] `@Api(tags=xxx)` + `@RestController` + `@RequestMapping`
- [x] 继承 `JeecgController<Entity, Service>`
- [x] 权限注解：`@RequiresPermissions("package:table:action")`
- [x] 日志注解：`@AutoLog(value=xxx)`
- [x] Swagger：`@ApiOperation`

#### Vue 层
- [x] 组件命名：`${EntityName}List.vue` / `${EntityName}Form.vue` / `${EntityName}Modal.vue`
- [x] API路径：`/${entityPackage}/${entityName?uncap_first}/xxx`
- [x] 表单校验：`validatorRules` 对象
- [x] 字典组件：`<j-dict-select-tag dictCode="xxx" />`

### 4.2 权限编码规范

```
格式：${entityPackage}:${tableName}:${action}

示例：
- demo:test_demo:add
- demo:test_demo:edit
- demo:test_demo:delete
- demo:test_demo:deleteBatch
- demo:test_demo:exportXls
- demo:test_demo:importExcel
```

### 4.3 API 路径规范

```
格式：/${entityPackage}/${entityName?uncap_first}/${action}

示例：
- GET  /demo/testDemo/list
- POST /demo/testDemo/add
- PUT  /demo/testDemo/edit
- DELETE /demo/testDemo/delete
- GET  /demo/testDemo/queryById
- GET  /demo/testDemo/exportXls
- POST /demo/testDemo/importExcel
```

---

## 5. 落地路径与技术组件

### 5.1 核心技术组件

| 组件 | 职责 | 技术选型 |
|-----|------|---------|
| **DDL 解析器** | 解析 SQL DDL 提取表结构 | JSqlParser / Druid SQL Parser |
| **元数据推导引擎** | DDL → CodegenSpec | AI 规则引擎 + 语义推断 |
| **配置增强器** | 业务描述 → 字典/校验配置 | LLM 自然语言理解 |
| **模板渲染器** | FreeMarker 模板渲染 | FreeMarker 2.3.x |
| **代码输出器** | 文件写入 + 目录结构 | Java IO / NIO |

### 5.2 实现步骤

#### Phase 1：基础能力（MVP）

1. **DDL 解析**
   - 输入：CREATE TABLE DDL
   - 输出：表名、字段列表、类型、约束、注释

2. **基础映射**
   - DB类型 → Java类型
   - 字段名 → 驼峰命名
   - 表名 → 实体名/包名

3. **单表生成**
   - 使用 `default/one` 模板
   - 生成 Entity/Controller/Service/Mapper/Vue

#### Phase 2：智能推断

1. **控件类型推断**
   - 基于字段名语义
   - 基于数据类型
   - 基于业务描述

2. **字典自动生成**
   - 识别枚举类字段
   - 生成字典 SQL
   - 关联字典配置

3. **校验规则推断**
   - 基于字段名（phone→m, email→e）
   - 基于约束（NOT NULL→*）

#### Phase 3：高级功能

1. **一对多支持**
   - 主子表关系识别
   - 外键字段推断
   - 多种风格模板

2. **树表支持**
   - 树结构字段识别（pid/parent_id）
   - 树表模板生成

3. **业务增强**
   - 自然语言配置
   - 自定义模板扩展

### 5.5 生成一致性校验（必须）

- **模板一致性**：生成入口必须调用官方模板，禁止绕过模板层。  
- **结构一致性**：校验输出目录/文件名/注解/权限编码与模板一致。  
- **控件一致性**：确保 `classType/fieldShowType` 与模板分支匹配；若不匹配必须提示并阻断生成。  
- **不支持控件**：如 `link_down/hidden/rate` 等 UI 存在但模板未支持，默认禁止生成，除非先扩模板。

### 5.3 AI Prompt 设计

```markdown
# 角色
你是 Jeecg-boot 代码生成专家，精通 FreeMarker 模板和 Jeecg 代码规范。

# 输入
1. DDL 语句
2. 业务描述（可选）
3. 生成模式（one/tree/many/jvxe/erp/innerTable/tab）

# 任务
1. 解析 DDL，提取表结构
2. 推导 CodegenSpec（TableSpec/ColumnSpec/SubTableSpec）
3. 智能推断控件类型、字典、校验规则
4. 按 Jeecg 模板风格生成代码

# 输出要求
- 代码风格必须与 Jeecg 官方生成器完全一致
- 注解位置、命名规范、权限编码必须对齐
- 生成完整的 Entity/Controller/Service/Mapper/Vue 文件

# 参考模板
[附上关键模板片段]
```

### 5.4 配置文件格式（可选）

支持 YAML 配置文件作为中间格式：

```yaml
jspMode: one
projectPath: /path/to/project
bussiPackage: demo

table:
  tableName: order_main
  entityPackage: order
  entityName: OrderMain
  ftlDescription: 订单主表
  fieldRowNum: 2

columns:
  - fieldDbName: id
    fieldName: id
    filedComment: 主键
    fieldDbType: string
    fieldType: String
    isKey: Y
    isShow: N
    isShowList: N
    isQuery: N
    nullable: N
    classType: default
    fieldShowType: default

  - fieldDbName: order_no
    fieldName: orderNo
    filedComment: 订单编号
    fieldDbType: string
    fieldType: String
    isShow: Y
    isShowList: Y
    isQuery: Y
    queryMode: single
    fieldValidType: only
    classType: default
    fieldShowType: default

  - fieldDbName: status
    fieldName: status
    filedComment: 订单状态
    fieldDbType: int
    fieldType: Integer
    classType: list
    fieldShowType: list
    dictField: order_status

  - fieldDbName: create_time
    fieldName: createTime
    filedComment: 创建时间
    fieldDbType: Datetime
    fieldType: Date
    classType: datetime
    fieldShowType: datetime
    isShow: N
    isShowList: N
    isQuery: N
```

> 字典项 SQL 属于“配置增强器”的附加输出，不属于 `CodegenSpec` 本体字段。

---

## 6. 总结

### 6.1 方案优势

1. **跳过 UI 配置**：AI 直接从 DDL/业务描述生成配置，无需手工点选
2. **保留模板逻辑**：复用 Jeecg 官方 FreeMarker 模板，确保代码风格一致
3. **智能推断**：基于字段语义自动推断控件类型、字典、校验规则
4. **可控性强**：支持 YAML 配置文件作为中间格式，便于人工调整

### 6.2 关键成功因素

1. **元数据映射准确性**：DDL → 配置对象的映射规则必须完备
2. **模板理解深度**：AI 必须深入理解 FreeMarker 模板的变量依赖
3. **风格对齐严格性**：生成代码必须与官方生成器输出完全一致

### 6.3 后续演进

1. **模板扩展**：支持自定义模板，适配不同项目风格
2. **增量生成**：支持在已有代码基础上增量修改
3. **双向同步**：代码修改后反向更新配置
