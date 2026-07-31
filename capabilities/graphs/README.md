# blite-cap-graphs

Classical Max-Cut baselines via `blite.graphs.maxcut` (`MaxCutBaseline`):
greedy and Goemans-Williamson, seeded — the only real entry point of this
package.

Scope note: earlier drafts promised "partitioning, centrality, flow"; none of
that exists. `blite.graphs.partition` (`GraphPartitioner`) is a declared stub —
its `invoke` raises `NotImplementedError` — and no centrality or flow tool was
ever written.
