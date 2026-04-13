---
name: draft-response-from-procurement-doc
description: Use when the user provides a procurement, solicitation, inquiry, negotiation, or bidding document and wants response files, quote sections, or technical-business sections drafted from the document's own template, qualification rules, pricing rules, and technical-commercial requirements.
---

# Draft Response From Procurement Doc

## Overview

Draft response files from the buyer's own document structure, not from memorized chapter numbers and not by blindly copying old sample bids.

**REQUIRED COMPANION:** Use `docx` when the deliverable must be created or edited as a `.docx` file.

## Core Rules

- Never hardcode chapter numbers such as "Chapter 5" or "Section 3".
- Locate sections by semantic headings: response template, qualification/submission rules, requirements, and contract terms.
- Treat sample bids as structure hints only; do not trust their copied content, package numbers, dates, or prices.
- Mark any unproven company fact, attachment, screenshot, or contact detail as `[待补充]` or `[需确认]`.
- Prefer compliance over flourish. A plain compliant draft beats a polished non-compliant one.

## Workflow

1. Read the source procurement document and identify the semantic sections listed in `references/section-keywords.md`.
2. Extract the structured facts needed for drafting: project name, project number, package/lot, deadlines, validity period, bond, submission rules, qualification documents, pricing rules, technical scope, commercial commitments, and contract risk notes.
3. Inspect any historical response files only after the source document is understood. Use them to infer formatting habits, file split, and reusable wording; ignore obvious template errors.
4. Rebuild the required output structure from the source template itself: quote part, technical-business part, negotiation quote, or any other split the document explicitly requires.
5. If the document allows commitment letters instead of detailed deviation tables, prefer the commitment-letter path unless the user asks for line-by-line deviation tables.
6. If multiple pricing rounds exist, generate separate files for each round and state the price source file used for each one.
7. Before claiming the draft is ready, run the checks in `references/checklist.md`.

## Drafting Rules

### 1. Locate the template first
Find the document's own response-file template before writing anything. Typical headings include:
- 响应文件格式
- 投标文件格式
- 应答文件格式
- 参选文件格式
- 报价文件格式
- 响应文件组成
- 附件：格式 / 模板

If the procurement document does not contain a usable template, say so explicitly and fall back to a sample-file-based structure only with a warning.

### 2. Map content by semantics
Use the source document to map content into four buckets:
- **Template bucket**: what sections the response file must contain
- **Rule bucket**: qualification, submission, sealing, signatures, validity period, bond
- **Requirement bucket**: technical scope, business commitments, delivery, warranty, payment, service
- **Risk bucket**: ownership, source code, penalties, acceptance, change scope, exclusivity, confidentiality

### 3. Handle missing company information safely
When company-specific facts are missing, do not invent them. Use placeholders such as:
- `[待补充：公司地址]`
- `[待补充：法定代表人姓名]`
- `[待补充：授权代表身份证号]`
- `[待补充：营业执照签发机关]`

Also produce a missing-information checklist for the user.

### 4. Handle pricing files carefully
For pricing:
- state whether the draft uses first quote, second quote, or negotiation quote
- cite the exact source filename when possible
- keep package number, tax rate, amount in figures, and amount in words consistent
- if a sample file conflicts with the source procurement document, trust the procurement document first

### 5. Surface risk without rewriting the buyer's rules
If the contract terms are harsh, summarize the risk briefly for the user, but do not silently soften or rewrite required commitments inside the draft.

## Outputs

Usually produce some combination of:
- response-file draft(s)
- quote file(s)
- technical-business file(s)
- negotiation quote file(s)
- missing-information checklist
- short risk summary when the contract terms are unusually one-sided

## References

- `references/section-keywords.md` — keyword map for locating semantic sections without relying on chapter numbers
- `references/checklist.md` — extraction, drafting, consistency, and final review checklist
