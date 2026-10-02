# Author Reference Files & Datasets (`author_files/`)

This directory houses the supplementary code, datasets, and simulation scripts provided directly by the paper's authors (Dr. Gustavo Banegas et al.) during academic correspondence.

To ensure long-term maintainability and clear provenance, the materials are organized into three distinct subdirectories:

```
author_files/
├── figure5_results/              # Expectation scripts & precomputed Figure 5 collision results
├── original_simulators/          # Initial C/C++ attack simulation source code
├── checkpoints_and_datasets/     # Master reference datasets, CSV checkpoints & Table 1 data
└── raw_zetas_128/                # Raw multi-zeta Monte Carlo simulation dumps (received from Dr. Kirthi Puniamurthy)
```

---

## 4. `raw_zetas_128/`
Contains the raw, comprehensive Monte Carlo collision datasets across all 128 NTT roots ($\pm \zeta$), received directly from Dr. Kirthivaasan Puniamurthy via correspondence on September 19, 2026 (`zetas.zip`):
- **128 Root Simulation Files (`zeta-0-2226.dat` to `zeta-63--1628.dat`):** Contain raw per-pair collision distributions across thousands of candidate pairs for each root, yielding an overall 1-way unique match probability of **99.6881%** (matching the published Figure 5 lower curve ~99.74%).
- **10 Detailed Candidate Log Files (`zeta105.dat`, `zeta2226.dat`, etc.):** Explicit $(b_0, b_1)$ candidate pair logs confirming that the authors sampled between 9,146 and 12,149 candidate pairs per root.
- **Verification:** Validated by `replication/phase1_noiseless/verify_author_zetas.py` and `compute_expectation.py`.

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
