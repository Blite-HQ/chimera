"""Smoke tests for the pinned scientific/quantum stack in uv.lock.

`uv pip check` only validates declared metadata ranges; it does not catch a
version combination that resolves cleanly but breaks at runtime (freeze
regression: pandapower>=3.5.4 + pandas 2.3.3 replaced a combo where
pandapower 3.1.2 + pandas 3.0.2 resolved fine but crashed `pp.runpp` with
"assignment destination is read-only" — see 0f74343/3f49ab7/b290aea). These
tests exercise the real entry point of each heavy dependency so a future
Dependabot bump that breaks compatibility fails CI instead of shipping.

Every third-party access goes through `pytest.importorskip` (typed `Any` by
pytest's stubs) rather than a plain `import`: none of these libraries ship
pyright stubs, and this repo's `typeCheckingMode = "strict"` would otherwise
flag every attribute access as unknown. It also means the qiskit/dwave/
pennylane/sklearn/xgboost extras (only installed with `--all-extras`, which
ci.yml's Python job always passes) skip cleanly for a contributor running
`pytest` locally without them synced.
"""

from __future__ import annotations

import numpy as np
import pytest


def test_pandapower_runs_a_power_flow() -> None:
    """pandapower.runpp on a stock network converges and returns finite voltages."""
    pp = pytest.importorskip("pandapower")
    nw = pytest.importorskip("pandapower.networks")

    net = nw.example_simple()
    pp.runpp(net)
    assert net.res_bus.vm_pu.notna().all()


def test_cvxpy_solves_a_linear_milp_after_pandapower_is_imported() -> None:
    """cvxpy resolves a linear MILP via the SCIPY backend, in engine's real
    import order (pandapower loads first — both are required `engine` deps,
    ADR-008 keeps them import-adjacent in any real process)."""
    pytest.importorskip("pandapower")
    cp = pytest.importorskip("cvxpy")

    y = cp.Variable(integer=True)
    prob = cp.Problem(cp.Maximize(y), [y >= 0, y <= 5])
    prob.solve(solver=cp.SCIPY)
    assert y.value == 5


@pytest.mark.xfail(
    strict=False,
    reason=(
        "Native symbol clash: importing pandapower before cvxpy breaks cvxpy's "
        "HIGHS backend in-process (highspy _core.so: undefined symbol "
        "_ZN5Highs13releaseMemoryEv — pandapower loads a conflicting bundled "
        "HiGHS via scipy at import time). Reproduced in isolation: `import "
        "pandapower; import cvxpy as cp; cp.Problem(...).solve(solver=cp.HIGHS)` "
        "raises SolverError('The solver HIGHS is not installed.'); cvxpy+highspy "
        "alone (no pandapower import) works fine. Workaround: use cp.SCIPY "
        "instead of cp.HIGHS for MILP wherever pandapower may already be "
        "loaded (i.e. anywhere in this engine process). Un-xfail once a "
        "highspy/pandapower/scipy version combination is found that doesn't "
        "collide, or cvxpy stops bundling a separate highspy dependency."
    ),
)
def test_cvxpy_highs_backend_survives_a_prior_pandapower_import() -> None:
    """Known-broken: cp.HIGHS after `import pandapower` — see xfail reason."""
    pytest.importorskip("pandapower")
    cp = pytest.importorskip("cvxpy")

    y = cp.Variable(integer=True)
    prob = cp.Problem(cp.Maximize(y), [y >= 0, y <= 5])
    prob.solve(solver=cp.HIGHS)
    assert y.value == 5


def test_ortools_solves_a_linear_program() -> None:
    """ortools' SCIP-backed LP solver runs end to end."""
    pywraplp = pytest.importorskip("ortools.linear_solver.pywraplp")

    solver = pywraplp.Solver.CreateSolver("SCIP")
    x = solver.NumVar(0, 10, "x")
    solver.Maximize(x)
    solver.Solve()
    assert x.solution_value() == 10


def test_qiskit_aer_simulates_a_bell_circuit() -> None:
    """qiskit + qiskit-aer build and simulate a 2-qubit circuit."""
    qiskit = pytest.importorskip("qiskit")
    aer = pytest.importorskip("qiskit_aer")

    qc = qiskit.QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    result = aer.AerSimulator().run(qc, shots=64).result()
    assert result.get_counts()


def test_qiskit_nature_drives_pyscf() -> None:
    """qiskit-nature's PySCFDriver runs an H2 single-point calculation."""
    drivers = pytest.importorskip("qiskit_nature.second_q.drivers")

    driver = drivers.PySCFDriver(atom="H 0 0 0; H 0 0 0.735", basis="sto3g")
    driver.run()


def test_pennylane_evaluates_a_circuit() -> None:
    """pennylane builds a device and evaluates a qnode."""
    qml = pytest.importorskip("pennylane")

    dev = qml.device("default.qubit", wires=1)

    @qml.qnode(dev)
    def circuit():
        qml.Hadamard(wires=0)
        return qml.expval(qml.PauliZ(0))

    circuit()


def test_dwave_samplers_solve_a_bqm() -> None:
    """dwave-samplers solves a trivial BQM via simulated annealing."""
    dimod = pytest.importorskip("dimod")
    samplers = pytest.importorskip("dwave.samplers")

    bqm = dimod.BinaryQuadraticModel(
        {"x": -1, "y": -1}, {("x", "y"): 2}, 0, dimod.BINARY
    )
    result = samplers.SimulatedAnnealingSampler().sample(bqm, num_reads=10)
    assert result.first.energy is not None


def test_sklearn_fits_a_classifier() -> None:
    """scikit-learn fits LogisticRegression on a toy dataset."""
    linear_model = pytest.importorskip("sklearn.linear_model")

    x = np.array([[0], [1], [2], [3]])
    y = np.array([0, 0, 1, 1])
    linear_model.LogisticRegression().fit(x, y)


def test_xgboost_fits_a_classifier() -> None:
    """xgboost fits XGBClassifier on a toy dataset."""
    xgb = pytest.importorskip("xgboost")

    x = np.array([[0], [1], [2], [3]])
    y = np.array([0, 0, 1, 1])
    xgb.XGBClassifier(n_estimators=2).fit(x, y)
