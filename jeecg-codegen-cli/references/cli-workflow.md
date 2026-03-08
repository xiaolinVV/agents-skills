# Jeecg Codegen CLI Workflow (Templates)

Use these as command templates. Replace paths with your repo root and absolute spec path.

## Common variables
- REPO_ROOT: the jeecg-boot repo root
- CLI_JAR: `REPO_ROOT/jeecg-boot/jeecg-codegen-cli/target/jeecg-codegen-cli-3.6.3-jar-with-dependencies.jar`
- BACKEND_OUT: `REPO_ROOT/jeecg-boot/jeecg-module-system/jeecg-system-biz`
- FRONTEND_ROOT: `REPO_ROOT/ant-design-vue-jeecg/src/views` (omit when using `--no-frontend`)


## Path detection
- Auto-resolve REPO_ROOT using `references/path-detection.md` rules.
- Always pass `--output` and absolute `--spec-out`; pass `--frontend-root` unless using `--no-frontend`.

## 0) Build jar if missing
```bash
mvn -pl jeecg-codegen-cli -am clean package
```

## 1) Single table (jspMode=one)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_products.sql \
  --spec-out "$REPO_ROOT/specs/cli_products.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode one \
  --vue-style vue \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_products.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue \
  --dry-run

java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_products.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```

## 1b) Single table backend-only (skip frontend copy)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_products.sql \
  --spec-out "$REPO_ROOT/specs/cli_products.yaml" \
  --output "$BACKEND_OUT" \
  --jsp-mode one \
  --vue-style vue \
  --no-frontend \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_products.yaml" \
  --output "$BACKEND_OUT" \
  --vue-style vue \
  --no-frontend \
  --dry-run

java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_products.yaml" \
  --output "$BACKEND_OUT" \
  --vue-style vue \
  --no-frontend
```

## 2) Tree table (jspMode=tree)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_categories.sql \
  --spec-out "$REPO_ROOT/specs/cli_categories.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode tree \
  --vue-style vue \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_categories.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue \
  --dry-run

java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_categories.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```

## 3) One-to-many classic (jspMode=many)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_contracts.sql \
  --spec-out "$REPO_ROOT/specs/cli_contracts_many.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode many \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_contracts_many.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue \
  --dry-run

java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_contracts_many.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```

## Validation checklist
- Tree: spec includes `extendParams.pidField/textField/hasChildren`.
- One-to-many: spec includes `foreignKeys` for sub table.
- BigDecimal: if using `--input` spec, `fieldType` must be `java.math.BigDecimal`.


## 4) One-to-many JVXE (jspMode=jvxe)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_contracts.sql \
  --spec-out "$REPO_ROOT/specs/cli_contracts_jvxe.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode jvxe \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_contracts_jvxe.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```

## 5) One-to-many ERP (jspMode=erp)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_contracts.sql \
  --spec-out "$REPO_ROOT/specs/cli_contracts_erp.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode erp \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_contracts_erp.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```

## 6) One-to-many innerTable (jspMode=innerTable)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_contracts.sql \
  --spec-out "$REPO_ROOT/specs/cli_contracts_innerTable.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode innerTable \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_contracts_innerTable.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```

## 7) One-to-many tab (jspMode=tab)
```bash
java -jar "$CLI_JAR" \
  --ddl specs/cli_contracts.sql \
  --spec-out "$REPO_ROOT/specs/cli_contracts_tab.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --jsp-mode tab \
  --vue-style vue \
  --one-to-many \
  --main-table cli_contracts \
  --sub-tables cli_contract_items \
  --bussi-package org.jeecg.modules \
  --entity-package cli


java -jar "$CLI_JAR" \
  --input "$REPO_ROOT/specs/cli_contracts_tab.yaml" \
  --output "$BACKEND_OUT" \
  --frontend-root "$FRONTEND_ROOT" \
  --vue-style vue
```


## Command generator
Use `scripts/gen_cli_commands.py` to print commands with auto-resolved paths.
Example:
```bash
python3 /Users/zhangshaolin/.codex/skills/jeecg-codegen-cli/scripts/gen_cli_commands.py \
  --ddl specs/cli_products.sql \
  --spec-out cli_products.yaml \
  --jsp-mode one \
  --vue-style vue
```
