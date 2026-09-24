---
name: d3-js
description: Production D3.js integration for Dash when custom SVG/canvas/browser interactions are required, covering data contracts, DOM ownership, update joins, clientside performance, accessibility, security, and JavaScript testing.
---

# D3.js — Production Playbook

## Use this skill when

Use D3 when the existing Dash component ecosystem cannot express the required visualization or interaction cleanly.

Good candidates:

- custom SVG;
- custom canvas;
- specialized layouts;
- bespoke interaction;
- custom scales/axes;
- hierarchy/force/shape utilities;
- advanced browser-side visualization.

Do not replace Plotly/Altair with D3 merely for novelty.

## Decision rule

Use the simplest technology that satisfies the requirement:

```text
standard analytical chart -> Plotly
declarative grammar -> Altair
high-density marks -> Datashader
network graph -> Cytoscape
scientific 3D -> VTK
custom browser visual -> D3
```

## Data contract

Define an explicit Python -> JavaScript contract.

Prefer:

```json
{
  "id": "...",
  "value": 123,
  "category": "..."
}
```

over opaque serialized domain objects.

Send only what the browser needs.

## DOM ownership

Choose one owner for each DOM subtree.

If D3 owns:

```text
#custom-chart svg
```

Dash should own the container but should not simultaneously regenerate the SVG's children.

## Update pattern

Use keyed joins:

```text
data join
 -> enter
 -> update
 -> exit
```

Stable keys prevent visual identity from jumping between records.

## SVG vs Canvas

Prefer SVG when:

- element count is manageable;
- individual elements need interaction/accessibility;
- semantic DOM is useful.

Prefer canvas when:

- element count is very high;
- individual DOM nodes are unnecessary;
- pixel rendering is sufficient.

## Clientside callbacks

Use browser-side computation when:

- the input data is already in the browser;
- computation is small;
- avoiding a server round trip materially improves UX.

Do not move sensitive business logic or authorization decisions into JavaScript.

## Security

Never inject untrusted HTML.

Prefer:

```javascript
selection.text(value)
```

over unsafe HTML insertion for user-controlled strings.

Validate URLs and resource references.

## Accessibility

Custom D3 graphics require deliberate accessibility:

- title/description;
- textual summary when useful;
- semantic labels;
- keyboard interaction for critical controls;
- non-color-only meaning.

## Testing

Test:

- Python/JS data contract;
- stable keys;
- transformation utilities;
- selection behavior;
- key clientside interaction.

If a JS test framework already exists, use it. Do not add a large frontend toolchain for a tiny visualization unless justified.

## Anti-patterns

Avoid:

- full SVG redraw on every update;
- Dash and D3 fighting over the same nodes;
- untrusted HTML injection;
- sending complete backend objects;
- using D3 for standard charts already handled well by Plotly;
- putting authorization logic only in clientside code.

## Production checklist

- [ ] D3 necessity justified
- [ ] compact data contract
- [ ] DOM ownership explicit
- [ ] keyed updates
- [ ] SVG/canvas choice justified
- [ ] security reviewed
- [ ] accessibility considered
- [ ] JS/data-contract tests exist
