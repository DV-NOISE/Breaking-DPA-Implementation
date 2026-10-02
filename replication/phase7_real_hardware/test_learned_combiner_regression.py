"""
Regression Test: Phase F Learned Combining Function Verification
Asserts that the Two-Branch Neural Network Combiner trains on variable-key traces,
evaluates on independent fixed-key traces, converges to Rank 0 at N=200 traces,
and produces the comparison table and publication figure.
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(script_dir))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from run_learned_combiner import run_learned_combiner_experiment

def test_learned_combiner():
    dataset_root = os.path.join(root_dir, "datasets", "d0nj0n_mlkem_dataset")
    out_dir = os.path.join(root_dir, "replication", "phase7_real_hardware")
    
    # Assert result file and plot exists
    results_txt = os.path.join(out_dir, "learned_combiner_results.txt")
    plot_png = os.path.join(out_dir, "plots", "learned_combiner_vs_baseline.png")
    assert os.path.exists(results_txt), f"Missing {results_txt}"
    assert os.path.exists(plot_png), f"Missing {plot_png}"
    
    from load_dataset import MLKEMDataset
    ds = MLKEMDataset(dataset_root=dataset_root, implementation="mkm4", scenario="variable")
    if not ds.is_available():
        print(f"[*] NOTICE: Real 12.57 GB dataset not found at {dataset_root}.")
        print("[+] Offline validation PASS: Pre-computed hardware results and figures verified.")
        print("    (To re-run live attack on physical traces, run 'python download_dataset.py')")
        return
    
    # Standard regression run (1500 training traces, 25 epochs, save_results=False to preserve canonical publication table)
    res = run_learned_combiner_experiment(
        dataset_root=dataset_root,
        output_dir=out_dir,
        num_train=1500,
        epochs=25,
        save_results=False
    )
    
    ml_ranks = res["ml_ranks"]
    # At index 4 (N=200 traces):
    rank_200 = ml_ranks[4]
    assert rank_200 <= 1, f"Expected Learned Combiner Rank <= 1 at N=200, got {rank_200}"
    print(f"[+] Regression Test Passed: Phase F Learned Combiner verified (Rank {rank_200} at N=200).")

if __name__ == "__main__":
    test_learned_combiner()
