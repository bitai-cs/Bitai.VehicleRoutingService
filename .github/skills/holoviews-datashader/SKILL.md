---
name: holoviews-datashader
description: Production high-density visualization with HoloViews and Datashader, including aggregation semantics, dynamic rasterization, geospatial correctness, caching, performance boundaries, and Dash integration.
---

# HoloViews + Datashader — Production Playbook

## Use this skill when

Use when browser rendering of raw marks becomes the bottleneck or when density/aggregation is the analytical object.

Typical cases:

- millions of points;
- dense time series;
- geospatial point clouds;
- simulation output;
- high-cardinality scatterplots.

## Core principle

Do not optimize a visualization by hiding the fact that it has become a density problem.

When individual marks are no longer visually distinguishable, rasterization/aggregation can be more truthful than plotting every point.

## Pipeline

Prefer:

```text
raw source
 -> validated data
 -> domain filtering
 -> HoloViews element
 -> Datashader aggregation/rasterization
 -> presentation integration
```

Keep business rules outside the rasterization layer.

## Aggregation semantics

Choose deliberately:

| Question | Typical aggregation |
|---|---|
| How many events? | count |
| Total quantity? | sum |
| Typical value? | mean |
| Extremes? | min/max |
| Category presence? | categorical strategy with explicit semantics |

Document aggregation where a user could otherwise interpret the color/intensity incorrectly.

## Dynamic views

For zoom/pan/filter interactions:

- aggregate for the current viewport where possible;
- avoid fetching the complete raw dataset on every interaction;
- cache repeatable transformations;
- bound query size;
- protect the server from pathological viewport requests.

## Geospatial correctness

Make CRS explicit.

Validate:

- coordinate columns;
- latitude/longitude ranges;
- projection transformations;
- geometry validity.

Never silently mix projected x/y with geographic lon/lat.

## Caching

Cache expensive, reusable computations when appropriate.

Cache keys should include every input that changes the result, including relevant:

- filters;
- viewport;
- resolution;
- aggregation;
- tenant/security context.

Do not use a shared cache for user-specific data without a safe cache-key boundary.

## Performance diagnostics

Measure:

- raw retrieval;
- filtering;
- aggregation;
- rasterization;
- serialization;
- callback duration;
- browser rendering.

Do not assume Datashader automatically makes the entire application fast; data retrieval can remain the bottleneck.

## Testing

Test aggregation and filtering independently from rendering.

Useful tests:

- expected aggregate values;
- viewport filtering;
- empty data;
- invalid coordinates;
- deterministic configuration;
- selection/filter semantics.

## Anti-patterns

Avoid:

- rasterizing data with unclear aggregation semantics;
- converting millions of rows to browser JSON first;
- mixing CRS silently;
- using image output to hide invalid data;
- rebuilding expensive data pipelines for every minor UI change.

## Production checklist

- [ ] density problem is real
- [ ] aggregation semantics are explicit
- [ ] CRS is explicit
- [ ] viewport behavior is bounded
- [ ] cache key is complete if caching
- [ ] raw data is not unnecessarily sent to browser
- [ ] aggregation tests exist
