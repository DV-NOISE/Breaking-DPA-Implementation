"""
ML-KEM (Kyber) Real-Hardware Open EM Dataset Loader
Reference: Magazin & Abdellatif, ePrint 2026/1851, Section 4.1
Target: STM32F407 (ARM Cortex-M4), 6.25 GS/s EM captures windowed on pair-pointwise multiplication.

Dataset structure:
  {root}/{implementation}/{scenario}/
    traces/
      traces_i.npy           # (10000, 10000) int16 for reference and pqm4
      traces_s0_i.npy        # (10000, 10000) int16 for mkm4 (Share 0)
      traces_s1_i.npy        # (10000, 10000) int16 for mkm4 (Share 1)
    metadata/
      ap_i.npy               # (10000, 256) int16: poly a coefficients
      bp_i.npy               # (10000, 256) int16: poly b coefficients (ref/pqm4)
      bp_s0_i.npy            # (10000, 256) int16: poly b Share 0 (mkm4)
      bp_s1_i.npy            # (10000, 256) int16: poly b Share 1 (mkm4)
      ct_i.npy               # (10000, 768 or 1088) uint8: ciphertext bytes
      dk_i.npy               # (10000, 1632 or 2400) uint8: decapsulation keys (or single key in fixed)
    README.md
"""

import os
import glob
import numpy as np
from typing import Dict, Tuple, Optional, List, Union

KYBER_Q = 3329

class MLKEMDataset:
    def __init__(self, dataset_root: str, implementation: str = "mkm4", scenario: str = "variable", mmap_mode: str = "r"):
        """
        Initializes dataset reader with memory-mapped array access.
        
        Args:
            dataset_root: Root path where dataset is extracted (or contains extracted subfolders).
            implementation: 'reference', 'pqm4', or 'mkm4'.
            scenario: 'variable' (for SNR / profiling) or 'fixed' (for attacks).
            mmap_mode: 'r' for read-only memory-mapping (zero-copy), None for in-memory copy.
        """
        self.dataset_root = os.path.abspath(dataset_root)
        self.implementation = implementation.lower()
        self.scenario = scenario.lower()
        self.mmap_mode = mmap_mode
        self.is_masked = (self.implementation == "mkm4")
        
        assert self.implementation in ["reference", "pqm4", "mkm4"], f"Unknown implementation: {self.implementation}"
        assert self.scenario in ["variable", "fixed"], f"Unknown scenario: {self.scenario}"
        
        self.scenario_dir = self._resolve_scenario_dir()
        td = os.path.join(self.scenario_dir, "traces")
        if not os.path.isdir(td) and os.path.isdir(os.path.join(self.scenario_dir, "leakages")):
            td = os.path.join(self.scenario_dir, "leakages")
        self.traces_dir = td
        self.metadata_dir = os.path.join(self.scenario_dir, "metadata")
        
    def _resolve_scenario_dir(self) -> str:
        """Finds the scenario folder, handling author layout and naming variants."""
        scen_variants = [self.scenario, f"{self.scenario}_key"]
        
        candidates = []
        if self.implementation in ["reference", "ref"]:
            for sv in scen_variants:
                candidates.extend([
                    os.path.join(self.dataset_root, "pqm4-ref", "ref", sv),
                    os.path.join(self.dataset_root, "d0nj0n_mlkem_dataset", "pqm4-ref", "ref", sv),
                    os.path.join(self.dataset_root, "reference", sv),
                    os.path.join(self.dataset_root, "ref", sv),
                ])
        elif self.implementation == "pqm4":
            for sv in scen_variants:
                candidates.extend([
                    os.path.join(self.dataset_root, "pqm4-ref", "pqm4", sv),
                    os.path.join(self.dataset_root, "d0nj0n_mlkem_dataset", "pqm4-ref", "pqm4", sv),
                    os.path.join(self.dataset_root, "pqm4", sv),
                ])
        elif self.implementation == "mkm4":
            masked_folder = "100k_capture_fixedkey_all" if self.scenario == "fixed" else "100k_capture_all_2"
            candidates.extend([
                os.path.join(self.dataset_root, "masked", masked_folder),
                os.path.join(self.dataset_root, "d0nj0n_mlkem_dataset", "masked", masked_folder),
                os.path.join(self.dataset_root, "mkm4", self.scenario),
                os.path.join(self.dataset_root, "d0nj0n_mlkem_dataset", "mkm4", self.scenario),
            ])
            
        for p in candidates:
            if os.path.isdir(p):
                return p
        return candidates[0] if candidates else os.path.join(self.dataset_root, self.implementation, self.scenario)

    def is_available(self) -> bool:
        """Checks whether the resolved directory and trace files exist on disk."""
        if not os.path.isdir(self.traces_dir) or not os.path.isdir(self.metadata_dir):
            return False
        chunks = self.list_available_chunks()
        return len(chunks) > 0

    def list_available_chunks(self) -> List[int]:
        """Returns sorted list of chunk indices available in the traces directory."""
        if not os.path.isdir(self.traces_dir):
            return []
        
        indices = []
        if self.is_masked:
            pattern = os.path.join(self.traces_dir, "traces_s0_*.npy")
            matched = glob.glob(pattern)
            for f in matched:
                basename = os.path.splitext(os.path.basename(f))[0]
                parts = basename.split("_")
                try:
                    idx = int(parts[-1])
                    if os.path.exists(os.path.join(self.traces_dir, f"traces_s1_{idx}.npy")):
                        indices.append(idx)
                except ValueError:
                    pass
        else:
            pattern = os.path.join(self.traces_dir, "traces_*.npy")
            matched = glob.glob(pattern)
            for f in matched:
                basename = os.path.splitext(os.path.basename(f))[0]
                parts = basename.split("_")
                try:
                    idx = int(parts[-1])
                    indices.append(idx)
                except ValueError:
                    pass
        return sorted(list(set(indices)))

    def load_traces(self, chunk_idx: int, share: Optional[int] = None) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """
        Loads EM traces for a given chunk index using memory-mapping.
        
        For unmasked (reference, pqm4): returns ndarray of shape (N, 10000), int16.
        For masked (mkm4):
            If share is 0 or 1: returns ndarray of shape (N, 10000) for that share.
            If share is None: returns tuple (traces_s0, traces_s1).
        """
        if self.is_masked:
            if share in [0, 1]:
                fn = os.path.join(self.traces_dir, f"traces_s{share}_{chunk_idx}.npy")
                if not os.path.exists(fn):
                    raise FileNotFoundError(f"Trace file not found: {fn}")
                return np.load(fn, mmap_mode=self.mmap_mode)
            elif share is None:
                fn0 = os.path.join(self.traces_dir, f"traces_s0_{chunk_idx}.npy")
                fn1 = os.path.join(self.traces_dir, f"traces_s1_{chunk_idx}.npy")
                if not os.path.exists(fn0) or not os.path.exists(fn1):
                    raise FileNotFoundError(f"Trace files for chunk {chunk_idx} not found: {fn0}, {fn1}")
                t0 = np.load(fn0, mmap_mode=self.mmap_mode)
                t1 = np.load(fn1, mmap_mode=self.mmap_mode)
                return t0, t1
            else:
                raise ValueError(f"Invalid share index {share}; must be 0, 1, or None.")
        else:
            fn = os.path.join(self.traces_dir, f"traces_{chunk_idx}.npy")
            if not os.path.exists(fn):
                raise FileNotFoundError(f"Trace file not found: {fn}")
            return np.load(fn, mmap_mode=self.mmap_mode)

    def load_metadata(self, chunk_idx: int) -> Dict[str, np.ndarray]:
        """
        Loads metadata arrays for a given chunk.
        Returns dict containing:
          'ap': poly a coefficients (N, 256) int16
          'bp': poly b coefficients (N, 256) int16 (or 'bp_s0', 'bp_s1' for mkm4)
          'ct': ciphertext (N, bytes) uint8
          'dk': decapsulation key (N, bytes) uint8 (or single key in fixed)
        """
        meta = {}
        # 1. ap (public operand in mkm4; secret in reference/pqm4)
        for name in [f"ap_{chunk_idx}.npy", f"mult_a_{chunk_idx}.npy"]:
            p = os.path.join(self.metadata_dir, name)
            if os.path.exists(p):
                meta["ap"] = np.load(p, mmap_mode=self.mmap_mode)
                break
            
        # 2. bp (public in ref/pqm4; secret split into shares in mkm4)
        if self.is_masked:
            bp0_fn = os.path.join(self.metadata_dir, f"bp_s0_{chunk_idx}.npy")
            bp1_fn = os.path.join(self.metadata_dir, f"bp_s1_{chunk_idx}.npy")
            if os.path.exists(bp0_fn) and os.path.exists(bp1_fn):
                meta["bp_s0"] = np.load(bp0_fn, mmap_mode=self.mmap_mode)
                meta["bp_s1"] = np.load(bp1_fn, mmap_mode=self.mmap_mode)
                # Combined secret: (bp_s0 + bp_s1) mod q
                meta["bp_combined"] = (meta["bp_s0"].astype(np.int32) + meta["bp_s1"].astype(np.int32)) % KYBER_Q
        else:
            for name in [f"bp_{chunk_idx}.npy", f"mult_b_{chunk_idx}.npy"]:
                p = os.path.join(self.metadata_dir, name)
                if os.path.exists(p):
                    meta["bp"] = np.load(p, mmap_mode=self.mmap_mode)
                    break
                
        # 3. ct (ciphertext)
        ct_fn = os.path.join(self.metadata_dir, f"ct_{chunk_idx}.npy")
        if os.path.exists(ct_fn):
            meta["ct"] = np.load(ct_fn, mmap_mode=self.mmap_mode)
            
        # 4. dk (decapsulation key)
        dk_fn = os.path.join(self.metadata_dir, f"dk_{chunk_idx}.npy")
        if os.path.exists(dk_fn):
            meta["dk"] = np.load(dk_fn, mmap_mode=self.mmap_mode)
        else:
            # In fixed scenario, dk might be stored as dk.npy once
            dk_fixed = os.path.join(self.metadata_dir, "dk.npy")
            if os.path.exists(dk_fixed):
                meta["dk"] = np.load(dk_fixed, mmap_mode=self.mmap_mode)
                
        return meta

    def get_slice(self, chunk_idx: int, rows: Optional[slice] = None, samples: Optional[slice] = None, share: Optional[int] = None):
        """
        Convenience method to slice a subset of rows and time samples with zero copy overhead.
        """
        if rows is None:
            rows = slice(None)
        if samples is None:
            samples = slice(None)
            
        traces = self.load_traces(chunk_idx, share=share)
        if isinstance(traces, tuple):
            t0, t1 = traces
            return t0[rows, samples], t1[rows, samples]
        return traces[rows, samples]

    def verify_alignment(self, chunk_idx: int) -> bool:
        """
        Validates row-alignment across trace arrays and metadata.
        Row j of traces_i.npy must correspond to row j of ap, bp, ct, dk.
        """
        meta = self.load_metadata(chunk_idx)
        if self.is_masked:
            t0, t1 = self.load_traces(chunk_idx, share=None)
            n_rows = t0.shape[0]
            assert t1.shape[0] == n_rows, f"Share row count mismatch: {t0.shape[0]} vs {t1.shape[0]}"
        else:
            t = self.load_traces(chunk_idx)
            n_rows = t.shape[0]
            
        for k, arr in meta.items():
            if arr.ndim >= 2:
                assert arr.shape[0] == n_rows, f"Metadata {k} row count mismatch: {arr.shape[0]} vs {n_rows}"
        return True


def create_mock_dataset(target_dir: str, implementation: str = "mkm4", scenario: str = "variable", chunk_idx: int = 0, n_traces: int = 25, n_samples: int = 200):
    """
    Creates a validly formatted miniature mock dataset chunk matching Section 4.1 specifications.
    Allows testing loader, regression assertions, and SNR pipelines before/independent of large downloads.
    """
    scen_dir = os.path.join(target_dir, implementation, scenario)
    traces_dir = os.path.join(scen_dir, "traces")
    meta_dir = os.path.join(scen_dir, "metadata")
    os.makedirs(traces_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)
    
    rng = np.random.RandomState(42 + chunk_idx)
    
    # Generate metadata
    ap = rng.randint(0, KYBER_Q, size=(n_traces, 256), dtype=np.int16)
    np.save(os.path.join(meta_dir, f"ap_{chunk_idx}.npy"), ap)
    
    ct_bytes = 1088 if implementation == "mkm4" else 768
    ct = rng.randint(0, 256, size=(n_traces, ct_bytes), dtype=np.uint8)
    np.save(os.path.join(meta_dir, f"ct_{chunk_idx}.npy"), ct)
    
    dk_bytes = 2400 if implementation == "mkm4" else 1632
    dk = rng.randint(0, 256, size=(n_traces, dk_bytes), dtype=np.uint8)
    np.save(os.path.join(meta_dir, f"dk_{chunk_idx}.npy"), dk)
    
    if implementation == "mkm4":
        bp_s0 = rng.randint(0, KYBER_Q, size=(n_traces, 256), dtype=np.int16)
        bp_s1 = rng.randint(0, KYBER_Q, size=(n_traces, 256), dtype=np.int16)
        np.save(os.path.join(meta_dir, f"bp_s0_{chunk_idx}.npy"), bp_s0)
        np.save(os.path.join(meta_dir, f"bp_s1_{chunk_idx}.npy"), bp_s1)
        
        # Synthesize mock EM traces with deliberate leakage peaks to test SNR & TVLA
        # Share 0 leaks at sample index 50 (mask M)
        # Share 1 leaks at sample index 120 (sk - M)
        t0 = rng.normal(0, 100, size=(n_traces, n_samples)).astype(np.int16)
        t1 = rng.normal(0, 100, size=(n_traces, n_samples)).astype(np.int16)
        
        idx0 = min(50, n_samples // 3)
        idx1 = min(80, (2 * n_samples) // 3)
        for j in range(n_traces):
            # Leakage is proportional to Hamming Weight of secret intermediate
            hw0 = bin(int(bp_s0[j, 0]) & 0xFFFF).count('1')
            hw1 = bin(int(bp_s1[j, 0]) & 0xFFFF).count('1')
            t0[j, idx0] += int(hw0 * 45)
            t1[j, idx1] += int(hw1 * 45)
            
        np.save(os.path.join(traces_dir, f"traces_s0_{chunk_idx}.npy"), t0)
        np.save(os.path.join(traces_dir, f"traces_s1_{chunk_idx}.npy"), t1)
    else:
        bp = rng.randint(0, KYBER_Q, size=(n_traces, 256), dtype=np.int16)
        np.save(os.path.join(meta_dir, f"bp_{chunk_idx}.npy"), bp)
        
        traces = rng.normal(0, 100, size=(n_traces, n_samples)).astype(np.int16)
        for j in range(n_traces):
            hw_a = bin(int(ap[j, 0]) & 0xFFFF).count('1')
            traces[j, 40] += int(hw_a * 50)
        np.save(os.path.join(traces_dir, f"traces_{chunk_idx}.npy"), traces)
        
    return scen_dir


if __name__ == "__main__":
    print("Testing MLKEMDataset loader with synthetic mock chunk...")
    import tempfile
    import gc
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        scen = create_mock_dataset(tmpdir, implementation="mkm4", scenario="variable", chunk_idx=0, n_traces=15, n_samples=100)
        ds = MLKEMDataset(dataset_root=tmpdir, implementation="mkm4", scenario="variable")
        assert ds.is_available()
        assert ds.list_available_chunks() == [0]
        
        t0, t1 = ds.load_traces(0)
        print(f"[+] Loaded traces: s0={t0.shape} ({t0.dtype}), s1={t1.shape} ({t1.dtype})")
        meta = ds.load_metadata(0)
        print(f"[+] Loaded metadata: ap={meta['ap'].shape}, bp_s0={meta['bp_s0'].shape}, bp_s1={meta['bp_s1'].shape}")
        assert ds.verify_alignment(0)
        print("[+] Alignment verified successfully!")
        del t0, t1, meta, ds
        gc.collect()
