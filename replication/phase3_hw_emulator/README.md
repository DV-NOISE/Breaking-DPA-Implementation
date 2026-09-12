# Phase 3: Hardware Trace Emulator (.TRS Generation)

Phase 3 bridges mathematical simulation with physical hardware security evaluation. It provides a software emulator modeling the electromagnetic (EM) and power side-channel emissions of an **ARM Cortex-M4 32-bit microcontroller** during Kyber NTT pair-pointwise multiplication.

The output is formatted as a standard **Riscure Inspector `.TRS` trace file**, matching the exact file format used by physical side-channel acquisition oscilloscopes.

---

## 1. Key Features & Modeling

- **Cortex-M4 Pipelining & Inertia**:
  - Emulates 3-stage pipeline transitions where intermediate state leakage is combined with previous register bus contents.
- **Hamming Weight Leakage Model**:
  - Maps 32-bit arithmetic operations to power/EM consumption via bitwise Hamming weight:
    $$\text{Leakage}(x) = \text{HW}(x) + \alpha \cdot \text{HW}(x_{\text{prev}}) + \mathcal{N}(0, \sigma^2)$$
- **Trace Averaging**:
  - Implements $N = 15$ trace averaging (matching the physical acquisition setup in the paper) to reduce ambient noise before correlation analysis.
- **Output Compatibility**:
  - Generates binary `.TRS` traces with standard headers (sample count, trace count, scale factors) consumable by open-source tooling (e.g., `trsfile`, ChipWhisperer) and our Phase 4 attack engine.

---

## 2. Source Files & Architecture

| File | Language | Purpose |
| :--- | :---: | :--- |
| [`generate_synthetic_trs.py`](generate_synthetic_trs.py) | Python | Hardware emulator generating `.TRS` traces from secret keys and known ciphertext inputs. |
| [`view_target.py`](view_target.py) | Python | Header and waveform inspection utility for generated `.TRS` files. |
| [`coefficients.txt`](coefficients.txt) | Text | Target secret key and ciphertext polynomial coefficients. |
| [`traces/`](traces/) | Directory | Storage directory for generated `.TRS` binary trace files. |
| [`trace_visualization.png`](trace_visualization.png) | Image | Multi-sample oscilloscope waveform visualization. |

---

## 3. Scope & Scientific Context

> [!IMPORTANT]
> **Scope Clarification**: The traces generated in Phase 3 are **synthetic software-emulated traces** designed to evaluate and verify the algorithmic pipeline of Phase 4 in a controlled unit-test environment.
> 
> They are **not** physical oscilloscope measurements from silicon. In physical laboratory settings, the authors recorded EM traces over an STM32F405 target using an EM probe, requiring extensive template profiling (43M to 105M templates across physical OTAs) to overcome environmental noise and clock jitter.

---

## 4. Reproduction Instructions

### Step 1: Synthesize Hardware Trace File (.TRS)
```powershell
python replication/phase3_hw_emulator/generate_synthetic_trs.py
```
*Generates `traces/synthetic_kyber_cortexm4.trs` and updates `trace_visualization.png`.*

### Step 2: Inspect Trace File Metadata
```powershell
python replication/phase3_hw_emulator/view_target.py
```
*Displays header parameters, sample length, data types, and waveform preview statistics.*
