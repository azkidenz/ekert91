# Ekert91 in Qiskit

Implementation of the Ekert91 (E91) quantum key distribution protocol in IBM Qiskit, developed as a project for the Cryptography course (A.Y. 2025/2026), MSc in Cybersecurity, University of Milan.

The code simulates the protocol, runs it on a real IBM Quantum processor and decides whether the key can be accepted, using the CHSH test and the device-independent key rate.

## What it does

- Prepares entangled pairs in the singlet state and measures them in Ekert's bases.
- Estimates the CHSH parameter S, with its standard deviation, and the QBER on the raw key.
- Computes the device-independent key rate (Acín et al., 2007) with a conservative value of S (|S| − 3σ) and accepts or aborts the key.
- Simulates an intercept-and-resend eavesdropper on all pairs or on a fraction p of them, showing that |S| > 2 alone is not enough to guarantee a secure key.
- Runs the same circuits on the least busy IBM Quantum processor available to your account.

Error correction and privacy amplification are not implemented: the protocol stops at the accept/abort decision.

## Files

| File | Content |
|---|---|
| `e91_core.py` | Shared code: circuits, random basis choices, counting of outcomes, CHSH test, QBER, key rate and decision |
| `e91_simulation.py` | Runs all the simulations with Qiskit Aer (ideal channel, full attack, attack on 30% of the pairs, partial-attack sweep) |
| `e91_hardware.py` | Runs a new experiment on the least busy IBM Quantum processor |
| `results/` | Output of the scripts (JSON, CSV and SVG files) |

## Requirements

Python 3.10 or later and the following packages:

```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime python-dotenv matplotlib pylatexenc
```

To run on IBM hardware you need an [IBM Quantum Platform](https://quantum.cloud.ibm.com) account. Put your API key in a `.env` file in this folder:

```
TOKEN=your_api_key
```

## Usage

```bash
python e91_simulation.py   # simulations: results/ideal.json, eve.json, eve30.json, e91_sweep.csv and .svg
python e91_hardware.py     # new run on IBM hardware: results/hardware.json
```

Each run of `e91_hardware.py` submits a new job, which may wait in the IBM queue, and also saves a drawing of the transpiled circuit to `results/circuit.svg`.
