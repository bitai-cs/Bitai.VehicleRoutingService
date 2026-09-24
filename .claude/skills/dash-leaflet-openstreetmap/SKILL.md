---
name: dash-leaflet-openstreetmap
description: Production Dash Leaflet mapping with OpenStreetMap, covering CRS, tile attribution/policy, layers, GeoJSON, markers, clustering, viewport-driven data, performance, security, and testing.
---

# Dash Leaflet + OpenStreetMap — Production Playbook

## Use this skill when

Use when map navigation, tiled basemaps, geographic layers, markers, GeoJSON, viewport filtering, or geographic controls are central.

## Technology boundary

Prefer Dash Leaflet over Plotly maps when the application needs:

- richer map layer management;
- tiled map navigation;
- operational geographic interaction;
- marker/vector layers;
- map-specific controls.

Use Plotly maps when the map is primarily an analytical chart.

## OpenStreetMap usage

When using OpenStreetMap tiles:

- retain required attribution;
- respect the applicable tile usage policy;
- do not treat public community tile infrastructure as an unlimited production tile service;
- make tile provider configuration replaceable.

For significant production traffic, evaluate a suitable tile provider/infrastructure.

## CRS discipline

Define the canonical CRS.

At the map boundary:

```text
source CRS -> validated transformation -> expected map CRS
```

Validate:

- longitude [-180, 180];
- latitude [-90, 90];
- geometry validity.

Never silently swap coordinates.

## Layer architecture

Separate:

- basemap;
- operational data;
- selection/highlight;
- labels;
- controls.

Keep stable layer IDs where interaction depends on them.

## GeoJSON

Validate:

- geometry type;
- coordinates;
- feature IDs;
- properties;
- CRS assumptions.

Do not serialize sensitive backend properties into GeoJSON just because they are available.

## Viewport-driven loading

For large datasets:

```text
map viewport/zoom
 -> validated geographic query
 -> bounded backend request
 -> simplified/aggregated geometry
 -> map layer
```

Do not ship the entire national/world dataset to the browser when only the current viewport is needed.

## Marker strategy

Avoid huge numbers of individual markers.

Consider:

- clustering;
- GeoJSON/vector layers;
- viewport aggregation;
- server-side filtering.

## Security

Treat tile URLs, remote resources, and user-selected layers as untrusted inputs.

Do not expose private service credentials in client-visible URLs.

## Testing

Test:

- coordinate conversion;
- GeoJSON validity;
- feature IDs;
- viewport query bounds;
- layer selection;
- empty/error behavior.

## Anti-patterns

Avoid:

- missing attribution;
- unbounded marker lists;
- client-side loading of massive geospatial datasets;
- silent CRS conversions;
- private data in map popups/GeoJSON;
- using map tiles as a substitute for analytical aggregation.

## Production checklist

- [ ] tile strategy is production-appropriate
- [ ] attribution present
- [ ] CRS explicit
- [ ] viewport requests bounded
- [ ] geometry simplified/aggregated when necessary
- [ ] sensitive properties excluded
- [ ] geographic tests exist
