---
name: altair-vega-charts-maps
description: Production Altair/Vega-Lite visualizations for Dash, emphasizing declarative specifications, semantic encodings, layered/linked views, interaction, map projections, performance, testing, and integration boundaries.
---

# Altair / Vega — Production Playbook

## Use this skill when

Use when a declarative grammar is advantageous, especially for:

- layered charts;
- small multiples/faceting;
- coordinated views;
- selection-driven interactions;
- reproducible chart specifications;
- concise analytical encodings.

## Decision rules

Prefer Altair/Vega when the visualization can be expressed clearly as a declarative grammar and specification readability matters.

Prefer Plotly when the application depends heavily on Plotly-specific interactive behavior or the chart is already part of a Plotly-first dashboard.

Do not introduce both libraries for equivalent charts without a concrete requirement.

## Specification discipline

Make data types explicit:

- quantitative;
- temporal;
- nominal;
- ordinal;
- geographic.

Avoid relying on inference when field semantics matter.

Prefer readable:

```text
data
 -> transform
 -> encoding
 -> mark
 -> interaction
```

over generated specifications that hide analytical intent.

## Transformations

Keep transformations in Vega-Lite when they are visualization-specific and improve readability.

Keep transformations in Python/domain services when they:

- implement business rules;
- are reused;
- require complex validation;
- should be unit tested independently.

## Interaction

Use parameters/selections for:

- brushing;
- highlighting;
- filtering;
- linked views.

If interaction can happen entirely in the browser without server data, avoid unnecessary Dash callback round trips.

If a selection must query backend data, send compact identifiers rather than entire records.

## Maps

For geographic visualizations:

- choose an appropriate projection;
- verify geographic field semantics;
- handle missing coordinates;
- avoid visual precision beyond the source data;
- distinguish geometry from attributes.

Use Dash Leaflet when tiled map navigation, geographic controls, or operational GIS behavior is central.

## Performance

Do not serialize unnecessarily large datasets.

For dense data:

- pre-aggregate;
- filter;
- sample only when analytically defensible;
- consider Datashader.

## Testing

Test the specification's meaning:

- marks;
- encodings;
- field names;
- data types;
- transforms;
- selections;
- titles/labels;
- empty behavior.

If the repository serializes Vega-Lite JSON, test stable semantic fragments rather than the entire generated document.

## Anti-patterns

Avoid:

- business logic hidden in Vega transforms;
- duplicated transformations in Python and Vega;
- ambiguous inferred types;
- huge browser-side datasets;
- using declarative interactions plus Dash callbacks for the same state without defining ownership.

## Production checklist

- [ ] encoding types explicit
- [ ] transformation ownership clear
- [ ] interaction ownership clear
- [ ] map projection validated if applicable
- [ ] browser payload bounded
- [ ] semantic tests added
