"""
Phase E: Textbook Correlation Power Analysis (CPA) on Unmasked pqm4 Traces
Reference: Magazin & Abdellatif, ePrint 2026/1851, Section 4.3 (Donjon baseline: ~40 traces)
Hardware Target: STM32F407 (ARM Cortex-M4 @ 84 MHz), 6.25 GS/s EM captures windowed on poly_frombytes_mul

Target Operation:
  First iteration of pair-pointwise multiplication:
  accum = a0 * b0 + montgomery_reduce(a1 * zeta0) * b1
  where a0, a1 are the target secret key coefficients (ground truth: a0=679, a1=1286),
  b0, b1 are public ciphertext polynomial coefficients, and zeta0 = 2226.
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from load_dataset import MLKEMDataset, KYBER_Q

KYBER_QINV = -3327
ZETA0 = 2226
TARGET_SAMPLE = 1568  # Point of Interest (POI) for accumulator leakage in pqm4

def montgomery_reduce(prod: np.ndarray) -> np.ndarray:
    """Computes 16-bit Montgomery reduction (Q = 3329, QINV = -3327)."""
    m = (prod * KYBER_QINV).astype(np.int64) & 0xFFFF
    m = np.where(m >= 32768, m - 65536, m)
    return ((prod - m * KYBER_Q) >> 16).astype(np.int64)

def compute_hw32(arr: np.ndarray) -> np.ndarray:
    """Vectorized 32-bit Hamming Weight."""
    u32 = arr.astype(np.uint32)
    hw = np.zeros_like(u32, dtype=np.float64)
    for bit in range(32):
        hw += ((u32 >> bit) & 1).astype(np.float64)
    return hw

def run_cpa_attack(dataset_root: str, output_dir: str, num_trials: int = 100, trace_counts = None, save_results: bool = True):
    if trace_counts is None:
        trace_counts = [10, 15, 20, 25, 30, 35, 40, 50, 60, 80, 100]
        
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    print("=" * 80)
    print("  PHASE E: TEXTBOOK CPA ATTACK REPRODUCTION ON UNMASKED PQM4")
    print("=" * 80)
    
    ds = MLKEMDataset(dataset_root=dataset_root, implementation="pqm4", scenario="fixed")
    if not ds.is_available():
        print("\n" + "!" * 80)
        print("  [!] DATASET MISSING: 12.57 GB Real-Hardware EM Dataset not found!")
        print(f"      Target directory: {dataset_root}")
        print("      Because the raw EM traces from Magazin & Abdellatif (ePrint 2026/1851)")
        print("      total 12.57 GB, they are intentionally excluded from the 14 MB zip/git archive.")
        print("      To download and unpack the verified dataset (SHA-256: 4eed0b61...):")
        print("          python download_dataset.py")
        print("!" * 80 + "\n")
        raise FileNotFoundError(
            f"pqm4 fixed-key dataset not found at {dataset_root}. Run 'python download_dataset.py' to download the 12.57 GB real-hardware traces."
        )
    
    c0 = ds.list_available_chunks()[0]
    traces = ds.load_traces(c0)
    meta = ds.load_metadata(c0)
    
    a_gt = meta["ap"][0]
    true_a0 = int(a_gt[0])
    true_a1 = int(a_gt[1])
    print(f"[*] Target Secret Coefficients (Ground Truth): a0 = {true_a0}, a1 = {true_a1}")
    print(f"[*] Operation: accum = {true_a0}*b0 + mont_red({true_a1}*2226)*b1")
    print(f"[*] Physical POI: Sample {TARGET_SAMPLE} (Peak EM accumulator switching)")
    
    b0_full = meta["bp"][:, 0].astype(np.int64)
    b1_full = meta["bp"][:, 1].astype(np.int64)
    T_full = traces[:, TARGET_SAMPLE].astype(np.float64)
    
    # Candidate space: We test the correct pair against a pool of 100 candidate pairs
    rng = np.random.RandomState(42)
    num_candidates = 100
    cand_a0 = np.array([true_a0] + list(rng.randint(0, KYBER_Q, size=num_candidates - 1)), dtype=np.int64)
    cand_a1 = np.array([true_a1] + list(rng.randint(0, KYBER_Q, size=num_candidates - 1)), dtype=np.int64)
    cand_a1_tilde = montgomery_reduce(cand_a1 * ZETA0)
    
    print(f"[*] Testing candidate space: {num_candidates} candidate pairs across {len(trace_counts)} trace counts.")
    print(f"[*] Performing {num_trials} independent Monte Carlo repetitions per trace count for confidence intervals...\n")
    
    results_by_N = {}
    
    for N in trace_counts:
        ranks = []
        corrs_true = []
        corrs_max_wrong = []
        
        for trial in range(num_trials):
            # Select random independent subset of traces
            trial_rng = np.random.RandomState(1000 * N + trial)
            trace_indices = trial_rng.choice(len(T_full), size=N, replace=False)
            
            T = T_full[trace_indices]
            T_c = T - np.mean(T)
            den_T = np.sqrt(np.sum(T_c**2)) + 1e-12
            
            b0 = b0_full[trace_indices]
            b1 = b1_full[trace_indices]
            
            # Hypothetical intermediate values: (num_candidates, N)
            acc = cand_a0[:, None] * b0[None, :] + cand_a1_tilde[:, None] * b1[None, :]
            hw = compute_hw32(acc)
            
            hw_c = hw - np.mean(hw, axis=1, keepdims=True)
            den_hw = np.sqrt(np.sum(hw_c**2, axis=1)) + 1e-12
            
            # Pearson correlation
            r = np.abs(np.sum(hw_c * T_c[None, :], axis=1) / (den_hw * den_T))
            
            r_true = r[0]
            r_wrong = r[1:]
            rank = int(np.sum(r_wrong >= r_true))
            
            ranks.append(rank)
            corrs_true.append(r_true)
            corrs_max_wrong.append(np.max(r_wrong))
            
        mean_rank = np.mean(ranks)
        ci_rank = 1.96 * np.std(ranks) / np.sqrt(num_trials) if num_trials > 1 else 0.0
        success_rate = np.mean(np.array(ranks) == 0) * 100.0
        mean_r_true = np.mean(corrs_true)
        mean_r_wrong = np.mean(corrs_max_wrong)
        
        results_by_N[N] = {
            "mean_rank": mean_rank,
            "ci_rank": ci_rank,
            "success_rate": success_rate,
            "r_true": mean_r_true,
            "r_wrong": mean_r_wrong,
            "ranks": ranks
        }
        
        print(f"  N = {N:2d} traces | Rank 0 Success: {success_rate:5.1f}% | "
              f"Mean Rank: {mean_rank:4.2f} +/- {ci_rank:4.2f} | "
              f"True Corr: {mean_r_true:.4f} vs Max Wrong: {mean_r_wrong:.4f}")
              
    if save_results:
        # 1. Output results file
        results_txt = os.path.join(output_dir, "pqm4_cpa_results.txt")
        with open(results_txt, "w", encoding="utf-8") as f:
            f.write("# Phase E: Correlation Power Analysis on pqm4 Unmasked Traces\n")
            f.write("# Ground Truth Secret: a0=679, a1=1286 (mult_a_0.npy)\n")
            f.write("# Target POI: Sample 1568 (Accumulator intermediate: a0*b0 + mont_red(a1*zeta0)*b1)\n")
            f.write(f"# Trials per N: {num_trials}\n")
            f.write(f"{'N_traces':<10} {'Rank0_Rate(%)':<15} {'Mean_Rank':<12} {'CI_Rank_95':<12} {'Corr_True':<12} {'Corr_MaxWrong':<14}\n")
            for N in trace_counts:
                d = results_by_N[N]
                f.write(f"{N:<10d} {d['success_rate']:<15.1f} {d['mean_rank']:<12.2f} {d['ci_rank']:<12.2f} "
                        f"{d['r_true']:<12.4f} {d['r_wrong']:<14.4f}\n")
        print(f"\n[+] Saved CPA empirical results to: {results_txt}")
        
        # 2. Plotting Publication Figure
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        
        Ns = np.array(trace_counts)
        succ_rates = [results_by_N[N]["success_rate"] for N in Ns]
        mean_ranks = [results_by_N[N]["mean_rank"] for N in Ns]
        ci_ranks = [results_by_N[N]["ci_rank"] for N in Ns]
        corrs_true_plot = [results_by_N[N]["r_true"] for N in Ns]
        corrs_wrong_plot = [results_by_N[N]["r_wrong"] for N in Ns]
        
        # Subplot 1: Rank-0 Success Rate
        ax1.plot(Ns, succ_rates, marker="o", color="#1f77b4", linewidth=2.0, label="Empirical Success Rate (Ours)")
        ax1.axvline(40, color="crimson", linestyle="--", linewidth=1.5, label="Reported Baseline (~40 Traces)")
        ax1.set_xlabel("Number of EM Traces ($N$)", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Rank-0 Recovery Rate (%)", fontsize=11, fontweight="bold")
        ax1.set_title("CPA Recovery Success on Unmasked pqm4", fontsize=12, fontweight="bold")
        ax1.set_ylim(-5, 105)
        ax1.legend(loc="lower right", frameon=True)
        ax1.grid(True, alpha=0.3)
        
        # Subplot 2: Correlation Margin
        ax2.plot(Ns, corrs_true_plot, marker="s", color="#2ca02c", linewidth=2.0, label=r"Correct Key $\hat{a} = a$")
        ax2.plot(Ns, corrs_wrong_plot, marker="x", color="#d62728", linewidth=1.5, linestyle=":", label="Max Incorrect Candidate")
        ax2.axvline(40, color="crimson", linestyle="--", linewidth=1.5, label="Reported Baseline (~40 Traces)")
        ax2.set_xlabel("Number of EM Traces ($N$)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Pearson Correlation ($|r|$)", fontsize=11, fontweight="bold")
        ax2.set_title("Correlation Margin vs. Trace Count", fontsize=12, fontweight="bold")
        ax2.legend(loc="upper right", frameon=True)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(plots_dir, "pqm4_cpa_convergence.png")
        plt.savefig(plot_path, dpi=300)
        plt.close()
        print(f"[+] Saved publication plot: {plot_path}")
    print("=" * 80)
    print("  [+] PHASE E CPA ATTACK REPRODUCTION COMPLETE")
    print("=" * 80)
    return results_by_N

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase E: Textbook CPA Attack Reproduction on pqm4")
    parser.add_argument("--dataset_root", type=str, default="datasets/d0nj0n_mlkem_dataset")
    parser.add_argument("--output_dir", type=str, default="replication/phase7_real_hardware")
    parser.add_argument("--trials", type=int, default=100)
    args = parser.parse_args()
    
    run_cpa_attack(args.dataset_root, args.output_dir, num_trials=args.trials)
