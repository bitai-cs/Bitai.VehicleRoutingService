---
name: dash-cytoscape
description: Production network/graph visualization with Dash Cytoscape, covering canonical graph contracts, stable IDs, layouts, styling, interaction, subgraph filtering, performance, security, and tests.
---

# Dash Cytoscape — Production Playbook

## Use this skill when

Use for:

- dependency graphs;
- entity relationships;
- network topology;
- lineage;
- workflows;
- organizational/network analysis.

## Canonical graph model

Use explicit:

```text
node.id
node.data
edge.id
edge.source
edge.target
edge.data
```

Node/edge IDs must be stable and unique.

## Graph size strategy

Do not render the entire graph simply because it exists.

For large graphs:

```text
query
 -> relevant subgraph
 -> aggregate/filter
 -> visualize
```

Consider neighborhood expansion, search, category filtering, and progressive disclosure.

## Layout

Choose based on topology:

- hierarchical for trees/workflows;
- force-like for relationship networks;
- deterministic layouts when reproducibility matters.

Large graphs often require user-driven filtering rather than a more sophisticated layout.

## Styling

Separate semantic classes from style definitions.

Examples:

```text
node type
selected
warning
inactive
critical
community-X
```

Avoid per-node style duplication.

## Interaction

Selections should emit compact stable IDs.

Use those IDs to update:

- tables;
- detail panels;
- charts;
- maps.

Avoid putting complete domain objects into graph node data.

## Security

Never assume graph metadata is safe to render.

Escape/validate user-controlled labels and URLs.

## Testing

Test:

- ID uniqueness;
- source/target validity;
- filtering;
- selection;
- class assignment;
- empty graph;
- isolated nodes;
- invalid edges.

## Anti-patterns

Avoid:

- positional node IDs;
- rendering millions of edges;
- label text containing untrusted HTML;
- full-domain graph payloads;
- layout recomputation for every tiny state change.

## Production checklist

- [ ] stable graph contract
- [ ] graph size bounded
- [ ] layout justified
- [ ] selection payload compact
- [ ] semantic styling
- [ ] graph invariants tested
