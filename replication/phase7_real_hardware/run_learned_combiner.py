"""
Phase F: Learned Combining Function for Masked Kyber (mkm4)
Reference: MASTER_PLAN.md Section 2 (Phase F)
Target: First-Order Masked Kyber768 (mkm4) on STM32F407 (ARM Cortex-M4 @ 84 MHz)

Novelty & Contribution:
  Instead of assuming the hand-crafted centered cross-product combiner:
    P(t) = (T_0(t) - mu_0) * (T_1(t) - mu_1)
  we train a Two-Branch Neural Network Combiner on the per-share traces of the
  `variable` scenario to learn the non-linear interaction directly from EM measurements.
  
  The trained combiner is then evaluated on the independent `fixed` scenario dataset,
  comparing its rank-0 recovery curve against Phase D's ~200-trace centered-product baseline.
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
from run_mkm4_2nd_order_cpa import montgomery_reduce, compute_hw32, precompute_covariance_model

TARGET_POI = 299  # Sample index for joint POI
WINDOW_HALF_WIDTH = 5 # Window: [POI - 5, POI + 5] (11 samples per share)

def extract_features(traces_s0: np.ndarray, traces_s1: np.ndarray, poi: int = TARGET_POI, hw: int = WINDOW_HALF_WIDTH):
    """Extracts localized feature windows around the joint POI for each share."""
    x0 = traces_s0[:, poi - hw : poi + hw + 1].astype(np.float64)
    x1 = traces_s1[:, poi - hw : poi + hw + 1].astype(np.float64)
    
    # Feature standardization
    x0_norm = (x0 - np.mean(x0, axis=0)) / (np.std(x0, axis=0) + 1e-8)
    x1_norm = (x1 - np.mean(x1, axis=0)) / (np.std(x1, axis=0) + 1e-8)
    return x0_norm, x1_norm

def pearson_loss(y_pred, y_true):
    """Negative Pearson correlation loss for gradient optimization."""
    pred_c = y_pred - np.mean(y_pred)
    true_c = y_true - np.mean(y_true)
    den = (np.sqrt(np.sum(pred_c**2)) * np.sqrt(np.sum(true_c**2))) + 1e-12
    corr = np.sum(pred_c * true_c) / den
    return -corr, corr

class NumpyTwoBranchCombiner:
    """
    Two-Branch Neural Network implemented in pure NumPy with Adam optimizer.
    Branch 0: R^d -> R^16
    Branch 1: R^d -> R^16
    Merge: R^32 -> R^16 -> R^1
    """
    def __init__(self, in_dim=11, hidden_dim=16, seed=42):
        rng = np.random.RandomState(seed)
        # He initialization
        self.W0 = rng.randn(in_dim, hidden_dim) * np.sqrt(2.0 / in_dim)
        self.b0 = np.zeros(hidden_dim)
        self.W1 = rng.randn(in_dim, hidden_dim) * np.sqrt(2.0 / in_dim)
        self.b1 = np.zeros(hidden_dim)
        
        self.Wm = rng.randn(hidden_dim * 2, hidden_dim) * np.sqrt(2.0 / (hidden_dim * 2))
        self.bm = np.zeros(hidden_dim)
        
        self.Wout = rng.randn(hidden_dim, 1) * np.sqrt(2.0 / hidden_dim)
        self.bout = np.zeros(1)
        
        # Adam state
        self.params = [self.W0, self.b0, self.W1, self.b1, self.Wm, self.bm, self.Wout, self.bout]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.t = 0
        
    def forward(self, x0, x1):
        # Branch 0
        self.z0 = x0 @ self.W0 + self.b0
        self.h0 = np.maximum(0, self.z0)  # ReLU
        
        # Branch 1
        self.z1 = x1 @ self.W1 + self.b1
        self.h1 = np.maximum(0, self.z1)  # ReLU
        
        # Merge layer (concat)
        self.concat = np.hstack([self.h0, self.h1])
        self.zm = self.concat @ self.Wm + self.bm
        self.hm = np.maximum(0, self.zm)
        
        # Output layer
        self.out = (self.hm @ self.Wout + self.bout).flatten()
        return self.out
        
    def train_step(self, x0, x1, y_target, lr=0.005):
        self.t += 1
        N = len(y_target)
        
        # Forward pass
        y_pred = self.forward(x0, x1)
        
        # Pearson loss gradient
        pred_c = y_pred - np.mean(y_pred)
        true_c = y_target - np.mean(y_target)
        sum_pred2 = np.sum(pred_c**2) + 1e-12
        sum_true2 = np.sum(true_c**2) + 1e-12
        den = np.sqrt(sum_pred2 * sum_true2)
        corr = np.sum(pred_c * true_c) / den
        
        # d(-corr)/d(y_pred)
        d_pred = -(true_c / den - (corr / sum_pred2) * pred_c) # (N,)
        
        # Backward pass
        # Out layer
        dWout = self.hm.T @ d_pred[:, None]
        dbout = np.sum(d_pred, keepdims=True)
        
        # Merge layer
        dhm = d_pred[:, None] @ self.Wout.T
        dzm = dhm * (self.zm > 0)
        dWm = self.concat.T @ dzm
        dbm = np.sum(dzm, axis=0)
        
        # Split concat
        dconcat = dzm @ self.Wm.T
        H = self.W0.shape[1]
        dh0 = dconcat[:, :H]
        dh1 = dconcat[:, H:]
        
        # Branch 0
        dz0 = dh0 * (self.z0 > 0)
        dW0 = x0.T @ dz0
        db0 = np.sum(dz0, axis=0)
        
        # Branch 1
        dz1 = dh1 * (self.z1 > 0)
        dW1 = x1.T @ dz1
        db1 = np.sum(dz1, axis=0)
        
        grads = [dW0, db0, dW1, db1, dWm, dbm, dWout, dbout]
        
        # Adam update
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        for i in range(len(self.params)):
            self.m[i] = beta1 * self.m[i] + (1 - beta1) * grads[i]
            self.v[i] = beta2 * self.v[i] + (1 - beta2) * (grads[i] ** 2)
            m_hat = self.m[i] / (1 - beta1 ** self.t)
            v_hat = self.v[i] / (1 - beta2 ** self.t)
            self.params[i] -= lr * m_hat / (np.sqrt(v_hat) + eps)
            
        return corr

def run_learned_combiner_experiment(dataset_root: str, output_dir: str, num_train: int = 3000, epochs: int = 30, num_trials: int = 50, save_results: bool = True):
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    print("=" * 80)
    print("  PHASE F: NOVEL LEARNED COMBINING FUNCTION FOR MASKED KYBER (MKM4)")
    print("=" * 80)
    
    # 1. Load Profiling Data from Variable Key Scenario
    print("[*] Loading Profiling Data (Variable Scenario) for training...")
    ds_var = MLKEMDataset(dataset_root=dataset_root, implementation="mkm4", scenario="variable")
    if not ds_var.is_available():
        print("\n" + "!" * 80)
        print("  [!] DATASET MISSING: 12.57 GB Real-Hardware EM Dataset not found!")
        print(f"      Target directory: {dataset_root}")
        print("      Because the raw EM traces from Magazin & Abdellatif (ePrint 2026/1851)")
        print("      total 12.57 GB, they are intentionally excluded from the 14 MB zip/git archive.")
        print("      To download and unpack the verified dataset (SHA-256: 4eed0b61...):")
        print("          python download_dataset.py")
        print("!" * 80 + "\n")
        raise FileNotFoundError(
            f"Variable dataset not found at {dataset_root}. Run 'python download_dataset.py' to download the 12.57 GB real-hardware traces."
        )
    
    c_var = ds_var.list_available_chunks()[0]
    t0_var, t1_var = ds_var.load_traces(c_var)
    meta_var = ds_var.load_metadata(c_var)
    
    # Target: Coefficient 1
    coeff_idx = 1
    a_var = meta_var["ap"][:num_train, coeff_idx].astype(np.int64)
    bp0_var = meta_var["bp_s0"][:num_train, coeff_idx].astype(np.int64)
    bp1_var = meta_var["bp_s1"][:num_train, coeff_idx].astype(np.int64)
    sec_var = (bp0_var + bp1_var) % KYBER_Q
    
    print(f"[*] Training pool: N={num_train} traces from variable key capture.")
    x0_train, x1_train = extract_features(t0_var[:num_train], t1_var[:num_train])
    
    # Target label: Mask-averaged covariance ground truth for the unmasked secret
    print("[*] Precomputing target training labels (true key mask-averaged covariance)...")
    m_sweep = np.arange(KYBER_Q, dtype=np.int64)
    y_target = np.zeros(num_train, dtype=np.float64)
    for i in range(num_train):
        ai = a_var[i]
        si = sec_var[i]
        h0 = compute_hw32(montgomery_reduce(ai * m_sweep) & 0xFFFF)
        F = np.fft.fft(h0)
        conv = np.fft.ifft(F * F).real / KYBER_Q
        mean_h = np.mean(h0)
        y_target[i] = conv[si] - (mean_h * mean_h)
        
    print(f"[+] Training labels generated. Standardizing targets...")
    y_target = (y_target - np.mean(y_target)) / (np.std(y_target) + 1e-8)
    
    # 2. Train Two-Branch Combiner Network
    print(f"[*] Training Two-Branch Neural Network Combiner ({epochs} epochs)...")
    model = NumpyTwoBranchCombiner(in_dim=x0_train.shape[1], hidden_dim=24, seed=42)
    
    for epoch in range(1, epochs + 1):
        corr = model.train_step(x0_train, x1_train, y_target, lr=0.01)
        if epoch % 10 == 0 or epoch == epochs:
            print(f"    Epoch {epoch:2d}/{epochs:2d} | Training Pearson Correlation: {corr:.4f}")
            
    print("[+] Learned combiner training complete.")
    
    # 3. Load Testing Data from Fixed Key Scenario (Independent Evaluation)
    print("\n[*] Loading Attack Data (Fixed Scenario) for evaluation...")
    ds_fix = MLKEMDataset(dataset_root=dataset_root, implementation="mkm4", scenario="fixed")
    assert ds_fix.is_available(), f"Fixed dataset not found at {dataset_root}!"
    
    c_fix = ds_fix.list_available_chunks()[0]
    t0_fix, t1_fix = ds_fix.load_traces(c_fix)
    meta_fix = ds_fix.load_metadata(c_fix)
    
    N_eval = 1000
    bp0_fix = meta_fix["bp_s0"][:, coeff_idx].astype(np.int64)
    bp1_fix = meta_fix["bp_s1"][:, coeff_idx].astype(np.int64)
    true_b = int((bp0_fix[0] + bp1_fix[0]) % KYBER_Q)
    a_fix = meta_fix["ap"][:N_eval, coeff_idx].astype(np.int64)
    
    print(f"[*] Target Secret: b[{coeff_idx}] = {true_b}")
    x0_eval, x1_eval = extract_features(t0_fix[:N_eval], t1_fix[:N_eval])
    
    # Pass fixed traces through Learned Combiner
    print("[*] Generating learned combined leakages via TwoBranchCombiner...")
    L_learned = model.forward(x0_eval, x1_eval)
    
    # Also extract Phase D's baseline smoothed centered cross-product for direct side-by-side comparison
    poi_raw = TARGET_POI + 1
    T0 = t0_fix[:N_eval, poi_raw-2:poi_raw+3].astype(np.float64)
    T1 = t1_fix[:N_eval, poi_raw-2:poi_raw+3].astype(np.float64)
    T0_c = T0 - np.mean(T0, axis=0, keepdims=True)
    T1_c = T1 - np.mean(T1, axis=0, keepdims=True)
    P_raw = T0_c * T1_c
    P_smooth = (P_raw[:, :-2] + P_raw[:, 1:-1] + P_raw[:, 2:]) / 3.0
    L_baseline = P_smooth[:, 1]
    
    # Precompute candidate models for fixed key traces
    print(f"[*] Precomputing candidate models across all {KYBER_Q} hypotheses for N={N_eval} traces...")
    model_pool = precompute_covariance_model(a_fix)
    
    # Direct signal correlation comparison on N_eval fixed traces
    true_model = model_pool[true_b]
    _, c_base_full = pearson_loss(L_baseline, true_model)
    _, c_ml_full = pearson_loss(L_learned, true_model)
    signal_gain = ((abs(c_ml_full) - abs(c_base_full)) / (abs(c_base_full) + 1e-12)) * 100.0
    
    print("\n" + "=" * 80)
    print(f"  DIRECT SIGNAL-TO-HYPOTHESIS CORRELATION EVALUATION (N = {N_eval} Fixed Traces)")
    print("=" * 80)
    print(f"  * Baseline Centered Cross-Product Corr with True Model : {abs(c_base_full):.4f}")
    print(f"  * Learned Two-Branch Combiner Corr with True Model      : {abs(c_ml_full):.4f}")
    print(f"  * Direct Signal Amplification Gain                      : +{signal_gain:.1f}%")
    print("=" * 80)
    
    # 4. Compare Attack Convergence vs. Trace Count
    trace_counts = [50, 100, 150, 180, 200, 220, 250, 300, 400, 500]
    
    # 4a. Sequential Progression (Reference Acquisition Mode)
    print("\n" + "=" * 80)
    print("  EVALUATION 1: SEQUENTIAL TRACE PROGRESSION (Reference Acquisition Mode)")
    print("=" * 80)
    print(f"{'N Traces':<10} {'Baseline Rank (Phase D)':<26} {'Learned Combiner Rank (Phase F)':<32} {'Outcome'}")
    print("-" * 80)
    
    seq_base_ranks = []
    seq_ml_ranks = []
    seq_base_corrs = []
    seq_ml_corrs = []
    
    for N in trace_counts:
        M_sub = model_pool[:, :N]
        M_c = M_sub - np.mean(M_sub, axis=1, keepdims=True)
        den_M = np.sqrt(np.sum(M_c**2, axis=1)) + 1e-12
        
        # Windowed Baseline
        P_sub = P_smooth[:N]
        all_r_base = []
        for s in range(P_sub.shape[1]):
            p = P_sub[:, s]
            p_c = p - np.mean(p)
            den_p = np.sqrt(np.sum(p_c**2)) + 1e-12
            all_r_base.append(np.abs(np.sum(M_c * p_c[None, :], axis=1) / (den_M * den_p)))
        max_r_base = np.max(np.array(all_r_base).T, axis=1)
        rank_base = int(np.where(np.argsort(max_r_base)[::-1] == true_b)[0][0])
        seq_base_ranks.append(rank_base)
        seq_base_corrs.append(float(max_r_base[true_b]))
        
        # Learned Combiner
        p_ml = L_learned[:N]
        p_ml_c = p_ml - np.mean(p_ml)
        den_ml = np.sqrt(np.sum(p_ml_c**2)) + 1e-12
        r_ml = np.abs(np.sum(M_c * p_ml_c[None, :], axis=1) / (den_M * den_ml))
        rank_ml = int(np.where(np.argsort(r_ml)[::-1] == true_b)[0][0])
        seq_ml_ranks.append(rank_ml)
        seq_ml_corrs.append(float(r_ml[true_b]))
        
        outcome = "MATCH" if rank_base == rank_ml else ("ML BETTER" if rank_ml < rank_base else "BASELINE BETTER")
        if rank_ml == 0 and rank_base == 0:
            outcome = "BOTH RANK 0!"
        elif rank_ml == 0:
            outcome = "ML RANK 0 WIN!"
            
        print(f"N = {N:<6d} {rank_base:<26d} {rank_ml:<32d} {outcome}")
        
    # 4b. Independent Monte Carlo Random Subsampling
    print("\n" + "=" * 80)
    print("  EVALUATION 2: 50 INDEPENDENT MONTE CARLO RANDOM SUBSETS PER N")
    print("=" * 80)
    print(f"{'N Traces':<10} {'Base Rank0 (%)':<16} {'Base Mean Rank':<18} {'ML Rank0 (%)':<16} {'ML Mean Rank':<18} {'Advantage'}")
    print("-" * 80)
    
    mc_results = {}
    
    for N in trace_counts:
        r_base_list = []
        r_ml_list = []
        for trial in range(num_trials):
            rng = np.random.RandomState(3000 * N + trial)
            idx = rng.choice(N_eval, size=N, replace=False)
            M_sub = model_pool[:, idx]
            M_c = M_sub - np.mean(M_sub, axis=1, keepdims=True)
            den_M = np.sqrt(np.sum(M_c**2, axis=1)) + 1e-12
            
            # ML Combiner
            p_ml = L_learned[idx]
            p_ml_c = p_ml - np.mean(p_ml)
            den_ml = np.sqrt(np.sum(p_ml_c**2)) + 1e-12
            r_ml = np.abs(np.sum(M_c * p_ml_c[None, :], axis=1) / (den_M * den_ml))
            rank_ml = int(np.where(np.argsort(r_ml)[::-1] == true_b)[0][0])
            r_ml_list.append(rank_ml)
            
            # Windowed Baseline
            P_sub = P_smooth[idx]
            all_r = []
            for s in range(P_sub.shape[1]):
                p = P_sub[:, s]
                p_c = p - np.mean(p)
                den_p = np.sqrt(np.sum(p_c**2)) + 1e-12
                all_r.append(np.abs(np.sum(M_c * p_c[None, :], axis=1) / (den_M * den_p)))
            max_r_base = np.max(np.array(all_r).T, axis=1)
            rank_base = int(np.where(np.argsort(max_r_base)[::-1] == true_b)[0][0])
            r_base_list.append(rank_base)
            
        rb = np.array(r_base_list)
        rm = np.array(r_ml_list)
        
        base_r0 = float(np.mean(rb == 0) * 100.0)
        base_mean = float(np.mean(rb))
        base_ci = float(1.96 * np.std(rb) / np.sqrt(num_trials))
        
        ml_r0 = float(np.mean(rm == 0) * 100.0)
        ml_mean = float(np.mean(rm))
        ml_ci = float(1.96 * np.std(rm) / np.sqrt(num_trials))
        
        advantage = "ML LOWER RANK" if ml_mean < base_mean else ("TIE" if ml_mean == base_mean else "BASELINE LOWER")
        print(f"N = {N:<6d} {base_r0:<16.1f} {base_mean:6.2f} +/- {base_ci:<8.2f} {ml_r0:<16.1f} {ml_mean:6.2f} +/- {ml_ci:<8.2f} {advantage}")
        
        mc_results[N] = {
            "base_r0": base_r0, "base_mean": base_mean, "base_ci": base_ci,
            "ml_r0": ml_r0, "ml_mean": ml_mean, "ml_ci": ml_ci
        }
        
    if save_results:
        # 5. Save Comparison Results
        results_txt = os.path.join(output_dir, "learned_combiner_results.txt")
        with open(results_txt, "w", encoding="utf-8") as f:
            f.write("# Phase F: Learned Combining Function vs Windowed Centered-Product Baseline\n")
            f.write(f"# Target Secret: b[{coeff_idx}] = {true_b} (fixed_unmasked_key.npy)\n")
            f.write(f"# Architecture: Two-Branch Neural Network (Input 11 -> Hidden 24 -> Output 1)\n")
            f.write(f"# Evaluation: 50 Independent Monte Carlo Subsets per N & Sequential Progression\n")
            f.write(f"{'N_traces':<10} {'Seq_Base':<10} {'Seq_ML':<10} {'Base_R0(%)':<12} {'Base_Mean':<12} {'Base_CI':<10} {'ML_R0(%)':<10} {'ML_Mean':<10} {'ML_CI':<10}\n")
            for i, N in enumerate(trace_counts):
                mc = mc_results[N]
                f.write(f"{N:<10d} {seq_base_ranks[i]:<10d} {seq_ml_ranks[i]:<10d} {mc['base_r0']:<12.1f} {mc['base_mean']:<12.2f} {mc['base_ci']:<10.2f} {mc['ml_r0']:<10.1f} {mc['ml_mean']:<10.2f} {mc['ml_ci']:<10.2f}\n")
        print(f"\n[+] Saved Phase F comparison table: {results_txt}")
        
        # 6. Publication Comparison Figure
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        
        Ns = np.array(trace_counts)
        base_means = [mc_results[N]["base_mean"] for N in Ns]
        ml_means = [mc_results[N]["ml_mean"] for N in Ns]
        base_r0s = [mc_results[N]["base_r0"] for N in Ns]
        ml_r0s = [mc_results[N]["ml_r0"] for N in Ns]
        
        # Panel 1: Monte Carlo Mean Rank Comparison
        ax1.plot(Ns, base_means, marker="o", color="#1f77b4", linewidth=2.0, label="Windowed Centered-Product (Phase D)")
        ax1.plot(Ns, ml_means, marker="^", color="#ff7f0e", linewidth=2.0, linestyle="--", label="Learned Two-Branch Combiner (Phase F)")
        ax1.axvline(200, color="crimson", linestyle=":", linewidth=1.5, label="Reported Baseline (~200 Traces)")
        ax1.axhline(0, color="darkgreen", linestyle=":", linewidth=1.2, label="Rank 0 (Full Recovery)")
        ax1.set_xlabel("Number of EM Traces ($N$)", fontsize=11, fontweight="bold")
        ax1.set_ylabel(r"Monte Carlo Mean Rank ($q=3329$)", fontsize=11, fontweight="bold")
        ax1.set_title("Rank Convergence: Hand-Crafted vs. Learned Combiner", fontsize=12, fontweight="bold")
        ax1.set_ylim(-2, max(base_means[:3] + ml_means[:3]) + 50)
        ax1.legend(loc="upper right", frameon=True)
        ax1.grid(True, alpha=0.3)
        
        # Panel 2: Rank-0 Success Rate Comparison
        ax2.plot(Ns, base_r0s, marker="s", color="#1f77b4", linewidth=2.0, label="Windowed Centered-Product")
        ax2.plot(Ns, ml_r0s, marker="d", color="#ff7f0e", linewidth=2.0, linestyle="--", label="Learned Two-Branch Combiner")
        ax2.axvline(200, color="crimson", linestyle=":", linewidth=1.5, label="Reported Baseline (~200 Traces)")
        ax2.set_xlabel("Number of EM Traces ($N$)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Rank-0 Recovery Success Rate (%)", fontsize=11, fontweight="bold")
        ax2.set_title("Rank-0 Recovery Rate: Baseline vs. Learned Combiner", fontsize=12, fontweight="bold")
        ax2.set_ylim(-5, 105)
        ax2.legend(loc="lower right", frameon=True)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(plots_dir, "learned_combiner_vs_baseline.png")
        plt.savefig(plot_path, dpi=300)
        plt.close()
        print(f"[+] Saved publication comparison plot: {plot_path}")
    print("=" * 80)
    print("  [+] PHASE F LEARNED COMBINER EVALUATION COMPLETE")
    print("=" * 80)
    return {"base_ranks": seq_base_ranks, "ml_ranks": seq_ml_ranks, "mc_results": mc_results}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase F: Learned Combiner for Masked Kyber")
    parser.add_argument("--dataset_root", type=str, default="datasets/d0nj0n_mlkem_dataset")
    parser.add_argument("--output_dir", type=str, default="replication/phase7_real_hardware")
    parser.add_argument("--train_traces", type=int, default=3000)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--trials", type=int, default=50)
    args = parser.parse_args()
    
    run_learned_combiner_experiment(args.dataset_root, args.output_dir, num_train=args.train_traces, epochs=args.epochs, num_trials=args.trials)
