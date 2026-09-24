---
name: dash-vtk
description: Production scientific and engineering 3D visualization with Dash VTK, covering geometry/scalar contracts, coordinate systems, rendering semantics, camera state, performance, serialization, interaction, and tests.
---

# Dash VTK — Production Playbook

## Use this skill when

Use for:

- meshes;
- finite-element/simulation geometry;
- volumes;
- surfaces;
- scientific scalar/vector fields;
- engineering geometry.

Do not use it for ordinary 2D maps.

## Data contract

Validate:

- points;
- topology/cells;
- point/cell scalar arrays;
- vector dimensions;
- array lengths;
- coordinate system.

A scalar array must have a valid relationship to its point/cell association.

## Rendering semantics

Make the scientific meaning explicit:

- scalar range;
- color mapping;
- opacity;
- representation;
- clipping/slicing;
- camera;
- selection.

Avoid dramatic styling that makes quantitative interpretation harder.

## Coordinate systems

Document the coordinate system and units.

If data is transformed, make the transformation explicit and testable.

## Performance

3D payloads can be large.

Prefer:

- preprocessing;
- simplification where acceptable;
- level-of-detail;
- avoiding repeated serialization of unchanged geometry;
- updating scalar fields without rebuilding geometry when the architecture supports it.

## Interaction

Keep camera state and selected-object state separate from the canonical scientific dataset.

When selection drives tables/charts, emit compact IDs.

## Testing

Test:

- geometry dimensions;
- topology references;
- scalar lengths;
- coordinate transforms;
- selection;
- empty/invalid inputs.

Use visual regression only when necessary.

## Anti-patterns

Avoid:

- invalid topology;
- mismatched scalar arrays;
- hidden unit conversions;
- reserializing huge meshes on every UI change;
- using 3D simply because it looks impressive.

## Production checklist

- [ ] scientific semantics explicit
- [ ] coordinate system documented
- [ ] geometry/scalars validated
- [ ] payload bounded
- [ ] interaction state separated
- [ ] conversion tests exist
