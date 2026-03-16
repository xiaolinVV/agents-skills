# Estimation Rules for Software Quote Builder

Use these rules to turn requirement materials into an explainable person-day estimate.

## Core principles

1. Quote **features**, not buzzwords.
2. Quote **explicit scope** only unless the user asks otherwise.
3. Prefer fewer, clearer rows over fake micro-splitting.
4. Reuse the customer's own feature structure if it is already good enough.
5. Keep estimates explainable from the source materials.
6. Default rounding is **1 person-day**.

## Suggested feature buckets

These are starting ranges, not laws.
Adjust upward when the source clearly implies complexity, cross-role coordination, or integration risk.

| Feature type | Typical range (person-days) | Notes |
| --- | ---: | --- |
| Static information page | 1-2 | About pages, help pages, policy pages |
| Login/logout/reset password | 2-4 | Basic auth only |
| User profile / account center | 2-4 | Simple forms and edits |
| Basic CRUD module | 2-5 | List + add + edit + delete + detail |
| CRUD with search/filter/export | 4-7 | Includes conditions, status, export |
| Approval / workflow node | 4-8 | Single process path |
| Multi-step business workflow | 6-12 | Status transitions, validation, exceptions |
| Role / permission management | 3-6 | Roles, menus, auth mapping |
| Dashboard / statistics page | 3-8 | Cards, charts, simple trends |
| Complex report center | 5-10 | Filters, grouping, export, multiple views |
| Import / export | 2-5 | Depends on templates and validation |
| Message / notification center | 2-5 | In-app only; external channels cost more |
| Third-party API integration | 3-10 | Depends on auth, callbacks, retries |
| Payment capability | 5-12 | Includes callback, order state, reconciliation hooks |
| File upload / attachment center | 2-4 | Simple upload, preview, delete |
| Rich business form | 3-7 | Complex validation and linked fields |
| Mobile/H5 adaptation of an existing module | +1 to +3 | Add on top of base feature |
| Mini-program / app-specific module | 3-8 | More if device capability is involved |
| Admin-only configuration page | 1-3 | Dictionary/configuration style pages |

## Complexity multipliers

Use these to move a row upward, not to justify fantasy work.

### Add complexity when the materials mention

- multi-role approval
- cross-module linkage
- financial logic
- inventory or order state machine
- external system callbacks/webhooks
- non-trivial import validation
- high-density table operations
- mobile-specific interaction constraints
- multi-tenant or organization-level permissions

### Reduce complexity when the materials show

- obvious CRUD pattern
- standard list/detail/form pattern
- repeated modules with minor field changes
- one-time admin maintenance page

## Multi-end rules

Do not double-count blindly.

- Same feature with a separate **admin backend** and **user frontend** usually needs more than one row or a higher estimate
- If the same logic is reused across Web + H5, add a modest increment instead of duplicating the entire estimate
- If the source clearly requires distinct experiences for PC, H5, mini-program, or app, estimate each surface honestly

## Table reuse rules

If the source already contains a structured feature table:

- preserve the row order
- preserve the customer's functional grouping
- add quotation columns instead of rewriting the whole thing

If the source is narrative or badly mixed:

- rebuild it using the standard template
- split only to the level supported by the evidence

## Budget alignment rules

1. Estimate the raw work first.
2. Compare the raw amount with the target amount.
3. If the raw estimate is inside the allowed band, keep it.
4. If it is outside, scale proportionally to the nearest tolerance boundary.
5. Keep the chat explanation honest about the adjustment.

## Scope exclusions by default

Do not add these automatically unless the source or user explicitly requires them:

- project management
- formal UAT or test case writing
- deployment or go-live support
- production operations
- training
- warranty or maintenance
- source-code handover clauses

## Smell checks

Stop and correct the estimate if any of these happen:

- too many 1-day rows with vague labels
- total amount matches the target perfectly but the breakdown feels fake
- repeated modules are quoted as totally unrelated work
- support activities are buried inside feature rows without being stated
- the quote table cannot explain where the work comes from in the source materials
