---
name: dash-mantine-components
description: Production Dash interfaces using Dash Mantine Components, covering design-system consistency, responsive layouts, forms, overlays, notifications, theme architecture, accessibility, performance, and testing.
---

# Dash Mantine Components — Production Playbook

## Use this skill when

Use when Mantine is the application's selected component system.

## Design-system rule

Treat theme configuration as infrastructure, not decoration.

Centralize:

- colors;
- typography;
- spacing;
- radius;
- component defaults;
- responsive conventions.

Prefer component properties and theme tokens over scattered CSS.

## Responsive composition

Design for:

- desktop analytical workflows;
- narrower laptop screens;
- tablet;
- small-screen filter stacking.

Do not assume an analytical dashboard only runs on a large monitor.

## Forms and filters

For expensive operations:

```text
edit controls
 -> local/temporary state
 -> Apply
 -> backend query
```

when immediate callback execution would be wasteful.

Use validation close to the input and authoritative validation at the backend.

## Feedback

Use:

- alerts for persistent important state;
- notifications for transient feedback;
- modals/drawers for focused tasks;
- loading indicators for active operations.

Do not hide critical errors only inside a transient notification.

## Accessibility

Ensure:

- labels;
- keyboard navigation;
- predictable focus;
- dialog semantics;
- sufficient contrast;
- non-color-only state.

## Performance

Avoid thousands of component nodes.

For large data, use:

- AG Grid;
- Plotly;
- Datashader;
- Leaflet;

instead of representing each record as a Dash component.

## Testing

Test semantic props and application state transitions.

Do not assert generated CSS class names.

## Anti-patterns

Avoid:

- mixing multiple UI frameworks without ownership rules;
- duplicated theme definitions;
- transient notifications for critical failures;
- component-per-record rendering.

## Production checklist

- [ ] centralized theme
- [ ] responsive behavior
- [ ] accessible controls
- [ ] explicit loading/error state
- [ ] component count bounded
