# blite-cap-mcp — one generic capability for every external MCP tool

Resolution **C-12**: third-party manifests are _not_ first-class
`CapabilityManifest`s. This package exposes **one** capability —
`blite.mcp.invoke_tool`, "invoke a tool on an external MCP server" — and the
third party's vocabulary (which servers, which tools, which versions, which
egress) enters as **configuration data with a digest**, in the
`DistributionManifest`.

That is what keeps ADR-029 intact by construction: registering a new MCP server
adds no scenario vocabulary to any manifest, because it adds no manifest at all.

## It does not run in-process

Its `execution_profile` is `service`, and `invoke()` refuses. The transport
lives in `blite.protocols.mcp` (egress belongs in `protocols`, governed by
authz — INV-6/Inv-E) and the dispatcher reaches it through `ServiceStrategy`.
A capability that spawned a third-party process from inside the engine would be
exactly the mediation AX3 exists to prevent.

## `side_effects: irreversible-external`

The honest floor. We cannot know what a stranger's tool does — assuming
reversibility would invent a guarantee we do not have, and the frozen retry rule
(§13) reads this field. A per-tool refinement is a real extension, and it needs
the freeze's ceremony, not a default.
