---
name: jeecg-dict-annotation
description: Guide for using Jeecg-boot's @Dict annotation to auto-translate dictionary values and foreign key IDs to display text. Use when adding dictionary translation to entity fields, configuring frontend columns for translated text, or troubleshooting @Dict annotation issues. Covers both normal dictionary (sys_dict/sys_dict_item) and table dictionary modes.
---

# Jeecg-Boot @Dict Annotation

Auto-translate dictionary codes and foreign key IDs to human-readable text using the `@Dict` annotation.

## Quick Decision: Which Mode?

| Use Case | Mode | Annotation |
|----------|------|------------|
| Status/Type/Enum fields | Normal Dictionary | `@Dict(dicCode = "xxx")` |
| Foreign key → Name | Table Dictionary | `@Dict(dicCode = "id", dicText = "name", dictTable = "table")` |
| Multi-values (comma separated) | Either mode | Same annotation, handles `1,2,3` → `A,B,C` |

## Workflow

### 1. Backend: Add @Dict to Entity Field

**Normal Dictionary** (for status, type, enum fields):

```java
@Dict(dicCode = "sex")
private Integer sex;  // Value 1 → sex_dictText: "男"
```

**Table Dictionary** (for foreign key translation):

```java
@Dict(dicCode = "username", dicText = "realname", dictTable = "sys_user")
private String createBy;  // "admin" → createBy_dictText: "管理员"
```

### 2. Frontend: Use {fieldName}_dictText in Column

```javascript
{
  title: '性别',
  dataIndex: 'sex_dictText',  // NOT 'sex'
  align: 'center'
}
```

### 3. Verify Result

API returns original + translated field:
```json
{
  "sex": 1,
  "sex_dictText": "男"
}
```

## Annotation Parameters

| Parameter | Required | Default | Usage |
|-----------|----------|---------|-------|
| `dicCode` | Yes | - | Normal: dict_code in sys_dict; Table: field to match |
| `dicText` | No | "" | Table mode only: field containing display text |
| `dictTable` | No | "" | Table mode only: table name to query |

## Common Issues

| Issue | Solution |
|-------|----------|
| No `_dictText` field | Check dict exists in sys_dict, dict_code matches |
| Translation not working | Verify Redis enabled for cache; clear cache if stale |
| Only first value translated in multi-value | Ensure comma-separated values (English comma) |

## Resources

- **[Detailed Guide](references/detailed-guide.md)** - Complete documentation with SQL examples, troubleshooting, best practices
- **[Code Templates](assets/templates/)** - Entity annotation templates and SQL scripts for dictionary setup
