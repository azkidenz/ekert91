"""
e91_hardware.py - E91 protocol on an IBM Quantum processor
"""

import datetime
import json
import os

import numpy as np
from dotenv import load_dotenv
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

import e91_core as core

NUM_PAIRS = 5000
EVE_FRACTION = 1.0    # second experiment in the same job: Eve attacks this fraction of pairs (0 = skip)
OUT_DIR = "results"


def main():
    load_dotenv()
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=os.getenv("TOKEN"))
    # The first processor available with the shortest queue
    backend = service.least_busy(operational=True, simulator=False)
    print(f"Backend: {backend.name}")

    # Two experiments in one job: without Eve and, if EVE_FRACTION > 0, with Eve
    rng = np.random.default_rng()
    plan = core.plan_experiment(NUM_PAIRS, 0.0, rng)
    plan_eve = core.plan_experiment(NUM_PAIRS, EVE_FRACTION, rng) if EVE_FRACTION > 0 else {}
    configs = list(plan) + list(plan_eve)
    shots = list(plan.values()) + list(plan_eve.values())
    circuits = [core.build_circuit(a, b, e) for (a, b, e) in configs]

    # Transpilation
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    circuits = pm.run(circuits)
    qubits = circuits[0].layout.final_index_layout()[:2]
    errors = [backend.target["measure"][(q,)].error for q in qubits]
    print(f"Physical qubits (Alice, Bob): {qubits}, readout error: "
          f"{100 * errors[0]:.2f}% and {100 * errors[1]:.2f}%")
    os.makedirs(OUT_DIR, exist_ok=True)
    circuits[0].draw("mpl", idle_wires=False, filename=f"{OUT_DIR}/circuit.svg")

    sampler = SamplerV2(mode=backend)
    sampler.options.dynamical_decoupling.enable = True   # reduces decoherence
    job = sampler.run([(qc, None, n) for qc, n in zip(circuits, shots)])
    print(f"Job ID: {job.job_id()}, {len(circuits)} circuits")
    print("Waiting for the results...")
    pubs = list(job.result())

    # The first len(plan) results belong to the experiment without Eve
    r = core.analyse(core.count_results(plan, pubs[:len(plan)]))
    core.print_results(r, f"HARDWARE {backend.name}")
    r.update(backend=backend.name, date=str(datetime.date.today()),
             qubits=[int(q) for q in qubits], readout_errors=[float(x) for x in errors])

    if plan_eve:
        r_eve = core.analyse(core.count_results(plan_eve, pubs[len(plan):]))
        core.print_results(r_eve, f"HARDWARE {backend.name}, Eve on {100 * EVE_FRACTION:.0f}% of pairs")
        r["eve"] = dict(r_eve, eve_fraction=EVE_FRACTION)

    with open(f"{OUT_DIR}/hardware.json", "w") as f:
        json.dump(r, f, indent=2)
    print("Saved results")


if __name__ == "__main__":
    main()
