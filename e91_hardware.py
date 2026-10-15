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
OUT_DIR = "results"


def main():
    load_dotenv()
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=os.getenv("TOKEN"))
    # The first processor available with the shortest queue
    backend = service.least_busy(operational=True, simulator=False)
    print(f"Backend: {backend.name}")

    plan = core.plan_experiment(NUM_PAIRS, 0.0, np.random.default_rng())
    circuits = [core.build_circuit(a, b, e) for (a, b, e) in plan]

    # Transpilation
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    circuits = pm.run(circuits)
    qubits = circuits[0].layout.final_index_layout()[:2]
    errors = [backend.target["measure"][(q,)].error for q in qubits]
    print(f"Physical qubits (Alice, Bob): {qubits}, reading error: "
          f"{100 * errors[0]:.2f}% e {100 * errors[1]:.2f}%")
    os.makedirs(OUT_DIR, exist_ok=True)
    circuits[0].draw("mpl", idle_wires=False, filename=f"{OUT_DIR}/circuit.svg")

    sampler = SamplerV2(mode=backend)
    sampler.options.dynamical_decoupling.enable = True   # riduce la decoerenza
    job = sampler.run([(qc, None, n) for qc, n in zip(circuits, plan.values())])
    print(f"Job ID: {job.job_id()}, {len(circuits)} circuits")
    print("Waiting for the results...")

    r = core.analyse(core.count_results(plan, job.result()))
    core.print_results(r, f"HARDWARE {backend.name}")

    r.update(backend=backend.name, date=str(datetime.date.today()),
             qubits=[int(q) for q in qubits], readout_errors=[float(x) for x in errors])
    with open(f"{OUT_DIR}/hardware.json", "w") as f:
        json.dump(r, f, indent=2)
    print("Saved results")


if __name__ == "__main__":
    main()
