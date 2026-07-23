"""Smoke test for the Guppy/Selene toolchain (Quantathon contingency, knowledge/quantum/08).

Compiles a Bell-pair Guppy program and runs it locally on the bundled Selene
emulator (Quest statevector, ideal/no-noise model) — no Nexus credits used.
Verifies the install works end-to-end and that entanglement holds (only
00/11 outcomes).

Run (ephemeral, no project dependency changes):
    uv run --with guppylang==0.21.16 python scripts/guppy_smoke_test.py
"""

from guppylang import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import cx, h, measure, qubit

SHOTS = 200


@guppy
def bell_pair() -> None:
    q0 = qubit()
    q1 = qubit()
    h(q0)
    cx(q0, q1)
    result("q0", measure(q0))
    result("q1", measure(q1))


def main() -> None:
    res = bell_pair.emulator(n_qubits=2).with_shots(SHOTS).with_seed(42).run()
    counts = res.collated_counts()

    print(f"guppylang toolchain OK -- {SHOTS} shots on Selene (Quest, ideal noise)")
    for outcome, count in sorted(counts.items()):
        print(f"  {dict(outcome)}: {count}/{SHOTS}")

    correlated = sum(
        count
        for outcome, count in counts.items()
        if dict(outcome)["q0"] == dict(outcome)["q1"]
    )
    if correlated != SHOTS:
        raise AssertionError("Bell state should only yield 00 or 11 outcomes")
    print("Entanglement check passed: only 00/11 outcomes observed.")


if __name__ == "__main__":
    main()
