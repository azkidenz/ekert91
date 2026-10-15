"""
e91_simulation.py - Simulation of the E91 protocol
"""

import json
import os

import matplotlib.pyplot as plt
import numpy as np
import qiskit
import qiskit_aer
from qiskit_aer.primitives import SamplerV2

import e91_core as core

NUM_PAIRS = 5000      # entangled pairs exchanged in each experiment
SEED = 2026           # seed: makes the results reproducible
OUT_DIR = "results"


def simulate(eve_fraction, seed):
    # Run the protocol once and return the analysis results
    rng = np.random.default_rng(seed)
    plan = core.plan_experiment(NUM_PAIRS, eve_fraction, rng)

    # One circuit per combination of bases, run once for each pair that uses it
    jobs = [(core.build_circuit(a, b, e), None, n) for (a, b, e), n in plan.items()]
    result = SamplerV2(seed=seed).run(jobs).result()

    return core.analyse(core.count_results(plan, result))


def save_json(r, filename):
    r["versions"] = f"Qiskit {qiskit.__version__}, Qiskit Aer {qiskit_aer.__version__}"
    with open(os.path.join(OUT_DIR, filename), "w") as f:
        json.dump(r, f, indent=2)


def sweep():
    # Partial attack: repeat the protocol for p = 0, 0.1, ..., 1 and draw the figure
    rows = []
    for k in range(11):
        p = k / 10
        r = simulate(p, SEED + k)
        rows.append([p, r["abs_S"], r["sigma_S"], r["qber"], r["key_rate"], int(r["accepted"])])
        print(f"p = {p:.1f}   |S| = {r['abs_S']:.3f}   QBER = {100 * r['qber']:5.2f}%   "
              f"rate = {r['key_rate']:.3f}")

    with open(os.path.join(OUT_DIR, "e91_sweep.csv"), "w") as f:
        f.write("p,S,sigma_S,qber,key_rate,accepted\n")
        for row in rows:
            f.write(",".join(str(x) for x in row) + "\n")

    # Theoretical curves: |S| = 2*sqrt(2) - sqrt(2)*p and QBER = 5p/24
    data = np.array(rows)
    p = np.linspace(0, 1, 201)
    S_th = 2 * np.sqrt(2) - np.sqrt(2) * p
    Q_th = 5 * p / 24
    r_th = [core.key_rate(s, q) for s, q in zip(S_th, Q_th)]

    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    ax[0].errorbar(data[:, 0], data[:, 1], yerr=data[:, 2], fmt="o", label="simulation")
    ax[0].plot(p, S_th, "--", label="theory")
    ax[0].axhline(2, color="gray", lw=1)
    ax[0].set_ylabel("|S|")
    ax[1].plot(data[:, 0], 100 * data[:, 3], "o", label="simulation")
    ax[1].plot(p, 100 * Q_th, "--", label="5p/24 theory")
    ax[1].set_ylabel("QBER (%)")
    ax[2].plot(data[:, 0], data[:, 4], "o", label="simulation (3σ)")
    ax[2].plot(p, r_th, "--", label="theory")
    ax[2].set_ylabel("r key rate")
    for a in ax:
        a.axvspan(0.31, 2 - np.sqrt(2), color="tab:red", alpha=0.1)  # |S| > 2 but r = 0
        a.set_xlabel("intercepted fraction p")
        a.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "e91_sweep.svg"))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    experiments = [("ideal.json", 0.0, "no attack"),
                   ("eve.json", 1.0, "Eve on all pairs"),
                   ("eve30.json", 0.3, "Eve on 30% of pairs")]
    for filename, eve_fraction, title in experiments:
        r = simulate(eve_fraction, SEED)
        core.print_results(r, f"Simulation: {title}")
        save_json(r, filename)

    print("\n=== Partial attack ===")
    sweep()
    print(f"\nResults saved in {OUT_DIR}/")


if __name__ == "__main__":
    main()
