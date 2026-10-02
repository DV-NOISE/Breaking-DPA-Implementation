# Physical Side-Channel Datasets for Kyber / ML-KEM

This directory holds the raw electromagnetic (EM) side-channel trace captures and metadata for STM32F407 (ARM Cortex-M4) running CRYSTALS-Kyber.

> [!IMPORTANT]
> **Git Storage Policy**:
> Raw trace files (`.npy`, `.zip`, `.trs`) are **intentionally excluded from Git tracking** via `.gitignore` because the extracted dataset occupies **~58 GB**, far exceeding GitHub's 100 MB individual file limit and repository quotas.
> Only this `README.md` and the verified checksum file `d0nj0n_mlkem_dataset_sha256.txt` are tracked in version control.

---

## 1. Primary Dataset: Magazin & Abdellatif (ePrint 2026/1851)

- **Source Paper**: Alain Alyosha Magazin & Karim M. Abdellatif, *"Open EM Dataset for ML-KEM (Kyber) Implementations on ARM Cortex-M4"*, Cryptology ePrint Archive, Report 2026/1851.
- **Hardware Platform**: STM32F407 (ARM Cortex-M4 @ 84 MHz)
- **Acquisition**: Near-field Langer EM probe @ 6.25 GS/s, 10,000 samples/trace centered on `basemul_asm`.
- **Target Implementations**:
  - `reference`: Unprotected C reference (Kyber-512)
  - `pqm4`: Hand-optimized assembly implementation (Kyber-512)
  - `mkm4`: First-order masked software implementation (Kyber-768), with per-share traces ($s_0, s_1$)
- **Archive Size**: 12.57 GB (`d0nj0n_mlkem_dataset.zip`)
- **Verified SHA-256 Checksum**:
  ```
  4eed0b61b028f91b0d2568b04baabcca6a4a3dbb450cd3613e2fc01f3fd20143
  ```

---

## 2. Automated Download & Setup

To download, verify, and unpack the dataset automatically into this directory, run:

```powershell
python download_dataset.py
```

This script will:
1. Stream the 12.57 GB archive directly from the authors' Cloudflare R2 repository.
2. Verify the SHA-256 checksum against `d0nj0n_mlkem_dataset_sha256.txt`.
3. Extract the `.npy` chunked traces and coefficients into `datasets/d0nj0n_mlkem_dataset/`.

---

## 3. Zero-Setup 23.7 MB Verification Slice (`sample_hardware_chunk/`)

To enable immediate, zero-download validation of real-hardware ARM Cortex-M4 EM traces, we have committed a self-contained 23.7 MB audit slice in [`sample_hardware_chunk/`](sample_hardware_chunk/):
- **Unmasked `pqm4`**: 100 physical EM traces (10,000 samples each) with matched `mult_a` and `mult_b` coefficients.
- **Masked `mkm4` Fixed-Key**: 100 physical EM traces per share (Share 0: Mask $M$, Share 1: $sk - M$) with metadata.
- **Masked `mkm4` Variable-Key**: 100 physical EM traces per share with metadata.

### Standalone 5-Second Verification Script
Run the automated slice integrity checker directly:
```powershell
python datasets/verify_sample_chunk.py
```
*Validates array dtypes (`int16`), dimensions (`100, 10000`), coefficient bounds modulo $q = 3329$, and computes non-trivial empirical SNR across Share 0 and Share 1.*

---

## 4. Lightweight Testing Without Full 12.57 GB Dataset Download

If working in a constrained environment or reviewing the code without downloading the full 12.57 GB archive:
- The sample hardware slice (`datasets/sample_hardware_chunk/`) and the mock fallback (`replication/phase7_real_hardware/mock_eval_data/`) provide zero-setup inputs.
- All 18 regression tests in `python replication/run_all_tests.py` validate algorithmic logic, memory-mapped loader interfaces, CPA attacks, and countermeasure simulations in ~45 seconds with 100% PASS.

