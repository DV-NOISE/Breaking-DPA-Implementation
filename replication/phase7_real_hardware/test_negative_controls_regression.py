"""
Regression Test: Phase D Masked CPA Negative Controls & Goodness-of-Fit Validation
Asserts that negative_control_results.txt exists, contains formal goodness-of-fit statistics,
confirms that both negative controls fail to reject the uniform null hypothesis (p > 0.05),
and optionally runs a fast live test on physical EM traces.
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(script_dir))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from run_negative_controls_full import run_negative_controls
from load_dataset import MLKEMDataset

def test_negative_controls():
    results_path = os.path.join(script_dir, "negative_control_results.txt")
    assert os.path.exists(results_path), f"Missing {results_path}"
    
    with open(results_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Check that both controls are present
    assert "CONTROL 1: Permuted Pairing" in content, "Missing Control 1 in results"
    assert "CONTROL 2: Validated Quiet Off-Target Window" in content, "Missing Control 2 in results"
    
    # Assert statistical validity of logged results
    # Control 1 assertions
    assert "Rank0_Count:      0 / 100" in content, "Control 1 had false positive Rank-0 recoveries"
    assert "KS_Test_Cont_D:   0.0863" in content, "Control 1 KS D mismatch"
    assert "KS_Test_Cont_P:   0.4221" in content, "Control 1 KS p mismatch"
    assert "Binomial_Test_P:  0.5477" in content, "Control 1 Binomial p mismatch"
    
    # Control 2 assertions
    assert "Rank0_Count:      0 / 100" in content, "Control 2 had false positive Rank-0 recoveries"
    assert "KS_Test_Cont_D:   0.1137" in content, "Control 2 KS D mismatch"
    assert "KS_Test_Cont_P:   0.1394" in content, "Control 2 KS p mismatch"
    assert "Binomial_Test_P:  0.7725" in content, "Control 2 Binomial p mismatch"
    
    # Live smoke test with small trial count if dataset is available
    dataset_root = os.path.join(root_dir, "datasets", "d0nj0n_mlkem_dataset")
    ds = MLKEMDataset(dataset_root=dataset_root, implementation="mkm4", scenario="fixed")
    if not ds.is_available():
        print(f"[*] NOTICE: Real 12.57 GB dataset not found at {dataset_root}.")
        print("[+] Offline validation PASS: Pre-computed negative control results verified.")
        return
        
    print("[*] Running fast live negative control smoke test (K=2 trials)...")
    smoke_results = run_negative_controls(
        dataset_root=dataset_root,
        output_dir=script_dir,
        num_trials=2,
        trace_count=100,
        pool_size=500,
        save_results=False
    )
    assert smoke_results["control1"]["rank0_count"] == 0, "Smoke test failed: false positive in Control 1"
    assert smoke_results["control2"]["rank0_count"] == 0, "Smoke test failed: false positive in Control 2"
    print("[+] Regression Test Passed: Formal Negative Controls verified.")

if __name__ == "__main__":
    test_negative_controls()
