# Author Reference Files & Datasets (`author_files/`)

This directory houses the supplementary code, datasets, and simulation scripts provided directly by the paper's authors (Dr. Gustavo Banegas et al.) during academic correspondence.

To ensure long-term maintainability and clear provenance, the materials are organized into three distinct subdirectories:

```
author_files/
├── figure5_results/              # Expectation scripts & precomputed Figure 5 collision results
├── original_simulators/          # Initial C/C++ attack simulation source code
└── checkpoints_and_datasets/     # Master reference datasets, CSV checkpoints & Table 1 data
```

---

## 1. `figure5_results/`
Contains statistical expectation tools and authors' precomputed collision probability text dumps across the 128 NTT roots ($\zeta$):

| File | Description |
| :--- | :--- |
| `clean_sim.cpp` | C++ simulation computing collision distributions for odd coefficients across 64 NTT roots. |
| `attack_sim.c` | C source code modeling the NTT pointwise multiplication intermediate states. |
| `compute_expectation.py` | Python routine calculating the mathematical expectation of unique states across roots. |
| `q-simulation-results.txt` | Precomputed collision output for the $q$-attack across all roots (mean unique states: ~433.86). |
| `q-squared-simulation-results.txt` | Precomputed collision output for the $q^2$-attack across all roots (exact ground truth: `0.9975237453476766` for $\zeta_0 = 2226$). |

---

## 2. `original_simulators/`
Contains early and standalone C++ simulation models provided during initial correspondence:

| File | Description |
| :--- | :--- |
| `figure5_q_template.cpp` | Standalone C++ simulation for Figure 5 $q$-template multiplicity matching. |
| `q-attack-sim-original.cpp` | Author reference code for $q$-template candidate matching simulation. |
| `q-squared-attack-sim-original.cpp` | Author reference code for $q^2$-template candidate matching simulation. |

---

## 3. `checkpoints_and_datasets/`
Contains the primary ground-truth datasets used to validate our replication suite:

| File / Sub-pattern | Description |
| :--- | :--- |
| `q-data-instr1.csv` ... `instr5.csv` | Empirical Hamming weight collision distributions for Instructions 1–5 ($q$-attack). |
| `q^2-data-instr1.csv` ... `instr12.csv` | Empirical Hamming weight collision distributions for Instructions 1–12 ($q^2$-attack). Checkpoints 1 (23 bins) and 2 (254 bins) match our replication with 100% bin fidelity. |
| `q+q-sd-results.csv` | Ground-truth candidate match probabilities (Top 1, 2, 3, 10, 100) for $q$-templates across noise $\sigma \in [0.0, 1.0]$ (reproduces Table 1 & Figure 6). |
| `q-squared-sd-results.csv` | Ground-truth candidate match probabilities for $q^2$-templates across $\sigma \in [0.0, 1.0]$ (reproduces Table 1 & Figure 7). |
| `q-attack-sim.cpp` | Final author C++ simulator for $q$-template noisy trace evaluation. |
| `q-squared-attack-sim.cpp` | Final author C++ simulator for $q^2$-template evaluation (line 54 establishes the ground-truth halfword packing `poly0 = (a0 << 16) + a1`). |
| `q-attack-for-different-zetas.txt` | Multiplicity and collision summary across varied NTT roots. |
| `ops_intermediate_results.txt` | Exhaustive intermediate operation dump during pair-pointwise NTT multiplications. |
