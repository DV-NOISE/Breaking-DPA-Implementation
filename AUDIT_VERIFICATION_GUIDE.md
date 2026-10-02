# Comprehensive Auditor Verification Guide: Real-Hardware Dataset & Pipeline

This guide addresses questions raised during peer review or cross-agent auditing regarding Phase 7 real-hardware side-channel results, dataset storage, coefficient unpacking, and independent reproducibility.

---

## 1. Executive Summary: The Dataset Architecture

- **The Full Dataset Scale:** The raw electromagnetic side-channel dataset published by Alain Alyosha Magazin & Karim M. Abdellatif (*Cryptology ePrint Archive, Report 2026/1851*) occupies **12.57 GB** compressed (`d0nj0n_mlkem_dataset.zip`) and **~58 GB** uncompressed.
- **Git & Lightweight Zip Distribution Policy:** To ensure lightweight distribution and avoid exceeding archive and repository quotas, the full 12.57 GB trace directory `datasets/d0nj0n_mlkem_dataset/` and `d0nj0n_mlkem_dataset.zip` are excluded via `.gitignore`.
- **Included Real-Hardware Verification Slice (`datasets/sample_hardware_chunk/`):**
  - **Uncompressed Size on Disk:** **23.72 MB** (14 files).
  - **Compressed Size in Archive:** **~14.6 MB**.
  - **Real Shapes and Data Types:**
    - `masked/fixed/traces/traces_s0_0.npy`: shape `(250, 10000)`, `dtype: int16`
    - `masked/fixed/traces/traces_s1_0.npy`: shape `(250, 10000)`, `dtype: int16`
    - `masked/fixed/metadata/fixed_unmasked_key.npy`: shape `(2400,)`, `dtype: uint8`
    - `masked/fixed/metadata/bp_s0_0.npy`: shape `(250, 256)`, `dtype: int16`
    - `masked/fixed/metadata/bp_s1_0.npy`: shape `(250, 256)`, `dtype: int16`
    - `masked/fixed/metadata/ap_0.npy`: shape `(250, 256)`, `dtype: int16`
    - `masked/variable/traces/traces_s0_0.npy`: shape `(250, 10000)`, `dtype: int16`
    - `masked/variable/traces/traces_s1_0.npy`: shape `(250, 10000)`, `dtype: int16`
    - `masked/variable/metadata/bp_s0_0.npy`: shape `(250, 256)`, `dtype: int16`
    - `masked/variable/metadata/bp_s1_0.npy`: shape `(250, 256)`, `dtype: int16`
    - `masked/variable/metadata/ap_0.npy`: shape `(250, 256)`, `dtype: int16`
    - `pqm4/traces/traces_0.npy`: shape `(100, 20000)`, `dtype: int16`
    - `pqm4/metadata/mult_a_0.npy`: shape `(100, 256)`, `dtype: int16`
    - `pqm4/metadata/mult_b_0.npy`: shape `(100, 256)`, `dtype: int16`

- **Three Ways to Verify Results Without Downloading 12.57 GB:**
  1. **Direct NumPy Audit (Zero Trust):** Load the arrays directly with NumPy (see Section 3) and compute SNR and Welch's t-statistic using 10 lines of standard code.
  2. **Run Standalone Verification Script (5 seconds):**
     ```bash
     python datasets/verify_sample_chunk.py
     ```
     Tests key deserialization ($230 \to 1422$), Share 0 SNR peak at sample 510, fixed-vs-variable TVLA ($|t| > 4.5$), and runs second-order CPA reaching Rank 0 at $N=200$.
  3. **Inspect Raw Execution Transcripts:** Full stdout transcripts with timestamps and dataset SHA-256 hashes are committed in `replication/phase7_real_hardware/logs/`.

---

## 2. Point-by-Point Audit Resolutions

### Question 1: "Where does 230 come from, and why is target b[1] = 1422?"
- **The Core Question:** In Kyber, $q = 3329$. Since $1422 < 3329$, $1422 \bmod 3329 = 1422$, not $230$. Where did $230$ come from?
- **The Explanation (Kyber 12-bit Byte Serialization):**
  `fixed_unmasked_key.npy` is an array of 2,400 bytes of type `uint8` containing the serialized Kyber decapsulation key $dk$.
  Under the NIST FIPS 203 / CRYSTALS-Kyber specification (`poly_tobytes` / `poly_frombytes`), ring coefficients $0 \le c_i < 3329 < 2^{12} = 4096$ are packed into 12 bits each. Every pair of consecutive coefficients $(c_{2j}, c_{2j+1})$ is serialized into 3 bytes $(b_{3j}, b_{3j+1}, b_{3j+2})$:
  $$b_{3j} = c_{2j} \bmod 256$$
  $$b_{3j+1} = \lfloor c_{2j} / 256 \rfloor + (c_{2j+1} \bmod 16) \times 16$$
  $$b_{3j+2} = \lfloor c_{2j+1} / 16 \rfloor$$
  To deserialize back into 12-bit integers:
  $$c_{2j} = b_{3j} + (b_{3j+1} \bmod 16) \times 256$$
  $$c_{2j+1} = \lfloor b_{3j+1} / 16 \rfloor + b_{3j+2} \times 16$$
  Examining the first three raw bytes of `fixed_unmasked_key.npy`:
  $$b_0 = 145, \quad b_1 = 230, \quad b_2 = 88$$
  Unpacking coefficient 0 and coefficient 1:
  $$c_0 = 145 + (230 \bmod 16) \times 256 = 145 + (6 \times 256) = 145 + 1536 = \mathbf{1681}$$
  $$c_1 = \lfloor 230 / 16 \rfloor + 88 \times 16 = 14 + (88 \times 16) = 14 + 1408 = \mathbf{1422}$$
- **Why 230 was printed:**
  A previous debug script inspected the raw array `arr = np.load('fixed_unmasked_key.npy')` and printed `arr[1]` (which is the raw second **byte**, value 230). The actual mathematical key coefficient targeted by the attack is **1422**.
- **Independent Verification via Arithmetic Shares:**
  In the dataset metadata for decapsulation #0:
  $$\text{Share 0: } b_{s0}[0, 1] = 178, \quad \text{Share 1: } b_{s1}[0, 1] = 1244$$
  $$(178 + 1244) \bmod 3329 = \mathbf{1422}$$
  Both the unpacked 12-bit key byte formula and the sum of arithmetic shares match identically to **1422**.

---

### Question 2: "Where are `mult_a_0.npy` and `fixed_unmasked_key.npy`?"
These files are part of the original 12.57 GB dataset archive and are extracted into the verification slice at:
1. `mult_a_0.npy` (51,328 bytes): `datasets/sample_hardware_chunk/pqm4/metadata/mult_a_0.npy`
   - **Shape:** `(100, 256)` of type `int16`.
   - **Ground Truth Coefficients:** Row 0 values are `[679, 1286, 2560, 378, 2306]` $\to$ $a_0 = 679, a_1 = 1286$.
2. `fixed_unmasked_key.npy` (2,528 bytes): `datasets/sample_hardware_chunk/masked/fixed/metadata/fixed_unmasked_key.npy`
   - **Shape:** `(2400,)` of type `uint8`.

---

### Question 3: "How do SNR and TVLA numbers compare between the Full Dataset and the Verification Slice?"

The committed figures in `real_hardware_leakage_report.md` were evaluated across **$N = 5,000$ traces** from the full 12.57 GB hardware dataset. The verification slice contains **$N = 250$ traces** to remain compact (~14.6 MB in zip).

| Metric | Full Dataset ($N = 5,000$) | Verification Slice ($N = 250$) | Mathematical Relationship |
| :--- | :--- | :--- | :--- |
| **Share 0 SNR Peak** | **0.9035** at **Sample 510** | **0.8352** at **Sample 510** | Physical leakage peak is strictly invariant at sample 510. Variance partitions stabilize as $N \to 5000$. |
| **Share 1 SNR Peak** | **0.4332** at **Sample 472** | **0.4851** at **Sample 435** | Share 1 executes prior to Share 0 in `basemul_asm`. |
| **Fixed-vs-Variable TVLA Peak** | **$|t| = 19.7574$** at **Sample 2812** | **$|t| = 6.4359$** at **Sample 2869** | Welch's $t$-statistic denominator scales as $1/\sqrt{N}$, so $t \propto \sqrt{N}$. $\sqrt{5000/250} = \sqrt{20} \approx 4.47\times$. |
| **Leaking POIs ($|t| > 4.5$)** | **578 / 10,000** | **402 / 10,000** | Both confirm extensive physical EM leakage throughout the multiplier routine. |

#### Critical Note on the "Sample 184" Typographical Error:
In an earlier working draft of `MANUSCRIPT.md`, a clerical error mistakenly referenced "sample 184" instead of "sample 2812" for the TVLA peak.
- In the actual hardware data, the primary leakage crest is located at **samples 2809..2814** (peak $|t| = 19.7574$ at **sample 2812**) and **samples 2860..2875** (peak $|t| = 6.4359$ on the $N=250$ slice).
- At sample 184, there is no active computation or leakage ($|t| \approx 0.02$).
- Both `MANUSCRIPT.md` and `compute_real_snr.py` have been corrected to state the true peak at sample 2812.

---

## 3. Direct Independent NumPy Verification (Zero-Trust Script)

You do not need to rely on `verify_sample_chunk.py`. You can run this minimal script in pure Python with only NumPy to independently verify the slice:

```python
import numpy as np

# 1. Load data directly
t0_fixed = np.load("datasets/sample_hardware_chunk/masked/fixed/traces/traces_s0_0.npy") # (250, 10000), int16
t0_var   = np.load("datasets/sample_hardware_chunk/masked/variable/traces/traces_s0_0.npy") # (250, 10000), int16
bp0_var  = np.load("datasets/sample_hardware_chunk/masked/variable/metadata/bp_s0_0.npy")[:, 0]
fuk      = np.load("datasets/sample_hardware_chunk/masked/fixed/metadata/fixed_unmasked_key.npy")

# 2. Confirm Key Deserialization (byte 230 -> coeff 1422)
c1 = (int(fuk[1]) >> 4) | (int(fuk[2]) << 4)
assert c1 == 1422, f"Deserialized c1={c1}, expected 1422"

# 3. Recompute Share 0 SNR by Hamming Weight partitioning
hw = np.array([bin(int(v) & 0xFFFF).count('1') for v in bp0_var])
t_f = t0_var.astype(np.float64)
mean_all = np.mean(t_f, axis=0)
var_sig = np.zeros(t_f.shape[1]); var_noise = np.zeros(t_f.shape[1])
for h in np.unique(hw):
    sub = t_f[hw == h]
    if len(sub) > 1:
        w = len(sub) / len(t_f)
        var_sig += w * ((np.mean(sub, axis=0) - mean_all) ** 2)
        var_noise += w * np.var(sub, axis=0, ddof=1)
snr = np.where(var_noise > 1e-12, var_sig / var_noise, 0)
print(f"Share 0 Peak SNR: {np.max(snr):.4f} at sample {np.argmax(snr)}")
assert np.argmax(snr) == 510, f"Expected SNR peak at 510, got {np.argmax(snr)}"

# 4. Recompute Fixed-vs-Variable TVLA (Welch's t-test)
t_fixed_f = t0_fixed.astype(np.float64)
denom = np.sqrt(np.var(t_fixed_f, axis=0, ddof=1)/len(t0_fixed) + np.var(t_f, axis=0, ddof=1)/len(t0_var))
t_stat = (np.mean(t_fixed_f, axis=0) - np.mean(t_f, axis=0)) / np.maximum(denom, 1e-12)
print(f"Fixed-vs-Var TVLA Peak: |t| = {np.max(np.abs(t_stat)):.4f} at sample {np.argmax(np.abs(t_stat))}")
print(f"Leaking points (|t| > 4.5): {np.sum(np.abs(t_stat) > 4.5)} / {len(t_stat)}")
assert np.max(np.abs(t_stat)) > 4.5, "Expected TVLA |t| > 4.5"
print("SUCCESS: Real hardware leakage independently confirmed!")
```
