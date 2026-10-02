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

## 3. Lightweight Testing Without Full Dataset Download

If working in a constrained environment or reviewing the code without downloading 12.57 GB:
- The test suite and data loaders ([`replication/phase7_real_hardware/load_dataset.py`](../replication/phase7_real_hardware/load_dataset.py)) include a built-in mock fallback located in `replication/phase7_real_hardware/mock_eval_data/`.
- All 17 regression tests in `python replication/run_all_tests.py` can validate algorithmic logic, memory-mapped loader interfaces, and countermeasure simulations cleanly.
