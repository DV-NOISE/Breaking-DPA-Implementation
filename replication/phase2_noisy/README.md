# Phase 2: Simulation for Noisy Traces & Table 1 Reproduction

Phase 2 transitions the analysis from noiseless theory to realistic noisy side-channel measurements. Under physical measurement conditions, each intermediate Hamming weight leakage $h_i$ is corrupted by additive Gaussian noise:
$$L_i = h_i + \mathcal{N}(0, \sigma^2)$$

This phase evaluates candidate ranking under Euclidean distance matching and calculates the resulting full secret key recovery probability $P(l \le 5)$.

---

## 1. Key Objectives & Results

### Path A: Author Reference CSV Parsing (`run_table1.py`)
- Replicates the published Table 1 values directly from the authors' reference CSV dumps (`q+q-sd-results.csv` and `q-squared-sd-results.csv`).
- Produces [`plots/figure6_q_candidates.png`](plots/figure6_q_candidates.png) and [`plots/figure7_q2_candidates.png`](plots/figure7_q2_candidates.png).

### Three $q^2$ Data Sources in this Repository & Citation Guidance
To ensure complete academic transparency, this repository contains three distinct $q^2$ data sources:
1. **Source (a) — Author Reference Dataset** ([`author_files/.../q-squared-sd-results.csv`](../../author_files/checkpoints_and_datasets/q-squared-sd-results.csv)): Static CSV dump received from the authors. Parsed by `run_table1.py`.
2. **Source (b) — Fixed-but-Dormant Function** (`compute_template_q2` in [`noisy_sim.cpp`](noisy_sim.cpp)): Corrected halfword packing bug (`(a0<<16)|a1`), preserved as a reference implementation.
3. **Source (c) — New Full-Scale Independent Sweep** ([`q2_noisy_sim.cpp`](q2_noisy_sim.cpp) & [`q2_noisy_sweep_results.txt`](q2_noisy_sweep_results.txt)): Full $11,082,241$-candidate Monte Carlo sweep ($N=2500$ trials/$\sigma$) run on local hardware.

> [!TIP]
> **Citation Guidance for Paper**: The publication manuscript should explicitly cite **Source (c)** as *"Ours (Independent Monte Carlo, $N=2,500$)"* and cite **Source (a)** as *"ACNS 2024 Reference"* to prove genuine, non-circular empirical validation.

### Independent Full-Scale Results Matrix ($N = 2,500$ Trials/$\sigma$)

| Template | $\sigma$ | Top 1 ($p_1$) [Paper / Independent] | Top 2 ($p_2$) [Paper / Independent] | Top 3 ($p_3$) [Paper / Independent] | Recovery $P(l \le 5)$ |
| :---: | :---: | :---: | :---: | :---: | :---: |
| $q^2$ | 0.5 | 0.9336 / **0.9200** | 0.9942 / **0.9720** | 0.9995 / **0.9860** | **$1.4117 \times 10^{-1}$** |
| $q^2$ | 0.6 | 0.8166 / **0.7800** | 0.9631 / **0.8920** | 0.9926 / **0.9300** | **$1.1578 \times 10^{-6}$** |
| $q^2$ | 0.7 | 0.6707 / **0.6080** | 0.8879 / **0.7300** | 0.9575 / **0.7860** | **$1.9542 \times 10^{-17}$** |
| $q^2$ | 0.8 | 0.5256 / **0.5080** | 0.7719 / **0.6460** | 0.8780 / **0.7080** | **$5.3725 \times 10^{-35}$** |
| $q^2$ | 0.9 | 0.4003 / **0.3000** | 0.6409 / **0.4240** | 0.7672 / **0.4820** | **$5.5670 \times 10^{-56}$** |
| $q^2$ | 1.0 | 0.2995 / **0.2360** | 0.5115 / **0.3320** | 0.6436 / **0.4020** | **$6.4678 \times 10^{-79}$** |

#### Figure 6: Single-Coefficient $q$-Templates ($3,329$ candidates per root)
[![Figure 6: q-Templates](plots/figure6_q_candidates.png)](plots/figure6_q_candidates.png)

#### Figure 7: Joint-Coefficient $q^2$-Templates ($11.08 \times 10^6$ candidates per root)
[![Figure 7: q2-Templates](plots/figure7_q2_candidates.png)](plots/figure7_q2_candidates.png)

#### Figure 7: Independent Full-Scale Monte Carlo ($N=2,500$ Trials/$\sigma$)
[![Figure 7 Independent](plots/figure7_q2_independent.png)](plots/figure7_q2_independent.png)

---

## 2. Source Files & Architecture

| File | Language | Purpose |
| :--- | :---: | :--- |
| [`q2_noisy_sim.cpp`](q2_noisy_sim.cpp) | C++17 (OpenMP) | Full-scale 11M-candidate Monte Carlo simulator across noise levels. |
| [`q2_noisy_sim.exe`](q2_noisy_sim.exe) | Binary | Precompiled high-speed binary (`g++ -O3 -fopenmp`). |
| [`run_q2_table1_independent.py`](run_q2_table1_independent.py) | Python | Driver script computing independent $P(l \le 5)$ and plotting `figure7_q2_candidates_independent.png`. |
| [`q2_noisy_sweep_results.txt`](q2_noisy_sweep_results.txt) | Data | Exported empirical multi-candidate match probabilities. |
| [`noisy_sim.cpp`](noisy_sim.cpp) | C++17 | Standalone single-coefficient $q$-template noisy simulator. |
| [`run_table1.py`](run_table1.py) | Python | Parses author reference CSVs and generates reference Figures 6 and 7. |
| [`plots/`](plots/) | Directory | Output gallery containing both author-reference and independent reproduction plots. |

---

## 3. Execution Instructions

### A. Run Independent Full-Scale $q^2$ Sweep & Generate Independent Figure 7
```powershell
python replication/phase2_noisy/run_q2_table1_independent.py
```

### B. Run Reference CSV Parsing & Verification
```powershell
python replication/phase2_noisy/run_table1.py
```
