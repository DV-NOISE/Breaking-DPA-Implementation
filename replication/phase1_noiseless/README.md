# Phase 1: Noiseless Collision Theory & Multiplicity Verification

Phase 1 establishes the mathematical foundation of the side-channel attack: **Hamming weight collision theory** during the pair-pointwise NTT polynomial multiplication of Kyber on an ARM Cortex-M4.

In the noiseless regime ($\sigma = 0$), intermediate register states produce discrete Hamming weight signatures. By simulating these transitions across all secret candidate shares, we quantify the candidate reduction power of single-trace side-channel leakage.

---

## 1. Key Objectives & Results

- **Replicate Figure 5 (Upper Table - $q$-templates)**:
  - **Replicated Mean**: **90.0136%** 1-way match probability across all 128 NTT roots ($\zeta$).
  - **Paper Target**: **90.01%** ($\approx 90\%$ uniqueness).
- **Replicate Figure 5 (Lower Table - $q^2$-templates)**:
  - **Replicated Mean**: **99.7316%** 1-way match probability across all 128 NTT roots.
  - **Paper Target**: **99.74%** ($\approx 99.7\%$ uniqueness).
  - **Root 0 ($\zeta_0 = 2226$)**: Evaluates to **0.997523**, exactly matching the author reference dump (`0.9975237453476766`).
- **Validate Instruction-Level Checkpoints**:
  - **Instruction 1** (`poly0` leakage): **23 / 23 bins match 100%** against `author_files/checkpoints_and_datasets/q^2-data-instr1.csv`.
  - **Instruction 2** (`smultt` $a_1 \cdot b_1$): **254 / 254 bins match 100%** against `q^2-data-instr2.csv`.
  - **Instruction 3** (`smulbt` Montgomery step 1): **1,825 / 1,825 bins match 100%** against `q^2-data-instr3.csv`.
  - **Instructions 4–12**: Open discrepancy documented below.

---

## 2. Source Files & Architecture

| File | Language | Purpose |
| :--- | :---: | :--- |
| [`sim_engine.cpp`](sim_engine.cpp) | C++17 | High-speed Montgomery & Barrett multiplication simulator modeling Cortex-M4 assembly instructions. |
| [`sim_engine.exe`](sim_engine.exe) | Binary | Precompiled 64-bit optimized executable (`g++ -O3`). |
| [`run_figure5.py`](run_figure5.py) | Python | Evaluates collision multiplicity frequencies across all 128 NTT roots for $q$ and $q^2$ templates. |
| [`verify_checkpoints.py`](verify_checkpoints.py) | Python | Validates generated checkpoint distributions against author reference CSVs. |
| [`verify_author_zetas.py`](verify_author_zetas.py) | Python | Parses all 128 NTT roots from Dr. Kirthi (`author_files/raw_zetas_128/`), validating 99.69% Figure 5 match. |
| [`test_sim_regression.py`](test_sim_regression.py) | Python | Regression test asserting numerical ground truths and static source code packing consistency. |
| [`compute_expectation.py`](compute_expectation.py) | Python | Statistical expectation calculation tool for unique states across roots. |
| [`zetas/`](zetas/) | Directory | Precomputed simulation collision dumps for all 128 individual NTT roots. |

---

## 3. Discrepancies & Audit Resolutions

### A. The $q^2$ Halfword Packing Bug Fix
- **Root Cause**: Early simulation code packed the secret candidate register as `poly0 = (a1 << 16) + a0;` (inverting high and low 16-bit halfwords). This produced an erroneous $q^2$ 1-way match of `0.999346`.
- **Resolution**: Corrected to `poly0 = (static_cast<int32_t>(a0) << 16) | (static_cast<uint16_t>(a1));` matching the authors' reference [`q-squared-attack-sim.cpp`](../../author_files/checkpoints_and_datasets/q-squared-attack-sim.cpp#L54). This restored the true collision rate of **0.997523** (Paper: 0.9974).

### B. Banegas Erratum ($b_1 \in [0, q-1]$)
- Appendix B of the ACNS 2024 paper stated that the theoretical expectation was evaluated over $b_1 \in [1, q-1]$ (excluding 0).
- Author correspondence with Dr. Gustavo Banegas confirmed that the actual simulation evaluated over all $q = 3329$ coefficients ($b_1 \in [0, q-1]$ including 0), which resolves the slight averaging divergence.

### C. Open Discrepancy for Instructions 4–12
- Instructions 1, 2, and 3 match the authors' reference CSVs with 100% bin fidelity.
- At Instruction 4 (`smlabb` accumulation and $\zeta$ multiplication), generated bins diverge (1,582 bins vs. author CSV 1,391 bins). Because the authors provided the static CSV dumps but not the generator script that produced them, this remains an open discrepancy currently under correspondence with the authors.

---

## 4. Reproduction Instructions

### Step 1: Run Automated Regression Test
```powershell
python replication/phase1_noiseless/test_sim_regression.py
```
*Asserts:*
- `q_single(2226) == 0.869559`
- `q2_single(2226) == 0.997523`
- Asserts absent buggy `0.999346`
- Verifies static AST packing across both `sim_engine.cpp` and `noisy_sim.cpp`.

### Step 2: Verify Checkpoints Against Author Reference CSVs
```powershell
python replication/phase1_noiseless/verify_checkpoints.py
```
*Expected Output:*
```
[+] Instruction 1: EXACT MATCH (23 bins match 100%)
[+] Instruction 2: EXACT MATCH (254 bins match 100%)
```

### Step 3: Generate Full Figure 5 Multiplicity Tables
```powershell
python replication/phase1_noiseless/run_figure5.py
```
*Expected Output:*
```
OVERALL EXPECTED MEANS ACROSS ALL 128 ZETAS (q-templates):
  1-way match mean: 0.900136  (Paper Figure 5: 90.01%)
  2-way collision:  0.085467  (Paper Figure 5: 8.55%)
  3-way collision:  0.011340  (Paper Figure 5: 1.13%)

OVERALL EXPECTED MEANS ACROSS ALL 128 ZETAS (q^2-templates):
  1-way match mean: 0.997316  (Paper Figure 5: 99.74%)
  2-way collision:  0.002645  (Paper Figure 5: 0.25%)
  3-way collision:  1.61e-05  (Paper Figure 5: 1.01e-05)
```

### Step 4: Verify Author 128 NTT Roots Dataset (`raw_zetas_128/`)
```powershell
python replication/phase1_noiseless/verify_author_zetas.py
```
*Expected Output:*
```
[+] Successfully parsed all 128 NTT root files!
[+] Over 1.5 million candidate pairs evaluated across 128 roots.
[+] Overall Empiric 1-way unique match: 99.6881% (Matches Figure 5 Lower Curve ~99.74%)
[+] Overall Empiric 2-way collision:    0.2729%
```

### (Optional) Recompile Simulation Engine
```powershell
g++ -O3 replication/phase1_noiseless/sim_engine.cpp -o replication/phase1_noiseless/sim_engine.exe
```

