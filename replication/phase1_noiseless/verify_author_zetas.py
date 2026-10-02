#!/usr/bin/env python3
"""
Validation Script: Ingestion and Verification of Author Multi-Zeta Simulation Dataset
Source: Received directly from Dr. Kirthivaasan Puniamurthy (Sept 19, 2026, zetas.zip).
Location: author_files/raw_zetas_128/

Validates that all 128 NTT root files exist, parses the collision distributions,
and asserts mathematical consistency with the paper's Figure 5 lower table (99.74%).
"""

import os
import sys

ZETAS = [
    2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653,
    3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254,
    817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670,
    2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628
]

def verify_author_zetas():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    zetas_dir = os.path.join(base_dir, "author_files", "raw_zetas_128")
    
    print("=" * 80)
    print("      VALIDATING AUTHOR RAW MULTI-ZETA SIMULATION DATASET (128 ROOTS)")
    print("=" * 80)
    print(f"[*] Ingesting from: {zetas_dir}")
    
    assert os.path.isdir(zetas_dir), f"Missing author zetas directory: {zetas_dir}"
    
    all_files = os.listdir(zetas_dir)
    print(f"[*] Total files in archive directory: {len(all_files)}")
    
    col_stats = {1: [], 2: [], 3: [], 4: [], 5: []}
    missing_files = []
    
    for i in range(64):
        for sign, zval in [("", ZETAS[i]), ("-", -ZETAS[i])]:
            fname = f"zeta-{i}-{zval}.dat"
            fpath = os.path.join(zetas_dir, fname)
            
            if not os.path.exists(fpath):
                missing_files.append(fname)
                continue
                
            file_stats = {1: [], 2: [], 3: [], 4: [], 5: []}
            with open(fpath, "r", errors="ignore") as f:
                for line in f:
                    for tok in line.strip().split(","):
                        for k in range(1, 6):
                            prefix = f"{k}:"
                            if prefix in tok:
                                try:
                                    file_stats[k].append(float(tok.split(":")[1]))
                                except ValueError:
                                    pass
                                    
            for k in range(1, 6):
                if file_stats[k]:
                    col_stats[k].append(sum(file_stats[k]) / len(file_stats[k]))
                    
    assert len(missing_files) == 0, f"Missing {len(missing_files)} expected zeta files: {missing_files[:5]}"
    assert len(col_stats[1]) == 128, f"Expected 128 roots, only parsed {len(col_stats[1])}"
    
    print(f"[+] All 128 NTT roots (64 +zeta, 64 -zeta) successfully verified and parsed.")
    print("-" * 80)
    print("MULTIPLICITY DISTRIBUTIONS (EXPECTATION OVER ALL 128 ROOTS):")
    
    mean_p1 = sum(col_stats[1]) / len(col_stats[1])
    mean_p2 = sum(col_stats[2]) / len(col_stats[2])
    mean_p3 = sum(col_stats[3]) / len(col_stats[3]) if col_stats[3] else 0.0
    
    print(f"  1-Way Unique Match Probability: {mean_p1:.6f} ({mean_p1 * 100:.4f}%) [Paper Fig 5: ~99.74%]")
    print(f"  2-Way Collision Probability:    {mean_p2:.6f} ({mean_p2 * 100:.4f}%) [Paper Fig 5: ~0.26%]")
    print(f"  3-Way Collision Probability:    {mean_p3:.6f} ({mean_p3 * 100:.4f}%) [Paper Fig 5: ~0.00%]")
    print("-" * 80)
    
    # Assert statistical consistency
    assert 0.995 <= mean_p1 <= 0.998, f"Mean 1-way {mean_p1} outside expected [0.995, 0.998]"
    assert 0.002 <= mean_p2 <= 0.004, f"Mean 2-way {mean_p2} outside expected [0.002, 0.004]"
    
    print("[+] SUCCESS: Author raw dataset strictly aligns with published Figure 5 lower table.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    verify_author_zetas()
