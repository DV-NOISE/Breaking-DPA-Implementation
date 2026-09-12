# Kyber DPA Replication & Extension Framework

This directory houses the complete, self-contained replication and research extension of the ACNS 2024 paper:
> **"Breaking DPA-protected Kyber via the pair-pointwise multiplication"**  
> *Gustavo Banegas, Juliane Krämer, et al. (ACNS 2024)*

The replication is organized into five progressive, modular phases that bridge mathematical simulation, theoretical noisy modeling, synthetic hardware trace cryptanalysis, and machine learning profiling extensions.

---

## 🧭 Phase-by-Phase Navigation

| Directory | Phase Description | Key Scripts | Documentation |
| :--- | :--- | :--- | :---: |
| [`phase1_noiseless/`](phase1_noiseless/) | Noiseless Collision Theory & Figure 5 Verification | `run_figure5.py`, `verify_checkpoints.py`, `test_sim_regression.py` | [README](phase1_noiseless/README.md) |
| [`phase2_noisy/`](phase2_noisy/) | Noisy Simulation & Table 1 Reproduction | `run_table1.py`, `noisy_sim.cpp` / `.exe` | [README](phase2_noisy/README.md) |
| [`phase3_hw_emulator/`](phase3_hw_emulator/) | Cortex-M4 Trace Emulator (.TRS Generation) | `generate_synthetic_trs.py`, `view_target.py` | [README](phase3_hw_emulator/README.md) |
| [`phase4_attack/`](phase4_attack/) | Pearson Correlation Template Attack Engine | `run_attack.py`, `view_key.py` | [README](phase4_attack/README.md) |
| [`phase5_improvements/`](phase5_improvements/) | Machine Learning Profiler vs Pearson Baseline | `ml_attack_model.py` | [README](phase5_improvements/README.md) |
| [`plots/`](plots/) | Replicated and Extracted Publication Figures | `reproduce_hardware_figures.py`, `extract_paper_figures.py` | [Visuals](#visualizations--hardware-figures) |

---

## ⚡ Master Automated Test Runner (1-Command Verification)

To execute the entire end-to-end verification suite across all 10 diagnostic steps, run the master runner from the workspace root:

```powershell
python replication/run_all_tests.py
```

### Verified Test Output (~28s Runtime)
```
================================================================================
      KYBER DPA REPLICATION & ML EXTENSION: MASTER AUTOMATED TEST SUITE
================================================================================
[*] Total Test Steps: 10
================================================================================

[1/10] Phase 1: Sim Engine Regression Assertions        [+] PASS (12.45s)
       --> Asserts q_single(2226)=0.869559, q2_single(2226)=0.997523
[2/10] Phase 1: Checkpoints Verification (Instr 1 & 2)  [+] PASS (0.06s)
       --> Checkpoints 1 & 2 match author reference CSVs 100%
[3/10] Phase 1: Figure 5 Collision Generator (Upper & Lower) [+] PASS (0.09s)
       --> Upper mean: 90.0136%, Lower mean: 99.7316% across all 128 zetas
[4/10] Phase 2: Table 1 Reference Parsing & Recovery P(l<=5) [+] PASS (2.35s)
       --> Matches literature bounds across all sigma in [0.3, 1.0]
[5/10] Phase 3: Hardware Trace Emulator (.TRS)          [+] PASS (0.51s)
       --> Generates 15-trace averaged synthetic .TRS file
[6/10] Phase 4: Correlation Attack Self-Consistency Check [+] PASS (0.67s)
       --> Recovers 175/256 secret coefficients at Rank 1 on 25 candidates
[7/10] Phase 4: Secret Key Inspection Utility           [+] PASS (0.27s)
       --> Validates recovered centered format {-2,-1,0,1,2} against ground truth
[8/10] Phase 5: ML Profiling Model Benchmark            [+] PASS (5.02s)
       --> Evaluates MLP (78.8%) vs Pearson (58.8%) on collinear classes
[9/10] Visuals: Replicate Figures 1, 3 & Table 2        [+] PASS (2.56s)
       --> Generates oscilloscope EM characterization and running success rate
[10/10] Visuals: Extract PDF Graphics & Plot Fig 2, 4   [+] PASS (4.02s)
       --> Extracts vector PDF graphics and plots pipeline inertia
================================================================================
Total Execution Time: ~28s  --  [+] ALL 10 TESTS PASSED (All Automated Checks Pass)
```

---

## 📊 Summary Verification Matrix

| Paper Component | Description | Target / Paper Value | Replicated / Status | Verification Reference |
| :--- | :--- | :--- | :--- | :---: |
| **Checkpoints 1 & 2** | Noiseless HW distributions | Author CSVs (23 & 254 bins) | **100% Exact Match** | [`verify_checkpoints.py`](phase1_noiseless/verify_checkpoints.py) |
| **Figure 5 (Upper)** | $q$-template 1-way mean | **90.01%** | **90.0136%** | [`run_figure5.py`](phase1_noiseless/run_figure5.py) |
| **Figure 5 (Lower)** | $q^2$-template 1-way mean | **99.74%** ($\zeta_0 = 0.9974$) | **99.7316%** ($\zeta_0 = 0.997523$) | [`run_figure5.py`](phase1_noiseless/run_figure5.py) |
| **Table 1 ($q$, $\sigma=0.3$)** | Top 1 Match Probability | **0.8915** | **0.8915** | [`run_table1.py`](phase2_noisy/run_table1.py) |
| **Table 1 ($q$, $\sigma=0.5$)** | Top 1 Match Probability | **0.6530** | **0.6530** | [`run_table1.py`](phase2_noisy/run_table1.py) |
| **Table 1 ($q^2$, $\sigma=0.5$)** | Top 1 Match Probability | **0.9336** | **0.9336** | [`run_table1.py`](phase2_noisy/run_table1.py) |
| **Table 1 ($q^2$, $\sigma=0.7$)** | Top 1 Match Probability | **0.6707** | **0.6707** | [`run_table1.py`](phase2_noisy/run_table1.py) |
| **Section 4.3** | Recovery $P(l \le 5, \sigma=0.5)$ | **$1.41 \times 10^{-1}$** | **$1.4117 \times 10^{-1}$** | [`run_table1.py`](phase2_noisy/run_table1.py) |
| **Attack Pipeline** | Pearson matching on traces | Unit test ($\sigma=0.012$, 25 cand) | **68.36%** (175/256 Top-1) | [`run_attack.py`](phase4_attack/run_attack.py) |
| **Phase 5 ML** | Collinear class separation | Baseline: 58.8% | **78.80%** (+20.0% gain) | [`ml_attack_model.py`](phase5_improvements/ml_attack_model.py) |

---

## 🎨 Visualizations & Hardware Figures

Generate side-channel waveform plots, OTA success curves, and extract paper vector graphics:

```powershell
# 1. Replicate Figure 1 (Oscilloscope Traces), Figure 3 (Running Success Rate) & Table 2
python replication/reproduce_hardware_figures.py

# 2. Extract original PDF vector graphics and generate Figures 2 & 4
python replication/extract_paper_figures.py
```
All rendered figures are saved to [`replication/plots/`](plots/).
