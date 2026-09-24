---
name: plotly-charts-maps
description: Production Plotly charts and analytical maps for Dash, including figure architecture, interactions, performance, accessibility, testing, and decision rules for when Plotly should or should not be used.
---

# Plotly Charts and Maps — Production Playbook

## Use this skill when

Use for Plotly Express, Plotly Graph Objects, `dcc.Graph`, Plotly analytical maps, figure interactions, figure factories, or review of Plotly-heavy Dash code.

Do not default to Plotly when the problem is better expressed as a high-density raster visualization, a rich tiled GIS interface, a node-edge network, or scientific 3D.

## Decision rules

Prefer Plotly when:

- users need analytical charts with rich hover/selection;
- the visualization fits browser rendering at the expected scale;
- the chart should integrate tightly with Dash callbacks;
- standard statistical/analytical chart types cover the requirement.

Consider alternatives when:

- millions of marks need dynamic rasterization -> HoloViews + Datashader;
- map controls/layers/tiles are central -> Dash Leaflet;
- bespoke SVG/canvas interaction is required -> D3;
- scientific 3D -> Dash VTK.

## Figure architecture

Prefer:

```python
def build_revenue_trend(data: DataFrame, *, metric: str) -> go.Figure:
    ...
```

rather than constructing the entire figure inside a callback.

A good builder should:

- accept validated data;
- avoid side effects;
- return a complete figure;
- define labels/units;
- handle empty input;
- make important ordering explicit.

Keep data transformation outside the builder when it is domain logic.

## Trace discipline

Avoid excessive trace counts.

Prefer a compact representation such as:

```text
one trace + categorical encoding
```

over:

```text
one trace per row
```

when both produce the same analytical meaning.

Use WebGL traces only after confirming they improve the actual bottleneck.

## Hover and selection

Use:

- `customdata` for stable identifiers;
- `hovertemplate` for controlled content;
- `clickData`/`selectedData` for meaningful cross-filtering;
- `relayoutData` for viewport-aware behavior.

Never put sensitive backend payloads into `customdata` just because the callback needs an ID.

Send IDs, not entire database records.

## State preservation

When user interactions should survive figure updates, evaluate `uirevision`.

Do not blindly use `uirevision`; define a stable revision key based on the semantic dataset/view state.

## Partial updates

When only a small property changes, consider Dash partial property updates rather than rebuilding a large figure.

Use this only when it reduces real work and keeps callback behavior understandable.

## Empty and invalid data

Define explicit behavior for:

- no rows;
- all-null metric;
- missing dimensions;
- invalid dates;
- invalid geographic coordinates.

A chart with an empty axes object and no explanation is usually a poor production state.

Prefer a user-visible empty state or an intentionally annotated figure.

## Maps

Choose Plotly maps for analytical map views where Plotly interaction is sufficient.

For geographic data:

- validate latitude/longitude;
- explicitly define projection/map scope;
- avoid misleading aggregation;
- use meaningful hover content;
- do not expose private location fields unnecessarily.

If rich tile/layer interaction is required, use the Dash Leaflet skill instead.

## Performance workflow

Measure before optimizing:

```text
callback duration
  -> data retrieval
  -> transformation
  -> figure construction
  -> serialization
  -> browser rendering
```

Optimization options:

- aggregate;
- filter server-side;
- cache reusable transformations;
- reduce trace count;
- reduce payload;
- use partial updates;
- move tiny frequent calculations clientside;
- use Datashader for high-density data.

## Accessibility

- label axes with units;
- use descriptive titles;
- avoid color-only semantics;
- choose accessible color scales;
- provide textual context outside the figure when the visual is essential to understanding.

## Testing patterns

Test semantic properties:

```python
assert len(fig.data) == 2
assert fig.data[0].x.tolist() == expected_x
assert fig.layout.xaxis.title.text == "Date"
```

Do not snapshot every Plotly JSON property.

For callbacks, test:

```text
input filter -> expected figure semantics
selection -> expected IDs
empty input -> expected empty-state behavior
```

## Anti-patterns

Avoid:

- giant callback functions;
- SQL/API calls inside figure builders;
- one trace per row;
- embedding secrets in figure config;
- shipping huge hidden datasets through `customdata`;
- visual-only tests for business logic;
- unexplained dual axes;
- misleading zero baselines when the analytical meaning requires another scale.

## Production checklist

- [ ] analytical purpose is explicit
- [ ] data mapping is correct
- [ ] labels/units are explicit
- [ ] trace count is reasonable
- [ ] hover/selection payload is minimal
- [ ] empty/error state exists
- [ ] performance path is measured
- [ ] semantic tests exist
