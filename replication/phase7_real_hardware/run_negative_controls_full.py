"""
Phase D / Section 5.2.1: Formal Negative Controls for 2nd-Order Masked CPA Scorer
Evaluates two independent null-hypothesis controls across K independent trials at N traces:
  1. Permuted Pairing: Shuffled trace-to-model pairing at the active target window (samples 290..310)
  2. Validated Quiet Off-Target Window: TVLA-verified leak-free window (samples 900..920)

Computes formal goodness-of-fit statistics:
  - Mean Rank & Median Rank (Uniform expectation: (q-1)/2 = 1664.00, q/2 = 1664.50)
  - Rank-0 false-positive count (Expected: 0)
  - Top-100 occurrences (Expected: K * 100 / 3329)
  - Two-sided Kolmogorov-Smirnov test against Uniform(0, 3328)
  - Exact two-sided Binomial test on top-100 count
"""

import os
import sys
import argparse
import numpy as np
from scipy import stats

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from load_dataset import MLKEMDataset, KYBER_Q
from run_mkm4_2nd_order_cpa import precompute_covariance_model

def run_negative_controls(
    dataset_root: str,
    output_dir: str,
    num_trials: int = 100,
    trace_count: int = 500,
    pool_size: int = 2000,
    target_start: int = 290,
    target_end: int = 310,
    quiet_start: int = 900,
    quiet_end: int = 920,
    seed_c1: int = 88880,
    seed_c2: int = 99990,
    save_results: bool = True
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("  PHASE D / SECTION 5.2.1: FORMAL NEGATIVE CONTROLS AUDIT")
    print("=" * 80)
    print(f"[*] Dataset Root: {dataset_root}")
    print(f"[*] Configuration: K={num_trials} trials, N={trace_count} traces/trial, Pool={pool_size} traces")
    print(f"[*] Control 1 Window (Active POI): Samples {target_start}..{target_end}")
    print(f"[*] Control 2 Window (Quiet POI):  Samples {quiet_start}..{quiet_end}")
    
    ds = MLKEMDataset(dataset_root=dataset_root, implementation="mkm4", scenario="fixed")
    if not ds.is_available():
        raise FileNotFoundError(f"mkm4 fixed-key dataset not found at {dataset_root}.")
        
    chunk0 = ds.list_available_chunks()[0]
    t0_traces, t1_traces = ds.load_traces(chunk0)
    meta = ds.load_metadata(chunk0)
    
    coeff_idx = 1
    bp0 = meta["bp_s0"][:, coeff_idx].astype(np.int64)
    bp1 = meta["bp_s1"][:, coeff_idx].astype(np.int64)
    true_b = int((bp0[0] + bp1[0]) % KYBER_Q)
    a_public = meta["ap"][:, coeff_idx].astype(np.int64)
    
    N_pool = min(pool_size, len(t0_traces))
    print(f"[*] Loaded N={N_pool} physical EM traces. True Secret b[{coeff_idx}] = {true_b}")
    print(f"[*] Precomputing mask-averaged circular covariance model for {N_pool} traces...")
    model_pool = precompute_covariance_model(a_public[:N_pool])
    print(f"[+] Covariance model computed: shape {model_pool.shape}")
    
    # --------------------------------------------------------------------------
    # Control 1: Permuted Pairing at Active Window
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print(f"  CONTROL 1: PERMUTED PAIRING AT ACTIVE WINDOW (Samples {target_start}..{target_end})")
    print("-" * 80)
    T0 = t0_traces[:N_pool, target_start:target_end].astype(np.float64)
    T1 = t1_traces[:N_pool, target_start:target_end].astype(np.float64)
    T0_c = T0 - np.mean(T0, axis=0, keepdims=True)
    T1_c = T1 - np.mean(T1, axis=0, keepdims=True)
    P_raw = T0_c * T1_c
    P_smooth = (P_raw[:, :-2] + P_raw[:, 1:-1] + P_raw[:, 2:]) / 3.0
    
    ranks_c1 = []
    r_trues_c1 = []
    r_wrongs_c1 = []
    
    for trial in range(num_trials):
        rng = np.random.RandomState(seed_c1 + trial)
        idx_traces = rng.choice(N_pool, size=trace_count, replace=False)
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
        ranks_c1.append(rank)
        r_trues_c1.append(float(max_r[true_b]))
        r_wrongs_c1.append(float(np.max(np.delete(max_r, true_b))))
        
    ranks_c1 = np.array(ranks_c1)
    m1 = float(np.mean(ranks_c1))
    med1 = float(np.median(ranks_c1))
    r0_1 = int(np.sum(ranks_c1 == 0))
    r100_1 = int(np.sum(ranks_c1 < 100))
    ks1_disc = stats.kstest(ranks_c1, lambda x: (np.floor(x) + 1.0) / KYBER_Q)
    ks1_cont = stats.kstest(ranks_c1, stats.uniform(0, KYBER_Q - 1).cdf)
    binom1 = stats.binomtest(r100_1, n=num_trials, p=100.0 / KYBER_Q)
    
    print(f"[+] Mean Rank: {m1:.2f} (Theoretical Discrete Uniform: {(KYBER_Q - 1)/2:.2f})")
    print(f"[+] Median Rank: {med1:.2f}")
    print(f"[+] Rank 0 Count: {r0_1} / {num_trials} ({r0_1 / num_trials * 100:.1f}%)")
    print(f"[+] Rank < 100 Count: {r100_1} / {num_trials} ({r100_1 / num_trials * 100:.1f}%, Expected: {num_trials * 100 / KYBER_Q:.2f})")
    print(f"[+] Kolmogorov-Smirnov Test (Continuous): D = {ks1_cont.statistic:.4f}, p = {ks1_cont.pvalue:.4f}")
    print(f"[+] Kolmogorov-Smirnov Test (Discrete):   D = {ks1_disc.statistic:.4f}, p = {ks1_disc.pvalue:.4f}")
    print(f"[+] Exact Binomial Test (Rank < 100):     p = {binom1.pvalue:.4f}")
    print(f"[+] Mean r_true: {np.mean(r_trues_c1):.4f} vs Mean max r_wrong: {np.mean(r_wrongs_c1):.4f}")
    
    # --------------------------------------------------------------------------
    # Control 2: Validated Quiet Window (Samples 900..920)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print(f"  CONTROL 2: VALIDATED QUIET OFF-TARGET WINDOW (Samples {quiet_start}..{quiet_end})")
    print("-" * 80)
    T0_q = t0_traces[:N_pool, quiet_start:quiet_end].astype(np.float64)
    T1_q = t1_traces[:N_pool, quiet_start:quiet_end].astype(np.float64)
    T0_qc = T0_q - np.mean(T0_q, axis=0, keepdims=True)
    T1_qc = T1_q - np.mean(T1_q, axis=0, keepdims=True)
    P_qraw = T0_qc * T1_qc
    P_qsmooth = (P_qraw[:, :-2] + P_qraw[:, 1:-1] + P_qraw[:, 2:]) / 3.0
    
    ranks_c2 = []
    r_trues_c2 = []
    r_wrongs_c2 = []
    
    for trial in range(num_trials):
        rng = np.random.RandomState(seed_c2 + trial)
        idx_traces = rng.choice(N_pool, size=trace_count, replace=False)
        
        # Valid pairing with true public key, but evaluating on leak-free window
        M_sub = model_pool[:, idx_traces]
        M_c = M_sub - np.mean(M_sub, axis=1, keepdims=True)
        den_M = np.sqrt(np.sum(M_c**2, axis=1)) + 1e-12
        
        P_sub = P_qsmooth[idx_traces]
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
        ranks_c2.append(rank)
        r_trues_c2.append(float(max_r[true_b]))
        r_wrongs_c2.append(float(np.max(np.delete(max_r, true_b))))
        
    ranks_c2 = np.array(ranks_c2)
    m2 = float(np.mean(ranks_c2))
    med2 = float(np.median(ranks_c2))
    r0_2 = int(np.sum(ranks_c2 == 0))
    r100_2 = int(np.sum(ranks_c2 < 100))
    ks2_cont = stats.kstest(ranks_c2, stats.uniform(0, KYBER_Q - 1).cdf)
    ks2_disc = stats.kstest(ranks_c2, lambda x: (np.floor(x) + 1.0) / KYBER_Q)
    binom2 = stats.binomtest(r100_2, n=num_trials, p=100.0 / KYBER_Q)
    
    print(f"[+] Mean Rank: {m2:.2f} (Theoretical Discrete Uniform: {(KYBER_Q - 1)/2:.2f})")
    print(f"[+] Median Rank: {med2:.2f}")
    print(f"[+] Rank 0 Count: {r0_2} / {num_trials} ({r0_2 / num_trials * 100:.1f}%)")
    print(f"[+] Rank < 100 Count: {r100_2} / {num_trials} ({r100_2 / num_trials * 100:.1f}%, Expected: {num_trials * 100 / KYBER_Q:.2f})")
    print(f"[+] Kolmogorov-Smirnov Test (Continuous): D = {ks2_cont.statistic:.4f}, p = {ks2_cont.pvalue:.4f}")
    print(f"[+] Kolmogorov-Smirnov Test (Discrete):   D = {ks2_disc.statistic:.4f}, p = {ks2_disc.pvalue:.4f}")
    print(f"[+] Exact Binomial Test (Rank < 100):     p = {binom2.pvalue:.4f}")
    print(f"[+] Mean r_true: {np.mean(r_trues_c2):.4f} vs Mean max r_wrong: {np.mean(r_wrongs_c2):.4f}")
    print("=" * 80 + "\n")
    
    results = {
        "control1": {
            "mean_rank": m1, "median_rank": med1, "rank0_count": r0_1, "rank100_count": r100_1,
            "ks_cont_d": float(ks1_cont.statistic), "ks_cont_p": float(ks1_cont.pvalue),
            "ks_disc_d": float(ks1_disc.statistic), "ks_disc_p": float(ks1_disc.pvalue),
            "binom_p": float(binom1.pvalue),
            "mean_r_true": float(np.mean(r_trues_c1)), "mean_r_wrong": float(np.mean(r_wrongs_c1))
        },
        "control2": {
            "mean_rank": m2, "median_rank": med2, "rank0_count": r0_2, "rank100_count": r100_2,
            "ks_cont_d": float(ks2_cont.statistic), "ks_cont_p": float(ks2_cont.pvalue),
            "ks_disc_d": float(ks2_disc.statistic), "ks_disc_p": float(ks2_disc.pvalue),
            "binom_p": float(binom2.pvalue),
            "mean_r_true": float(np.mean(r_trues_c2)), "mean_r_wrong": float(np.mean(r_wrongs_c2))
        }
    }
    
    if save_results:
        results_file = os.path.join(output_dir, "negative_control_results.txt")
        with open(results_file, "w", encoding="utf-8") as f:
            f.write("# Phase D: Formal Negative Controls for Second-Order Masked CPA Scorer\n")
            f.write(f"# Target Implementation: mkm4 (STM32F407, Magazin & Abdellatif ePrint 2026/1851)\n")
            f.write(f"# Number of Trials: K = {num_trials}, Traces per Trial: N = {trace_count}\n")
            f.write(f"# Candidate Space: q = {KYBER_Q} in Z_q, Theoretical Uniform Mean: {(KYBER_Q - 1)/2:.2f}\n\n")
            
            f.write("CONTROL 1: Permuted Pairing (Trace i <-> Model pi(i)) at Active Window (Samples 290..310)\n")
            f.write(f"Mean_Rank:        {m1:.2f}\n")
            f.write(f"Median_Rank:      {med1:.2f}\n")
            f.write(f"Rank0_Count:      {r0_1} / {num_trials} ({r0_1 / num_trials * 100:.1f}%)\n")
            f.write(f"Rank100_Count:    {r100_1} / {num_trials} ({r100_1 / num_trials * 100:.1f}%)\n")
            f.write(f"KS_Test_Cont_D:   {ks1_cont.statistic:.4f}\n")
            f.write(f"KS_Test_Cont_P:   {ks1_cont.pvalue:.4f}\n")
            f.write(f"KS_Test_Disc_D:   {ks1_disc.statistic:.4f}\n")
            f.write(f"KS_Test_Disc_P:   {ks1_disc.pvalue:.4f}\n")
            f.write(f"Binomial_Test_P:  {binom1.pvalue:.4f}\n")
            f.write(f"Mean_r_true:      {np.mean(r_trues_c1):.4f}\n")
            f.write(f"Mean_max_r_wrong: {np.mean(r_wrongs_c1):.4f}\n\n")
            
            f.write("CONTROL 2: Validated Quiet Off-Target Window (Samples 900..920)\n")
            f.write(f"Mean_Rank:        {m2:.2f}\n")
            f.write(f"Median_Rank:      {med2:.2f}\n")
            f.write(f"Rank0_Count:      {r0_2} / {num_trials} ({r0_2 / num_trials * 100:.1f}%)\n")
            f.write(f"Rank100_Count:    {r100_2} / {num_trials} ({r100_2 / num_trials * 100:.1f}%)\n")
            f.write(f"KS_Test_Cont_D:   {ks2_cont.statistic:.4f}\n")
            f.write(f"KS_Test_Cont_P:   {ks2_cont.pvalue:.4f}\n")
            f.write(f"KS_Test_Disc_D:   {ks2_disc.statistic:.4f}\n")
            f.write(f"KS_Test_Disc_P:   {ks2_disc.pvalue:.4f}\n")
            f.write(f"Binomial_Test_P:  {binom2.pvalue:.4f}\n")
            f.write(f"Mean_r_true:      {np.mean(r_trues_c2):.4f}\n")
            f.write(f"Mean_max_r_wrong: {np.mean(r_wrongs_c2):.4f}\n")
            
        print(f"[+] Saved negative control empirical results to: {results_file}")
        
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run formal negative controls for 2nd-order masked CPA")
    parser.add_argument("--dataset_root", type=str, default=os.path.join(script_dir, "..", "..", "datasets", "d0nj0n_mlkem_dataset"))
    parser.add_argument("--output_dir", type=str, default=script_dir)
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--traces", type=int, default=500)
    parser.add_argument("--pool", type=int, default=2000)
    args = parser.parse_args()
    
    run_negative_controls(
        dataset_root=args.dataset_root,
        output_dir=args.output_dir,
        num_trials=args.trials,
        trace_count=args.traces,
        pool_size=args.pool
    )
