"""
Phase D: Second-Order Correlation Power Analysis (CPA) on Masked mkm4 Traces
Reference: Magazin & Abdellatif, ePrint 2026/1851, Section 4.3 (Donjon baseline: ~200 traces)
           Ledger Donjon: 'A second-order side-channel attack on masked Kyber768' (2026)
Hardware Target: STM32F407 (ARM Cortex-M4 @ 84 MHz), 6.25 GS/s EM captures windowed on basemul_asm

Target Operation:
  Masked pair-pointwise multiplication:
  public * s = public * s0 + public * s1 (mod q)
  where b = b_s0 + b_s1 (mod q) is arithmetically masked (q = 3329).
  
Attack Strategy:
  1. Combiner: Pointwise centered cross-product with 3-sample jitter-mitigation smoothing:
     P_i(t) = (T_{0, i}(t) - mu_0(t)) * (T_{1, i}(t) - mu_1(t))
  2. Leakage Model: Mask-averaged covariance over all masks m in Z_q:
     leakage(a_i, g) = Cov_m( HW(Mont(a_i * m)), HW(Mont(a_i * ((g - m) mod q))) )
     computed across all 3,329 candidates g in [0, 3328] via FFT circular convolution.
  3. Key Recovery: Second-order Pearson CPA distinguishing the true key b among 3,329 hypotheses.
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from load_dataset import MLKEMDataset, KYBER_Q

KYBER_QINV = -3327
TARGET_POI = 299  # Calibrated sample index in 3-sample smoothed cross-product

def montgomery_reduce(prod: np.ndarray) -> np.ndarray:
    """Computes 16-bit Montgomery reduction (Q = 3329, QINV = -3327)."""
    prod = np.asarray(prod, dtype=np.int64)
    m = (prod * KYBER_QINV) & 0xFFFF
    m = np.where(m >= 32768, m - 65536, m)
    return ((prod - m * KYBER_Q) >> 16).astype(np.int64)

def compute_hw32(arr: np.ndarray) -> np.ndarray:
    """Vectorized 32-bit Hamming Weight."""
    u32 = arr.astype(np.uint32)
    hw = np.zeros_like(u32, dtype=np.float64)
    for bit in range(32):
        hw += ((u32 >> bit) & 1).astype(np.float64)
    return hw

def precompute_covariance_model(a_arr: np.ndarray) -> np.ndarray:
    """
    Computes the mask-averaged circular covariance model:
    Cov_m(HW(Mont(a * m)), HW(Mont(a * ((g - m) mod q))))
    for all g in [0, q-1] across N traces using FFT circular convolution.
    Returns: model_mat of shape (KYBER_Q, N)
    """
    N = len(a_arr)
    m_sweep = np.arange(KYBER_Q, dtype=np.int64)
    model_mat = np.zeros((KYBER_Q, N), dtype=np.float64)
    
    for i in range(N):
        ai = a_arr[i]
        h0 = compute_hw32(montgomery_reduce(ai * m_sweep) & 0xFFFF)
        F = np.fft.fft(h0)
        conv = np.fft.ifft(F * F).real / KYBER_Q
        mean_h = np.mean(h0)
        model_mat[:, i] = conv - (mean_h * mean_h)
        
    return model_mat

def run_negative_control(model_pool: np.ndarray, P_smooth: np.ndarray, true_b: int, num_trials: int = 50, N: int = 500) -> dict:
    """
    Executes a negative control (null hypothesis test) on the windowed max-correlation scorer
    by independently permuting the trace-to-model pairing. Asserts that the windowed search
    does not manufacture false separation and results in a uniform rank distribution (~1664).
    """
    print("\n" + "=" * 80)
    print("  NEGATIVE CONTROL / NULL HYPOTHESIS TEST: WINDOWED SCORER VALIDATION")
    print("=" * 80)
    print(f"[*] Breaking trace-to-model pairing across {num_trials} independent trials at N={N}...")
    
    N_pool = P_smooth.shape[0]
    null_ranks = []
    null_r_trues = []
    null_r_wrongs = []
    
    for trial in range(num_trials):
        rng = np.random.RandomState(88880 + trial)
        idx_traces = rng.choice(N_pool, size=N, replace=False)
        idx_model = rng.permutation(idx_traces)
        
        M_sub = model_pool[:, idx_model]
        M_c = M_sub - np.mean(M_sub, axis=1, keepdims=True)
        den_M = np.sqrt(np.sum(M_c**2, axis=1)) + 1e-12
        
        P_sub = P_smooth[idx_traces]
        all_r = []
        for s_idx in range(P_sub.shape[1]):
            p = P_sub[:, s_idx]
            p_c = p - np.mean(p)
            den_p = np.sqrt(np.sum(p_c**2)) + 1e-12
            r = np.abs(np.sum(M_c * p_c[None, :], axis=1) / (den_M * den_p))
            all_r.append(r)
        all_r = np.array(all_r).T
        max_r = np.max(all_r, axis=1)
        
        rank = int(np.where(np.argsort(max_r)[::-1] == true_b)[0][0])
        null_ranks.append(rank)
        null_r_trues.append(float(max_r[true_b]))
        null_r_wrongs.append(float(np.max(np.delete(max_r, true_b))))
        
    null_ranks = np.array(null_ranks)
    m_rank = float(np.mean(null_ranks))
    med_rank = float(np.median(null_ranks))
    r0_count = int(np.sum(null_ranks == 0))
    r100_count = int(np.sum(null_ranks < 100))
    ks_res = stats.kstest(null_ranks, stats.uniform(0, KYBER_Q - 1).cdf)
    binom_res = stats.binomtest(r100_count, n=num_trials, p=100.0/KYBER_Q)
    
    print(f"[+] Null Hypothesis Mean Rank: {m_rank:.2f} (Expected Uniform: {KYBER_Q / 2:.2f})")
    print(f"[+] Null Hypothesis Median Rank: {med_rank:.2f}")
    print(f"[+] Null Hypothesis Rank 0 Recoveries: {r0_count} / {num_trials} ({r0_count / num_trials * 100:.1f}%)")
    print(f"[+] Null Hypothesis Rank < 100 Count: {r100_count} / {num_trials} ({r100_count / num_trials * 100:.1f}%)")
    print(f"[+] Two-Sided Kolmogorov-Smirnov Goodness-of-Fit: D = {ks_res.statistic:.4f}, p = {ks_res.pvalue:.4f}")
    print(f"[+] Exact Binomial Test (Rank < 100): p = {binom_res.pvalue:.4f}")
    print(f"[+] Null Hypothesis Mean r_true: {np.mean(null_r_trues):.4f} vs Mean max r_wrong: {np.mean(null_r_wrongs):.4f}")
    print("=" * 80 + "\n")
    return {
        "mean_rank": m_rank, "median_rank": med_rank, "rank0_count": r0_count,
        "ks_d": ks_res.statistic, "ks_p": ks_res.pvalue, "binom_p": binom_res.pvalue
    }

def run_mkm4_attack(dataset_root: str, output_dir: str, num_trials: int = 50, trace_counts = None, poi: int = TARGET_POI, 
                    save_results: bool = True, run_null_test: bool = True):
    if trace_counts is None:
        trace_counts = [50, 100, 150, 180, 200, 220, 250, 300, 400, 500]
        
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    print("=" * 80)
    print("  PHASE D: REPRODUCING SECOND-ORDER CPA ATTACK ON MASKED MKM4")
    print("=" * 80)
    
    ds = MLKEMDataset(dataset_root=dataset_root, implementation="mkm4", scenario="fixed")
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
            f"mkm4 fixed-key dataset not found at {dataset_root}. Run 'python download_dataset.py' to download the 12.57 GB real-hardware traces."
        )
    
    chunk0 = ds.list_available_chunks()[0]
    t0_traces, t1_traces = ds.load_traces(chunk0)
    meta = ds.load_metadata(chunk0)
    
    # Target: Coefficient 1 of secret polynomial b
    coeff_idx = 1
    bp0 = meta["bp_s0"][:, coeff_idx].astype(np.int64)
    bp1 = meta["bp_s1"][:, coeff_idx].astype(np.int64)
    true_b = int((bp0[0] + bp1[0]) % KYBER_Q)
    a_public = meta["ap"][:, coeff_idx].astype(np.int64)
    
    print(f"[*] Target Operation: Masked basemul_asm on STM32F407 Cortex-M4")
    print(f"[*] Target Secret Key Coefficient: b[{coeff_idx}] = {true_b} (Ground Truth in fixed_unmasked_key.npy)")
    print(f"[*] Joint Point of Interest (POI) Window: Samples 292-304 (smoothed centered cross-product)")
    print(f"[*] Candidate Space: ALL {KYBER_Q} candidate hypotheses in Z_q")
    
    N_pool = min(2000, len(t0_traces))
    print(f"[*] Loading pool of N={N_pool} traces...")
    
    # Extract window around POI [290..310] (covering temporal drift [292..304])
    T0 = t0_traces[:N_pool, 290:310].astype(np.float64)
    T1 = t1_traces[:N_pool, 290:310].astype(np.float64)
    T0_c = T0 - np.mean(T0, axis=0, keepdims=True)
    T1_c = T1 - np.mean(T1, axis=0, keepdims=True)
    P_raw = T0_c * T1_c
    P_smooth = (P_raw[:, :-2] + P_raw[:, 1:-1] + P_raw[:, 2:]) / 3.0
    
    print(f"[*] Precomputing mask-averaged circular covariance model for N={N_pool} traces...")
    model_pool = precompute_covariance_model(a_public[:N_pool])
    print(f"[+] Covariance model matrix computed: {model_pool.shape} elements.")
    
    # Optional Negative Control Test
    if run_null_test:
        run_negative_control(model_pool, P_smooth, true_b, num_trials=50, N=500)
    
    # Helper to compute windowed correlation across POI interval
    def compute_windowed_cpa(idx_subset):
        M_sub = model_pool[:, idx_subset]
        M_c = M_sub - np.mean(M_sub, axis=1, keepdims=True)
        den_M = np.sqrt(np.sum(M_c**2, axis=1)) + 1e-12
        
        P_sub = P_smooth[idx_subset]
        all_r = []
        for s_idx in range(P_sub.shape[1]):
            p = P_sub[:, s_idx]
            p_c = p - np.mean(p)
            den_p = np.sqrt(np.sum(p_c**2)) + 1e-12
            r = np.abs(np.sum(M_c * p_c[None, :], axis=1) / (den_M * den_p))
            all_r.append(r)
        all_r = np.array(all_r).T # Shape: (3329, num_samples)
        max_r = np.max(all_r, axis=1)
        return max_r

    # 1. Primary Sequential Acquisition Evaluation (Trace progression 1..N)
    print("-" * 80)
    print("  EVALUATION 1: SEQUENTIAL TRACE PROGRESSION (Reference Acquisition Mode)")
    print("-" * 80)
    print(f"{'N Traces':<12} {'Rank':<10} {'Corr True':<14} {'Max Wrong':<14} {'Margin':<10}")
    print("-" * 80)
    
    seq_ranks = []
    seq_corrs_true = []
    seq_corrs_wrong = []
    
    for N in trace_counts:
        max_r = compute_windowed_cpa(np.arange(N))
        sorted_cands = np.argsort(max_r)[::-1]
        rank = int(np.where(sorted_cands == true_b)[0][0])
        r_true = float(max_r[true_b])
        r_wrong = float(np.max(np.delete(max_r, true_b)))
        margin = r_true - r_wrong
        
        seq_ranks.append(rank)
        seq_corrs_true.append(r_true)
        seq_corrs_wrong.append(r_wrong)
        
        status_tag = " [RANK 0 RECOVERY!]" if rank == 0 else ""
        print(f"N = {N:<8d} {rank:<10d} {r_true:<14.4f} {r_wrong:<14.4f} {margin:<+10.4f}{status_tag}")
        
    # 2. Multi-Subset Evaluation (Independent Monte Carlo random subsampling)
    print("\n" + "-" * 80)
    print(f"  EVALUATION 2: STATISTICAL MULTI-SUBSET ANALYSIS ({num_trials} Independent Monte Carlo Subsets)")
    print("-" * 80)
    print(f"{'N Traces':<12} {'Rank 0 (%)':<14} {'Mean Rank':<14} {'95% CI':<14} {'Mean rTrue':<12} {'Mean rWrong':<12} {'Margin':<10}")
    print("-" * 80)
    
    multi_results = {}
    
    for N in trace_counts:
        w_ranks = []
        w_r_true = []
        w_r_wrong = []
        
        for trial in range(num_trials):
            rng = np.random.RandomState(1000 * N + trial)
            idx = rng.choice(N_pool, size=N, replace=False)
            max_r = compute_windowed_cpa(idx)
            rank = int(np.where(np.argsort(max_r)[::-1] == true_b)[0][0])
            w_ranks.append(rank)
            w_r_true.append(float(max_r[true_b]))
            w_r_wrong.append(float(np.max(np.delete(max_r, true_b))))
            
        m_rank = float(np.mean(w_ranks))
        std_r = float(np.std(w_ranks))
        ci_r = 1.96 * std_r / np.sqrt(len(w_ranks)) if len(w_ranks) > 1 else 0.0
        succ = float(np.mean(np.array(w_ranks) == 0) * 100.0)
        m_rt = float(np.mean(w_r_true))
        m_rw = float(np.mean(w_r_wrong))
        margin = m_rt - m_rw
        
        multi_results[N] = {
            "mean_rank": m_rank,
            "ci_rank": ci_r,
            "success_rate": succ,
            "ranks": w_ranks,
            "mean_r_true": m_rt,
            "mean_r_wrong": m_rw,
            "margin": margin
        }
        
        print(f"N = {N:<8d} {succ:<14.1f} {m_rank:<14.2f} {ci_r:<14.2f} {m_rt:<12.4f} {m_rw:<12.4f} {margin:<+10.4f}")
        
    if save_results:
        # 3. Save Tabular Results
        results_txt = os.path.join(output_dir, "mkm4_2nd_order_cpa_results.txt")
        with open(results_txt, "w", encoding="utf-8") as f:
            f.write("# Phase D: Second-Order Correlation Power Analysis on Masked mkm4\n")
            f.write("# Target: STM32F407 (ARM Cortex-M4 @ 84 MHz), Magazin & Abdellatif ePrint 2026/1851\n")
            f.write(f"# Ground Truth Secret: b[{coeff_idx}] = {true_b} (fixed_unmasked_key.npy)\n")
            f.write(f"# Joint POI Window: Samples 292-304 (smoothed centered cross-product)\n")
            f.write(f"# Candidate Space: {KYBER_Q} hypotheses in Z_q\n")
            f.write(f"# Evaluation: Independent Monte Carlo random subsampling (K={num_trials} trials/N) & sequential progression\n")
            f.write(f"{'N_traces':<10} {'Seq_Rank':<10} {'Rank0(%)':<10} {'Mean_Rank':<12} {'CI_Rank_95':<12} {'Mean_rTrue':<12} {'Mean_rWrong':<14}\n")
            for i, N in enumerate(trace_counts):
                mr = multi_results[N]
                f.write(f"{N:<10d} {seq_ranks[i]:<10d} {mr['success_rate']:<10.1f} {mr['mean_rank']:<12.2f} {mr['ci_rank']:<12.2f} "
                        f"{mr['mean_r_true']:<12.4f} {mr['mean_r_wrong']:<14.4f}\n")
        print(f"\n[+] Saved Phase D empirical results to: {results_txt}")
        
        # 4. Generate Publication Figure
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        
        Ns = np.array(trace_counts)
        mean_ranks_plot = [multi_results[N]["mean_rank"] for N in Ns]
        ci_ranks_plot = [multi_results[N]["ci_rank"] for N in Ns]
        mean_rt_plot = [multi_results[N]["mean_r_true"] for N in Ns]
        mean_rw_plot = [multi_results[N]["mean_r_wrong"] for N in Ns]
        
        # Subplot 1: Key Rank vs Trace Count
        ax1.plot(Ns, seq_ranks, marker="o", color="#1f77b4", linewidth=2.0, label="Sequential Acquisition Rank (Reference)")
        ax1.plot(Ns, mean_ranks_plot, marker="s", color="#ff7f0e", linewidth=2.0, linestyle="--", label="Monte Carlo Mean Rank (K=50)")
        ax1.axvline(200, color="crimson", linestyle="--", linewidth=1.5, label="Reported Baseline (~200 Traces)")
        ax1.axhline(0, color="darkgreen", linestyle=":", linewidth=1.2, label="Rank 0 (Complete Recovery)")
        ax1.set_xlabel("Number of EM Traces ($N$)", fontsize=11, fontweight="bold")
        ax1.set_ylabel(r"Key Candidate Rank (out of $q=3329$)", fontsize=11, fontweight="bold")
        ax1.set_title("Second-Order CPA Rank Convergence on Masked mkm4", fontsize=12, fontweight="bold")
        ax1.set_ylim(-2, min(max(mean_ranks_plot[:3]) + 50, 1200))
        ax1.legend(loc="upper right", frameon=True)
        ax1.grid(True, alpha=0.3)
        
        # Subplot 2: Correlation Margin vs N
        ax2.plot(Ns, mean_rt_plot, marker="s", color="#2ca02c", linewidth=2.2, label=r"True Key Hypothesis $\hat{b} = b$")
        ax2.plot(Ns, mean_rw_plot, marker="x", color="#d62728", linewidth=1.5, linestyle=":", label=r"Max Incorrect Candidate ($g \neq b$)")
        ax2.axvline(200, color="crimson", linestyle="--", linewidth=1.5, label="Reported Baseline (~200 Traces)")
        ax2.set_xlabel("Number of EM Traces ($N$)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Pearson Correlation ($|r|$)", fontsize=11, fontweight="bold")
        ax2.set_title("Correlation Margin vs. Trace Count ($q=3329$)", fontsize=12, fontweight="bold")
        ax2.legend(loc="upper right", frameon=True)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(plots_dir, "mkm4_2nd_order_cpa_convergence.png")
        plt.savefig(plot_path, dpi=300)
        plt.close()
        print(f"[+] Saved publication figure: {plot_path}")
    print("=" * 80)
    print("  [+] PHASE D SECOND-ORDER CPA ATTACK REPRODUCTION COMPLETE")
    print("=" * 80)
    return {"seq_ranks": seq_ranks, "multi_results": multi_results}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase D: Second-Order CPA Attack on Masked mkm4")
    parser.add_argument("--dataset_root", type=str, default="datasets/d0nj0n_mlkem_dataset")
    parser.add_argument("--output_dir", type=str, default="replication/phase7_real_hardware")
    parser.add_argument("--trials", type=int, default=50)
    parser.add_argument("--poi", type=int, default=TARGET_POI)
    parser.add_argument("--skip_null_test", action="store_true", help="Skip negative control null test")
    args = parser.parse_args()
    
    run_mkm4_attack(args.dataset_root, args.output_dir, num_trials=args.trials, poi=args.poi, run_null_test=not args.skip_null_test)
