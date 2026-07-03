---
name: Capability request
about: Propose a new capability package (see CONTRIBUTING.md "Adding a capability")
title: '[capability] '
labels: capability
---

## What tool/algorithm should this capability wrap

<!-- e.g. "A SAT solver capability wrapping python-sat" -->

## Generic manifest sketch (ADR-029: no scenario-specific terms)

```
description: "..."
input_schema: {...}
output_schema: {...}
```

## Why it belongs in `capabilities/` and not `knowledge/`

<!-- Capabilities are generic tools; scenario-specific usage goes in knowledge/ instead -->

## Dependencies

<!-- Heavy libs should be optional extras, loaded lazily inside invoke() -->
