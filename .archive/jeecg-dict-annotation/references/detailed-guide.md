# @Dict Annotation - Detailed Guide

Complete reference for Jeecg-boot dictionary translation annotation.

## Table of Contents

1. [Database Schema](#database-schema)
2. [Usage Patterns](#usage-patterns)
3. [Best Practices](#best-practices)
4. [Troubleshooting](#troubleshooting)
5. [Advanced Features](#advanced-features)

---

## Database Schema

### sys_dict (Dictionary Main Table)

```sql
CREATE TABLE `sys_dict` (
  `id` varchar(32) NOT NULL COMMENT 'Primary Key',
  `dict_name` varchar(100) NOT NULL COMMENT 'Dictionary Name',
  `dict_code` varchar(100) NOT NULL COMMENT 'Dictionary Code (Unique)',
  `description` varchar(255) DEFAULT NULL,
  `del_flag` int DEFAULT NULL,
  `type` int(1) DEFAULT '0' COMMENT '0=string, 1=number',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sd_dict_code` (`dict_code`)
) ENGINE=InnoDB;
```

### sys_dict_item (Dictionary Items Table)

```sql
CREATE TABLE `sys_dict_item` (
  `id` varchar(32) NOT NULL COMMENT 'Primary Key',
  `dict_id` varchar(32) DEFAULT NULL COMMENT 'FK to sys_dict.id',
  `item_text` varchar(100) NOT NULL COMMENT 'Display Text',
  `item_value` varchar(3000) DEFAULT NULL COMMENT 'Dictionary Value',
  `item_color` varchar(10) DEFAULT NULL COMMENT 'Color Code',
  `sort_order` int DEFAULT NULL,
  `status` int DEFAULT NULL COMMENT '1=enabled, 0=disabled',
  PRIMARY KEY (`id`),
  KEY `idx_sditem_role_dict_id` (`dict_id`)
) ENGINE=InnoDB;
```

---

## Usage Patterns

### Pattern 1: Normal Dictionary

Use for: Status flags, types, enums - any fixed set of values.

**Step 1: Add Dictionary Data**

```sql
-- 1. Create dictionary type
INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `create_by`, `create_time`)
VALUES ('1234567890', 'user_status', 'User Status', 'User status dictionary', 0, 'admin', NOW());

-- 2. Add dictionary items
INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `sort_order`, `status`, `create_by`, `create_time`)
VALUES
    ('1234567891', '1234567890', 'Normal', '1', '#00CC00', 1, 1, 'admin', NOW()),
    ('1234567892', '1234567890', 'Disabled', '0', '#FF0000', 2, 1, 'admin', NOW());
```

**Step 2: Annotate Entity Field**

```java
@Data
@TableName("sys_user")
public class SysUser {

    @Dict(dicCode = "user_status")
    private Integer status;
}
```

**Result:**
```json
{"status": 1, "status_dictText": "Normal"}
```

---

### Pattern 2: Table Dictionary

Use for: Foreign key translation, fetching related data from other tables.

**Annotation:**

```java
@Data
@TableName("sys_files")
public class SysFiles {

    // Translates createBy username to realname from sys_user table
    @Dict(dicCode = "username", dicText = "realname", dictTable = "sys_user")
    private String createBy;
}
```

**SQL equivalent:**
```sql
SELECT realname FROM sys_user WHERE username = ?
```

**Result:**
```json
{"createBy": "admin", "createBy_dictText": "Administrator"}
```

---

### Pattern 3: Multi-Value Translation

Supports comma-separated values.

**Entity:**

```java
@Dict(dicCode = "role_id", dicText = "role_name", dictTable = "sys_role")
private String roleIds;  // Value: "1,2,3"
```

**Result:**
```json
{"roleIds": "1,2,3", "roleIds_dictText": "Admin,User,Guest"}
```

---

## Best Practices

### 1. Naming Conventions

```java
// ✅ Recommended: snake_case for dicCode
@Dict(dicCode = "user_status")
@Dict(dicCode = "order_type")

// ❌ Avoid: camelCase or UPPER_CASE
@Dict(dicCode = "userStatus")
@Dict(dicCode = "ORDER_TYPE")
```

### 2. Performance Optimization

**Enable Redis Cache** (application.yml):

```yaml
spring:
  redis:
    host: localhost
    port: 6379
```

**Cache Keys:**
- Normal dict: `sys:cache:dict::{dictCode}:{value}`
- Table dict: `sys:cache:dictTable::SimpleKey [{table},{text},{code},{value}]`
- Table dict cache: 5 minutes; Normal dict: permanent

### 3. When to Use

```java
// ✅ DO: Use in VO/DTO for API responses
@Data
public class UserVO {
    @Dict(dicCode = "user_status")
    private Integer status;
}

// ⚠️ AVOID: Overusing in Entity (use only when needed)
@Data
@TableName("sys_user")
public class SysUser {
    @Dict(dicCode = "user_status")
    private Integer status;  // Only if all APIs need translation
}
```

### 4. Dictionary Data Maintenance

```sql
-- Template for adding new dictionary
SET @dict_id = REPLACE(UUID(), '-', '');

INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `create_by`, `create_time`)
VALUES (@dict_id, 'your_dict_code', 'Dictionary Name', 'Description', 0, 'admin', NOW());

SET @item1 = REPLACE(UUID(), '-', '');
SET @item2 = REPLACE(UUID(), '-', '');

INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `sort_order`, `status`, `create_by`, `create_time`)
VALUES
    (@item1, @dict_id, 'Option 1', 'value1', '#000000', 1, 1, 'admin', NOW()),
    (@item2, @dict_id, 'Option 2', 'value2', '#000000', 2, 1, 'admin', NOW());
```

---

## Troubleshooting

### Issue 1: No `_dictText` Field in Response

**Check 1: Dictionary Exists**

```sql
SELECT * FROM sys_dict WHERE dict_code = 'your_dict_code';
```

**Check 2: Dictionary Items Exist and Enabled**

```sql
SELECT * FROM sys_dict_item
WHERE dict_id = (SELECT id FROM sys_dict WHERE dict_code = 'your_dict_code')
AND status = 1;
```

**Check 3: Field Value Not Empty**

Empty values are skipped during translation.

---

### Issue 2: Translation Returns Stale Data

**Cause:** Redis cache not updated.

**Solutions:**

```java
// Clear cache programmatically
redisTemplate.delete("sys:cache:dict::" + dictCode + ":*");
redisTemplate.delete("sys:cache:dictTable::SimpleKey [" + table + "," + text + "," + code + ",*]");
```

Or restart application to clear all cache.

---

### Issue 3: Only First Value Translated in Multi-Value

**Check Data Format:**

```java
// ✅ Correct: English comma
private String roleIds = "1,2,3";

// ❌ Wrong: Chinese comma
private String roleIds = "1，2，3";

// ❌ Wrong: Semicolon
private String roleIds = "1;2;3";
```

---

### Issue 4: Performance Problems

**Enable Redis** - Without Redis, each translation queries database.

**Add Indexes:**

```sql
CREATE INDEX idx_dict_code ON sys_dict(dict_code);
CREATE INDEX idx_dict_item_value ON sys_dict_item(item_value);
CREATE INDEX idx_dict_item_status ON sys_dict_item(status);
```

---

## Advanced Features

### 1. Disable Translation for Specific Endpoint

```java
@GetMapping("/list")
@AutoDict(false)  // Disable dict translation for this method
public Result<List<User>> getUserList() {
    // ...
}
```

### 2. Custom Translation Logic

Implement `CommonAPI` interface:

```java
@Service
public class CustomDictService implements CommonAPI {

    @Override
    public String translateDict(String code, String key) {
        // Custom logic
        return customTranslate(code, key);
    }

    @Override
    public String translateDictFromTable(String table, String text, String code, String key) {
        // Custom table logic
        return customTableTranslate(table, text, code, key);
    }
}
```

---

## How It Works

### AOP Interception

```java
@Pointcut("execution(public * org.jeecg.modules..*.*Controller.*(..)) || @annotation(org.jeecg.common.aspect.annotation.AutoDict)")
public void excudeService() {}

@Around("excudeService()")
public Object doAround(ProceedingJoinPoint pjp) throws Throwable {
    Object result = pjp.proceed();
    result = this.parseDictText(result);
    return result;
}
```

### Translation Flow

1. Scan `@Dict` annotated fields in return object
2. Collect dict codes and values
3. Check Redis cache first
4. Query database for cache misses
5. Batch translate all values
6. Fill `_dictText` fields
