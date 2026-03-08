# 数据库表结构设计规范

## 1. 基础字段规范
所有表必须包含以下字段：
```sql
`id` varchar(32) NOT NULL COMMENT '主键ID',
`del_flag` varchar(1) DEFAULT '0' COMMENT '删除状态 0=未删除 1=已删除',
`create_by` varchar(32) DEFAULT NULL COMMENT '创建人',
`create_time` datetime DEFAULT CURRENT_TIMESTAMP not null COMMENT '创建时间',
`update_by` varchar(32) DEFAULT NULL COMMENT '更新人',
`update_time` datetime DEFAULT NULL COMMENT '更新时间',
`org_code` varchar(64) DEFAULT NULL COMMENT '部门编码'
```

## 2. 表命名规范
- 使用小写字母和下划线（`snake_case`）。
- 表名应简洁、明确，避免使用缩写。
- 表名应使用复数形式。
- 表名必须以 `模块名_实体名`格式命名，如 `cms_article`。

## 3. 字段命名规范
- 使用小写字母和下划线（`snake_case`）。
- 字段名应简洁、明确，避免使用缩写。
- 主键字段统一命名为 `id`。
- 外键字段命名为 `[关联表名]_id`，并注释关联表名，例如 `user_id` (关联 `user` 表)。

## 4. 字段类型规范
- **主键**：`varchar(32)`，使用 UUID 或雪花算法生成。
- **字符串**：**根据预估最大长度选用 `VARCHAR(n)`，仅在必要时（如长文本内容）使用 `TEXT` 或 `LONGTEXT`**。
- **数字**：
  - 数字：整数用 `INT` 或 `BIGINT` (根据范围)，**小数/金额务必使用 `DECIMAL(m,n)`**。
  - 时间：时间戳用 `DATETIME`，若只需日期用 `DATE`。
- **布尔值**：`tinyint(1)`，`0` 表示 `false`，`1` 表示 `true`。

## 5. 枚举字段规范
- 枚举字段使用 `varchar` 类型。
- 字段注释必须说明枚举值含义，并注明对应的字典编码，同时必须生成字典配置 SQL
- 示例：
  ```sql
  `status` varchar(1) DEFAULT NULL COMMENT '状态：0=未启用；1=已启用。字典：sys_status'
  ```
- 字典配置 SQL 示例：
  ```sql
  -- 字典配置 SQL 示例
  -- 说明：id 使用雪花算法生成或去除 `-` 的 UUID 字符串
  
  -- 生成去除 `-` 的 UUID
  SET @dict_id = REPLACE(UUID(), '-', '');
  
  -- 添加字典类型
  INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `create_by`, `create_time`, `update_by`, `update_time`) 
  VALUES (@dict_id, 'sys_status', '状态字典', '系统状态字典', '0', 'admin', NOW(), 'admin', NOW());
  
  -- 生成去除 `-` 的 UUID
  SET @item_id_1 = REPLACE(UUID(), '-', '');
  
  -- 添加字典项
  INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`) 
  VALUES (@item_id_1, @dict_id, '未启用', '0', null, '未启用状态', 1, 1, 'admin', NOW(), 'admin', NOW());
  
  -- 生成去除 `-` 的 UUID
  SET @item_id_2 = REPLACE(UUID(), '-', '');
  
  -- 添加字典项
  INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`) 
  VALUES (@item_id_2, @dict_id, '已启用', '1', null, '已启用状态', 2, 1, 'admin', NOW(), 'admin', NOW());
  ```

## 6. 索引规范
- **主键索引**：每个表必须有主键索引。
- **唯一索引**：对唯一性字段（如 `dict_code`）创建唯一索引 `UNIQUE KEY uk_...`。
- **外键索引**：对关联字段（如 `dict_id`）创建索引。
- **复合索引**：根据查询需求创建，避免过多索引影响性能。
- **索引命名**：索引名称必须以 `idx_` 开头，后跟字段名，如 `idx_dict_id`。
- **索引创建**：为所有**经常用于查询条件 (WHERE)、排序 (ORDER BY)、分组 (GROUP BY) 的字段或字段组合**创建索引 (`INDEX idx_...`)。

## 7. 表注释规范
- 每个表必须有**清晰的中文注释**，说明表的用途。
- 示例：
  ```sql
  COMMENT='字典配置主表';
  ```

## 8. 其他重要规范
- **字符集**：统一使用 `utf8mb4`，支持表情符号，排序规则 `utf8mb4_unicode_ci`。
- **存储引擎**：存储引擎统一使用 `InnoDB`。
- **外键约束**：严格禁止在数据库层面使用外键约束 (FOREIGN KEY)，关联逻辑在应用层保证，避免数据库性能问题。
- **字段默认值**：根据业务需求设置合理的默认值，如 `0`, `''`, `'默认值'`, `CURRENT_TIMESTAMP`，或显式允许 `NULL` ( `DEFAULT NULL`)。
- **时间默认值**：避免使用 `DEFAULT (now())`，优先 `DEFAULT CURRENT_TIMESTAMP`（兼容性更好）。

## 9. 一对多（主子表）结构规范
- **必须有主表 + 子表**：主表保存业务头信息，子表保存明细。
- **子表必须包含外键字段**：该字段关联主表主键，**类型/长度必须与主表主键一致**。
- **外键命名必须可识别**：字段名**必须以 `_id` 结尾**，建议命名为 `<主表名>_id` 或 `<主实体>_id`（如 `contract_id`）。
- **外键字段注释必须标注关联表**：例如 `合同ID(关联 demo_contracts 表)`，便于自动识别关系。
- **外键字段必须建索引**：`KEY idx_<外键字段>`，否则列表/关联查询性能不可控。
- **允许多子表**：每个子表必须具备独立外键字段与索引。
- **禁止数据库外键约束**：仅使用应用层约束，符合全局规范。

## 10. 树表结构规范
- **必须包含树结构三要素**：`id`（主键）、`parent_id`（父节点）、`name/title`（节点名称字段）。
- **字段类型一致**：`parent_id` 与 `id` 类型/长度必须一致。
- **parent_id 必须允许为空或根值**：根节点允许 `NULL` 或固定值（推荐 `0` 或 `NULL`），并在业务层处理。
- **父节点字段必须建索引**：`KEY idx_<parent_id>`，树查询依赖该索引。
- **建议字段（非强制但强烈推荐）**：
  - `is_leaf`/`has_child`：叶子标记
  - `level_num`：层级
  - `path`：路径
  - `sort_order`：排序
- **Online/CLI 代码生成一致性要求**：
  - `has_child`/`is_leaf` 推荐使用 `varchar(1)`，默认值 `'0'`/`'1'`（避免树表模板按字符串处理导致类型不匹配）。

## 示例表结构，仅供参考结构，具体字段需智能生成
```sql
CREATE TABLE `example_table`
(
    --  标准字段
    `id` varchar(32) NOT NULL COMMENT '主键ID',
    `del_flag` varchar(1) DEFAULT '0' COMMENT '删除状态 0=未删除 1=已删除',
    `create_by` varchar(32) DEFAULT NULL COMMENT '创建人',
    `create_time` datetime DEFAULT CURRENT_TIMESTAMP not null COMMENT '创建时间',
    `update_by` varchar(32) DEFAULT NULL COMMENT '更新人',
    `update_time` datetime DEFAULT NULL COMMENT '更新时间',
    `org_code` varchar(64) DEFAULT NULL COMMENT '部门编码',
    -- 业务字段 (请根据用户提供的需求（图片/文本）智能填充)
    `name`        varchar(100)                          NOT NULL COMMENT '名称',
    `status`      varchar(1)  DEFAULT NULL COMMENT '状态：0=未启用；1=已启用。字典：sys_status',
    PRIMARY KEY (`id`),
    -- 常用索引 (按需添加)
    UNIQUE KEY `uk_example_name` (`name`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='示例表';
```

**请严格按照以下 SQL 模板生成 `CREATE TABLE` 语句（业务字段根据用户提供的需求（图片/文本）智能填充）：**
**请将所有表的 SQL 语句统一完整输出，不要中途省略或分开输出。**
