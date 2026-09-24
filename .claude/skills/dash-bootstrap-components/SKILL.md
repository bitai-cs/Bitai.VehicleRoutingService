---
name: dash-bootstrap-components
description: Production responsive Dash UI using Dash Bootstrap Components, covering layout architecture, responsive grids, navigation, forms, themes, accessibility, state feedback, CSS discipline, and component tests.
---

# Dash Bootstrap Components — Production Playbook

## Use this skill when

Use when Bootstrap is the chosen UI system for the Dash application.

## Layout system

Prefer a clear hierarchy:

```text
Container
  Row
    Column
      Card
        content
```

Use responsive breakpoints intentionally.

Do not solve every layout problem with arbitrary pixel widths.

## Dashboard pattern

A strong analytical page commonly has:

```text
page title/context
  -> filter/control card
  -> primary analytical output
  -> supporting views
  -> status/help
```

Keep the hierarchy consistent across pages.

## Component ownership

Use DBC for UI structure and controls. Do not use it as a data visualization engine.

Keep visualization-specific behavior in the relevant visualization skill.

## Forms

Every control should have:

- label;
- sensible default;
- validation;
- clear disabled state when dependent inputs are unavailable;
- useful error feedback.

For expensive filters, consider an explicit Apply action instead of triggering network-heavy callbacks on every keystroke.

## CSS

Prefer component props and theme variables.

Custom CSS should be:

- scoped;
- documented when non-obvious;
- minimal.

Avoid global overrides that silently change third-party component behavior.

## Accessibility

- labels must be associated with controls;
- keyboard focus must remain usable;
- alerts should communicate state changes;
- modals should have meaningful titles/actions;
- color should not be the only status indicator.

## Testing

Test component structure and callback behavior, not generated Bootstrap markup/classes.

## Anti-patterns

Avoid:

- giant nested rows/columns;
- arbitrary fixed dimensions;
- global CSS overrides;
- unlabeled controls;
- using cards purely as decoration;
- triggering expensive callbacks on every low-value input event.

## Production checklist

- [ ] responsive layout
- [ ] labeled controls
- [ ] clear state feedback
- [ ] scoped CSS
- [ ] accessibility reviewed
