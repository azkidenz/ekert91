"""
e91_core.py - Common functions of the E91 protocol
"""

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

# Measurement angles on the Bloch sphere; bases are referred to by index 0, 1 or 2
ALICE_ANGLES = [0, np.pi / 4, np.pi / 2]            # phi_1, phi_2, phi_3
BOB_ANGLES = [np.pi / 4, np.pi / 2, 3 * np.pi / 4]  # theta_1, theta_2, theta_3

KEY_BASES = [(1, 0), (2, 1)]    # matching bases: phi_2 = theta_1 and phi_3 = theta_2


def measure_basis(qc, qubit, clbit, angle):
    # Measure qubit along the axis tilted by angle: rotate the axis onto Z and measure
    qc.ry(-angle, qubit)
    qc.measure(qubit, clbit)


def build_circuit(a, b, e=-1):
    # Circuit for one pair with bases a (Alice) and b (Bob); if e >= 0 Eve measures Bob's qubit
    regs = [QuantumRegister(2, "q"), ClassicalRegister(1, "alice"), ClassicalRegister(1, "bob")]
    if e >= 0:
        regs.append(ClassicalRegister(1, "eve"))
    qc = QuantumCircuit(*regs)

    # Singlet state (|01> - |10>)/sqrt(2)
    qc.x([0, 1])
    qc.h(0)
    qc.cx(0, 1)
    qc.barrier()

    # Eve: measures Bob's qubit and resends him the state she measured
    if e >= 0:
        measure_basis(qc, 1, 2, ALICE_ANGLES[e])
        qc.ry(ALICE_ANGLES[e], 1)
        qc.barrier()

    # Alice and Bob measure in their chosen bases
    measure_basis(qc, 0, 0, ALICE_ANGLES[a])
    measure_basis(qc, 1, 1, BOB_ANGLES[b])
    return qc


def plan_experiment(n_pairs, eve_fraction, rng):
    """
    Randomly choose the bases for each pair (and, with probability eve_fraction, Eve's angle)
    and count how many pairs use each combination (a, b, e).
    Each combination becomes one circuit, run once for each of those pairs.
    """
    plan = {}
    for _ in range(n_pairs):
        a = int(rng.integers(3))
        b = int(rng.integers(3))
        e = int(rng.integers(3)) if rng.random() < eve_fraction else -1
        plan[(a, b, e)] = plan.get((a, b, e), 0) + 1
    return dict(sorted(plan.items()))


def count_results(plan, result):
    """
    For each pair of bases (a, b) count: measured pairs, pairs with equal outcomes and,
    among attacked pairs, how many times Eve guesses Alice's bit.
    """
    counts = {}
    for (a, b, e), pub in zip(plan, result):
        alice = pub.data.alice.get_bitstrings()
        bob = pub.data.bob.get_bitstrings()
        c = counts.setdefault((a, b), {"pairs": 0, "same": 0, "eve_pairs": 0, "eve_right": 0})
        c["pairs"] += len(alice)
        c["same"] += sum(x == y for x, y in zip(alice, bob))
        if e >= 0:
            # Eve measured Bob's qubit: Alice's bit is (almost always) the opposite of hers
            eve = pub.data.eve.get_bitstrings()
            c["eve_pairs"] += len(eve)
            c["eve_right"] += sum(x != y for x, y in zip(eve, alice))
    return counts


def h(x):
    # Binary entropy
    if x <= 0 or x >= 1:
        return 0.0
    return -x * np.log2(x) - (1 - x) * np.log2(1 - x)


def key_rate(S, qber):
    # Fraction of the raw key that can become secret key
    S = min(abs(S), 2 * np.sqrt(2))
    if S <= 2:
        return 0.0  # no violation: Eve may know everything
    eve_info = h((1 + np.sqrt((S / 2) ** 2 - 1)) / 2)
    return max(0.0, 1 - h(qber) - eve_info)


def analyse(counts):
    # CHSH test, QBER and key decision
    # Correlator E = (equal - different) / pairs, for each pair of bases
    E = [[0.0] * 3 for _ in range(3)]
    for (a, b), c in counts.items():
        E[a][b] = (2 * c["same"] - c["pairs"]) / c["pairs"]

    # CHSH parameter and its standard deviation
    S = E[0][0] - E[0][2] + E[2][0] + E[2][2]
    sigma = np.sqrt(sum((1 - E[a][b] ** 2) / counts[(a, b)]["pairs"]
                        for a, b in [(0, 0), (0, 2), (2, 0), (2, 2)]))

    # Raw key and QBER: on matching bases the outcomes should always be opposite
    raw_key = sum(counts[k]["pairs"] for k in KEY_BASES)
    errors = sum(counts[k]["same"] for k in KEY_BASES)
    qber = errors / raw_key

    # Conservative decision: use |S| - 3 sigma
    rate = key_rate(abs(S) - 3 * sigma, qber)

    eve_pairs = sum(counts[k]["eve_pairs"] for k in KEY_BASES)
    eve_right = sum(counts[k]["eve_right"] for k in KEY_BASES)
    return {"abs_S": abs(S), "sigma_S": float(sigma), "E": E,
            "raw_key_len": raw_key, "qber": qber,
            "key_rate": float(rate), "accepted": bool(rate > 0),
            "eve_knowledge": eve_right / eve_pairs if eve_pairs else None}


def print_results(r, title):
    print(f"\n=== {title} ===")
    for row in r["E"]:
        print("   " + "   ".join(f"{x:+.3f}" for x in row))
    print(f"|S| = {r['abs_S']:.3f} +/- {r['sigma_S']:.3f}   (classic <= 2, Tsirelson = 2.828)")
    print(f"Raw key: {r['raw_key_len']} bit, QBER: {100 * r['qber']:.2f}%")
    if r["eve_knowledge"] is not None:
        print(f"Key bits guessed by Eve: {100 * r['eve_knowledge']:.1f}%")
    print(f"Key rate: {r['key_rate']:.3f}  ->  "
          f"{'KEY ACCEPTED' if r['accepted'] else 'ABORT: unsecure channel'}")
