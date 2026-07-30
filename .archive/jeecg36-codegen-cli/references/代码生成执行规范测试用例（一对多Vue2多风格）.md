# 代码生成执行规范测试用例（一对多 / Vue2 多风格）

> 目标：验证一对多（主子表）在 Vue2 下的多种模板风格输出一致性。
> 规范：表结构遵循《数据库设计规范》，一对多必须显式开启。

## 1. SQL（DDL + 字典）

```sql
CREATE TABLE `cli_contracts` (
  `id` varchar(32) NOT NULL COMMENT '主键ID',
  `del_flag` varchar(1) DEFAULT '0' COMMENT '删除状态 0=未删除 1=已删除',
  `create_by` varchar(32) DEFAULT NULL COMMENT '创建人',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP not null COMMENT '创建时间',
  `update_by` varchar(32) DEFAULT NULL COMMENT '更新人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',

  `contract_no` varchar(64) NOT NULL COMMENT '合同编号',
  `contract_name` varchar(120) NOT NULL COMMENT '合同名称',
  `contract_status` varchar(1) DEFAULT NULL COMMENT '合同状态：0=草稿；1=生效；2=完结。字典：cli_contract_status',
  `sign_date` date DEFAULT NULL COMMENT '签订日期',
  `contract_amount` decimal(12,2) DEFAULT '0.00' COMMENT '合同金额',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `sort_order` int DEFAULT 0 COMMENT '排序',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cli_contracts_no` (`contract_no`),
  KEY `idx_cli_contracts_status` (`contract_status`),
  KEY `idx_cli_contracts_sign_date` (`sign_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CLI合同主表';

CREATE TABLE `cli_contract_items` (
  `id` varchar(32) NOT NULL COMMENT '主键ID',
  `del_flag` varchar(1) DEFAULT '0' COMMENT '删除状态 0=未删除 1=已删除',
  `create_by` varchar(32) DEFAULT NULL COMMENT '创建人',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP not null COMMENT '创建时间',
  `update_by` varchar(32) DEFAULT NULL COMMENT '更新人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',

  `contract_id` varchar(32) NOT NULL COMMENT '合同ID(关联 cli_contracts 表)',
  `item_code` varchar(64) NOT NULL COMMENT '明细编号',
  `item_name` varchar(120) NOT NULL COMMENT '明细名称',
  `item_unit` varchar(10) DEFAULT NULL COMMENT '单位：PCS=件；SET=套。字典：cli_item_unit',
  `item_price` decimal(10,2) DEFAULT '0.00' COMMENT '单价',
  `item_qty` int DEFAULT 1 COMMENT '数量',
  `item_amount` decimal(12,2) DEFAULT '0.00' COMMENT '金额',
  `delivery_date` date DEFAULT NULL COMMENT '交付日期',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cli_contract_items_code` (`contract_id`, `item_code`),
  KEY `idx_cli_contract_items_contract_id` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CLI合同明细表';

-- 字典：cli_contract_status
SET @dict_contract_status_id = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@dict_contract_status_id, 'cli_contract_status', '合同状态字典', '合同状态字典', '0', 'admin', NOW(), 'admin', NOW());
SET @item_contract_status_0 = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@item_contract_status_0, @dict_contract_status_id, '草稿', '0', null, '草稿', 1, 1, 'admin', NOW(), 'admin', NOW());
SET @item_contract_status_1 = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@item_contract_status_1, @dict_contract_status_id, '生效', '1', null, '生效', 2, 1, 'admin', NOW(), 'admin', NOW());
SET @item_contract_status_2 = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@item_contract_status_2, @dict_contract_status_id, '完结', '2', null, '完结', 3, 1, 'admin', NOW(), 'admin', NOW());

-- 字典：cli_item_unit
SET @dict_item_unit_id = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@dict_item_unit_id, 'cli_item_unit', '明细单位字典', '明细单位字典', '0', 'admin', NOW(), 'admin', NOW());
SET @item_unit_pcs = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@item_unit_pcs, @dict_item_unit_id, '件', 'PCS', null, '件', 1, 1, 'admin', NOW(), 'admin', NOW());
SET @item_unit_set = REPLACE(UUID(), '-', '');
INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `description`, `sort_order`, `status`, `create_by`, `create_time`, `update_by`, `update_time`)
VALUES (@item_unit_set, @dict_item_unit_id, '套', 'SET', null, '套', 2, 1, 'admin', NOW(), 'admin', NOW());
```

## 2. CLI 执行指令（Vue2 多风格）

> 注意：一对多必须显式 `--one-to-many`，并指定 `--main-table/--sub-tables`。
> 当使用 `--input` 读取既有 spec 时，`BigDecimal` 必须写成 `java.math.BigDecimal`（全限定名），否则 VO 可能缺少 import 而导致编译失败。

```bash
# 统一：DDL → spec（多表）
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

# 可选：spec → dry-run（规划清单，不落盘）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_many.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue \
  --dry-run

# 经典一对多（default.onetomany）
java -jar jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar \
  --input specs/cli_contracts_many.yaml \
  --output jeecg-boot/jeecg-module-system/jeecg-system-biz \
  --frontend-root ant-design-vue-jeecg/src/views \
  --vue-style vue

# JVXE 一对多
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

# ERP 一对多
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

# 内嵌子表（innerTable）
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

# Tab 一对多
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

## 3. 验收要点
- 生成主表 + 子表完整代码（Entity/Mapper/Service/Controller/Vue）。
- 子表外键字段 `contract_id` 被识别为 `foreignKeys`。
- 不同 jspMode 输出的 Vue 结构符合对应模板（classic/JVXE/ERP/innerTable/tab）。
