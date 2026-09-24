---
name: dash-ag-grid-tables
description: Production Dash AG Grid tables, covering row-model selection, server-side data boundaries, filtering/sorting/grouping, selection contracts, formatting, editing, virtualization, performance, security, and tests.
---

# Dash AG Grid — Production Playbook

## Use this skill when

Use for analytical tables requiring rich filtering, sorting, grouping, selection, pagination, virtualization, or controlled editing.

## Row-model decision

Choose deliberately:

| Data characteristic | Starting strategy |
|---|---|
| Small/moderate dataset | Client-side row model |
| Large flat dataset | Infinite row model |
| Large enterprise grouped/aggregated dataset | Server-side row model when available/appropriate |
| Specialized viewport streaming | Viewport model |

The client-side model loads all rows into the browser; server-oriented models keep more work on the backend. Do not choose based only on convenience.

## Data contract

Every row should have a stable identity.

Prefer:

```text
row_id
```

over positional identity.

Keep raw numeric/date values typed so sorting and filtering remain semantic.

## Server-side query boundary

When the grid sends:

- sort;
- filter;
- grouping;
- pagination;

translate them through a validated query model.

Never concatenate arbitrary column names or operators directly into SQL.

Use allowlists:

```text
client field -> known backend field
client operator -> supported operator
```

Bound page size and query complexity.

## Formatting

Keep canonical values separate from display formatting.

Example:

```text
canonical: 0.125
display: 12.5%
```

Do not store `"12.5%"` as the only value if the grid needs numeric sorting/filtering.

## Selection

Emit compact stable IDs to other dashboard components.

Avoid returning complete row payloads when the receiving component can retrieve what it needs.

## Editing

If editing is enabled:

- validate on the server;
- enforce authorization;
- use optimistic concurrency where required;
- distinguish validation errors from persistence failures;
- never trust the browser's displayed value.

## Virtualization

Virtualization reduces browser rendering work; it does not magically eliminate data-transfer cost.

If the dataset is too large to transfer, use a server-side data strategy.

## UX

Provide:

- clear column names;
- meaningful types;
- useful default sorting;
- empty state;
- loading state;
- error state;
- selected-row indication.

## Testing

Test:

- column definitions;
- field types;
- stable IDs;
- filter translation;
- sort translation;
- pagination bounds;
- selection output;
- edit validation.

Do not rely on generated CSS/DOM details.

## Anti-patterns

Avoid:

- loading millions of rows into client state;
- using row indexes as identity;
- unsanitized server-side filter expressions;
- converting all values to strings;
- storing entire domain records in grid state;
- enabling every grid feature without a user requirement.

## Production checklist

- [ ] row model justified
- [ ] stable row IDs
- [ ] safe query translation
- [ ] bounded page/query size
- [ ] canonical typed values
- [ ] selection payload compact
- [ ] edits validated/authorized
- [ ] tests cover query semantics
