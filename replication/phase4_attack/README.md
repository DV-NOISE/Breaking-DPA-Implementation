# Phase 4: Correlation Attack Engine & Key Recovery

Phase 4 implements the side-channel cryptanalysis engine. It ingests hardware-emulated `.TRS` traces, builds intermediate Hamming weight templates for secret key hypotheses, calculates **Pearson correlation coefficients**, ranks the hypotheses, and extracts the target secret polynomial.

---

## 1. Attack Methodology

For each secret candidate share pair $(a_0, a_1)$ and known public polynomial coefficient $b_1$:
1. **Template Formulation**:
   Construct the expected 5-point intermediate Hamming weight vector:
   $$\mathbf{h}(a_0, a_1) = [H_0, H_1, H_2, H_3, H_4]$$
2. **Pearson Correlation Matching**:
   Compute the Pearson correlation coefficient between the hypothesized template $\mathbf{h}$ and the trace segment $\mathbf{T}$ at peak sample points:
   $$\rho(a_0, a_1) = \frac{\sum_{i=1}^5 (h_i - \bar{h})(T_i - \bar{T})}{\sqrt{\sum_{i=1}^5 (h_i - \bar{h})^2 \sum_{i=1}^5 (T_i - \bar{T})^2}}$$
3. **Hypothesis Ranking**:
   Sort all candidates by descending correlation $\rho$. The hypothesis with the highest correlation is ranked as Top-1.
4. **Key Extraction**:
   Export the top-ranked candidates to reconstruct the 256-coefficient Kyber secret key polynomial.

---

## 2. Key Objectives & Experimental Scope

- **Algorithmic Self-Consistency Check**:
  - Evaluates the correlation attack engine on a reduced **25-candidate centered subspace**:
    $$(a_0, a_1) \in \{-2, -1, 0, 1, 2\}^2 \subset [0, q-1]^2$$
    under synthetic trace noise ($\sigma = 0.012$).
  - **Results**:
    - **175 / 256 coefficients (68.36%)** successfully recovered at **Rank 1**.
    - All 256 coefficients recovered within **Rank $\le 3$**, demonstrating complete algorithmic correctness of the correlation matching and ranking pipeline.

> [!IMPORTANT]
> **Scope & Honest Framing**:
> This test is an **end-to-end self-consistency unit test** of our correlation software pipeline on a reduced 25-candidate subspace.
> 
> It is **not** equivalent to the paper's full masked-share attack:
> - In Kyber's actual masked-share setting, the two shares $s'_1, s''_1$ are uniformly distributed modulo $q$, requiring a search across $q^2 \approx 1.1 \times 10^7$ candidate pairs under physical noise ($\sigma \ge 0.5$).
> - On physical hardware, the paper demonstrates that single-trace full key recovery requires **78M to 105M templates via hybrid $q^2 + \text{OTA}$ to achieve 43% to >90% success**.

---

## 3. Source Files & Architecture

| File | Language | Purpose |
| :--- | :---: | :--- |
| [`run_attack.py`](run_attack.py) | Python | Core Pearson correlation attack engine parsing `.TRS` traces and extracting key candidates. |
| [`view_key.py`](view_key.py) | Python | Formats and validates recovered secret keys against target ground-truth vectors. |
| [`recovered_secret_key.npy`](recovered_secret_key.npy) | NumPy | Binary array containing recovered 256-coefficient polynomial values. |

---

## 4. Reproduction Instructions

### Step 1: Execute Correlation Attack on Emulated Traces
```powershell
python replication/phase4_attack/run_attack.py
```
*Outputs rank statistics (Top-1: 175/256) and exports `recovered_secret_key.npy`.*

### Step 2: Validate Recovered Key Against Ground Truth
```powershell
python replication/phase4_attack/view_key.py
```
*Displays centered representation $\{-2, -1, 0, 1, 2\}$, rank progression, and match counts.*
