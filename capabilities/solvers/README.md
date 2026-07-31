# blite-cap-solvers

Classical optimization: exact QUBO via OR-Tools CP-SAT (`blite.solvers.qubo`,
`QuboSolver`) — the anchor solver (INV-2 role) and the only real entry point.

Scope note: "MILP" was promised but never implemented — QUBO is the only
solver. The `gurobi` extra (and the `"gurobi"` value in the manifest's backend
enum) is declared without any implementation behind it: `invoke` only accepts
`auto`/`ortools`.
