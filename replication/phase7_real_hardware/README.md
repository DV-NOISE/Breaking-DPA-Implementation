# Phase C: Real-Hardware Leakage Characterization & TVLA

## 1. Overview
This module implements the loaders, regression assertions, and statistical leakage characterization for the open EM side-channel dataset released by **Alain Alyosha Magazin & Karim M. Abdellatif** (*ePrint 2026/1851*).

- **Hardware Platform:** STM32F407 (ARM Cortex-M4 @ 84 MHz)
- **Modality:** Near-field electromagnetic (EM) probe, raw captures at 6.25 GS/s
- **Trace Length:** 10,000 samples per trace (~1.6 μs / ~134 clock cycles) windowed on the pair-pointwise multiplication (`basemul_asm`).
- **Implementations Covered:**
  - `reference`: Unprotected C reference code (Kyber-512)
  - `pqm4`: Hand-optimized assembly implementation (Kyber-512)
  - `mkm4`: First-order masked software implementation (Kyber-768), with per-share traces ($s_0, s_1$)

---

## 2. Directory Layout & Data Formats (Section 4.1)

All files in the dataset are distributed as chunked NumPy (`.npy`) arrays:
```
{reference,pqm4,mkm4}/
  {variable,fixed}/
    traces/
      traces_i.npy          # (10000, 10000) int16 [reference/pqm4]
      traces_s0_i.npy       # (10000, 10000) int16 [mkm4, Share 0: Mask M]
      traces_s1_i.npy       # (10000, 10000) int16 [mkm4, Share 1: sk - M]
    metadata/
      ap_i.npy              # (10000, 256) int16: poly a coefficients
      bp_i.npy              # (10000, 256) int16: poly b coefficients (or bp_s0/s1)
      ct_i.npy              # (10000, 768/1088) uint8: ciphertext bytes
      dk_i.npy              # (10000, 1632/2400) uint8: decapsulation keys
```

### Key Differences Between Targets
| Implementation | Public Operand | Secret Key Operand | Shares Captured | Attack Baseline (Donjon) |
| :--- | :---: | :---: | :---: | :--- |
| **`reference`** | $b$ | $a$ | 1 window | Non-profiled deep learning |
| **`pqm4`** | $b$ | $a$ | 1 window | 1st-order CPA (~40 traces) |
| **`mkm4`** | $a$ | $b = s_0 + s_1 \pmod q$ | 2 windows ($s_0, s_1$) | 2nd-order CPA on cross-product (~200 traces) |

---

## 3. Implemented Components

1. **Memory-Mapped Data Loader ([`load_dataset.py`](file:///d:/new%20DPA/replication/phase7_real_hardware/load_dataset.py))**:
   - Zero-copy streaming via `mmap_mode='r'` prevents multi-gigabyte RAM exhaustion.
   - Transparently handles masked vs. unmasked structures and share combinations.
   - Enforces strict row-by-row alignment between traces and sensitive metadata.

2. **Automated Regression Suite ([`test_real_hardware_regression.py`](file:///d:/new%20DPA/replication/phase7_real_hardware/test_real_hardware_regression.py))**:
   - Validates trace dimensions (`10000, 10000`), dtypes (`int16`), and metadata ranges against $q = 3329$.
   - Runs against real extracted chunks when present or synthetic mocks during download.

3. **Empirical SNR & TVLA Characterization ([`compute_real_snr.py`](load_dataset.py))**:
   - Computes Signal-to-Noise Ratio (SNR) on Share 0 ($M$) and Share 1 ($sk - M$).
   - Pointwise fixed-vs-variable Welch's t-test (TVLA) across EM time samples.
   - Output plots:

| Per-Share SNR across 10,000 Samples (`snr_mkm4_shares.png`) | Full 10,000-Sample Welch's t-test TVLA (`tvla_full_10k.png`) |
| :---: | :---: |
| ![Per-Share SNR Analysis](plots/snr_mkm4_shares.png) | ![Full TVLA Curve](plots/tvla_full_10k.png) |

4. **Phase E: Unmasked `pqm4` 1st-Order CPA ([`run_pqm4_cpa.py`](run_pqm4_cpa.py))**:
   - Targets Cortex-M4 assembly accumulator intermediate $HW_{32}(a_0 \cdot b_0 + \text{mont\_red}(a_1 \cdot \zeta_0) \cdot b_1)$ at POI sample 1568.
   - Eliminates single-operand ghost peaks and reproduces ~40-trace convergence (Mean rank $2.90 \pm 2.23$ at $N=40$; 70% Rank 0 at $N=60$).
   - Regression test: `test_pqm4_cpa_regression.py` (Step 15 in master suite).

| Unmasked `pqm4` CPA Convergence (`pqm4_cpa_convergence.png`) |
| :---: |
| ![Unmasked CPA](plots/pqm4_cpa_convergence.png) |

5. **Phase D: Masked `mkm4` 2nd-Order CPA ([`run_mkm4_2nd_order_cpa.py`](run_mkm4_2nd_order_cpa.py))**:
   - 3-sample smoothed centered cross-product at joint POI sample 299: $P_i = (T_{0, i} - \mu_0) \times (T_{1, i} - \mu_1)$.
   - Mask-averaged circular covariance leakage model computed across all 3,329 candidates in $\mathbb{Z}_q$ via FFT circular convolution.
   - Recovers target key $b[1] = 1422$ at **Rank 0 at $N = 180, 200, 250, 300$ traces** (True Corr = 0.3066 vs Max Wrong = 0.3040 at $N=200$).
   - Regression test: `test_mkm4_cpa_regression.py` (Step 16 in master suite).

| Masked `mkm4` 2nd-Order CPA Convergence (`mkm4_2nd_order_cpa_convergence.png`) |
| :---: |
| ![Masked CPA](plots/mkm4_2nd_order_cpa_convergence.png) |

6. **Phase F: Learned Combining Function ([`run_learned_combiner.py`](run_learned_combiner.py))**:
   - Two-Branch Neural Network trained with Adam on Pearson correlation loss using variable-key traces (`100k_capture_all_2`).
   - Evaluated on fixed-key traces without key knowledge: achieves **Rank 0 at $N = 180, 200, 220$**.
   - Outperforms baseline CPA at $N = 220$ (Learned Rank 0 vs Baseline Rank 1) with 8$\times$ higher Rank-0 rate under resampling.
   - Regression test: `test_learned_combiner_regression.py` (Step 18 in master suite).

| Learned Combining Function Neural Network vs. Baseline (`learned_combiner_vs_baseline.png`) |
| :---: |
| ![Learned Combiner](plots/learned_combiner_vs_baseline.png) |

---

## 4. Execution Instructions

```powershell
# 1. Run zero-copy memory-mapped dataset loader regression
python replication/phase7_real_hardware/test_real_hardware_regression.py

# 2. Run unmasked pqm4 1st-order CPA (~40 traces)
python replication/phase7_real_hardware/run_pqm4_cpa.py

# 3. Run masked mkm4 2nd-order CPA (~180 traces)
python replication/phase7_real_hardware/run_mkm4_2nd_order_cpa.py

# 4. Run formal negative controls (permuted pairing & off-target baseline)
python replication/phase7_real_hardware/run_negative_controls_full.py

# 5. Run Two-Branch Neural Network learned combiner
python replication/phase7_real_hardware/run_learned_combiner.py
```

