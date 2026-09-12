#!/usr/bin/env python3
"""
Master Test Runner for Kyber DPA Replication & ML Extension
Runs an automated end-to-end diagnostic across all 5 phases and generated figures.
"""

import os
import sys
import time
import subprocess

TEST_STEPS = [
    {
        "phase": "Phase 1",
        "name": "Sim Engine Regression Assertions",
        "script": "replication/phase1_noiseless/test_sim_regression.py",
        "description": "Asserts exact Figure 5 ground-truth constants for q_single (0.869559) and q2_single (0.997523)"
    },
    {
        "phase": "Phase 1",
        "name": "Checkpoints Verification (Instr 1 & 2)",
        "script": "replication/phase1_noiseless/verify_checkpoints.py",
        "description": "Verifies noiseless HW collision distributions against author ground-truth CSVs"
    },
    {
        "phase": "Phase 1",
        "name": "Figure 5 Collision Generator (Upper & Lower)",
        "script": "replication/phase1_noiseless/run_figure5.py",
        "description": "Computes multiplicity collision frequencies across all 128 NTT roots for q and q^2 templates"
    },
    {
        "phase": "Phase 2",
        "name": "Table 1 Reference Parsing & Recovery P(l<=5)",
        "script": "replication/phase2_noisy/run_table1.py",
        "description": "Parses author reference datasets and computes closed-form key recovery formula across sigma"
    },
    {
        "phase": "Phase 3",
        "name": "Hardware Trace Emulator (.TRS)",
        "script": "replication/phase3_hw_emulator/generate_synthetic_trs.py",
        "description": "Generates 15-trace averaged synthetic .TRS trace modeling Cortex-M4 pipelining"
    },
    {
        "phase": "Phase 4",
        "name": "Correlation Attack Self-Consistency Check",
        "script": "replication/phase4_attack/run_attack.py",
        "description": "Executes Pearson correlation template attack on 25-candidate centered subspace (sigma=0.012)"
    },
    {
        "phase": "Phase 4",
        "name": "Secret Key Inspection Utility",
        "script": "replication/phase4_attack/view_key.py",
        "description": "Validates centered format {-2,-1,0,1,2} secret key against ground truth"
    },
    {
        "phase": "Phase 5",
        "name": "ML Profiling Model Benchmark",
        "script": "replication/phase5_improvements/ml_attack_model.py",
        "description": "Evaluates Neural Network Profiler vs Pearson baseline on 5-class toy setup (N=10/class)"
    },
    {
        "phase": "Visuals",
        "name": "Replicate Figures 1, 3 & Table 2",
        "script": "replication/reproduce_hardware_figures.py",
        "description": "Generates oscilloscope EM characterization and running average success rate"
    },
    {
        "phase": "Visuals",
        "name": "Extract PDF Graphics & Plot Fig 2, 4",
        "script": "replication/extract_paper_figures.py",
        "description": "Extracts vector PDF figures and plots pipeline inertia and OTA distributions"
    }
]

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    
    print("=" * 80)
    print("      KYBER DPA REPLICATION & ML EXTENSION: MASTER AUTOMATED TEST SUITE")
    print("=" * 80)
    print(f"[*] Workspace Root: {root_dir}")
    print(f"[*] Python Runtime: {sys.executable} (v{sys.version.split()[0]})")
    print(f"[*] Total Test Steps: {len(TEST_STEPS)}")
    print("=" * 80 + "\n")
    
    results = []
    total_start_time = time.time()
    
    for idx, test in enumerate(TEST_STEPS, 1):
        script_path = os.path.join(root_dir, test["script"])
        print(f"[{idx}/{len(TEST_STEPS)}] Running {test['phase']}: {test['name']}...")
        print(f"    Description: {test['description']}")
        
        start_t = time.time()
        try:
            res = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                cwd=root_dir,
                timeout=60
            )
            elapsed = time.time() - start_t
            
            if res.returncode == 0:
                print(f"    [+] Status: PASS ({elapsed:.2f}s)")
                results.append((test["phase"], test["name"], "PASS", elapsed, ""))
            else:
                print(f"    [!] Status: FAIL (Exit Code {res.returncode}) ({elapsed:.2f}s)")
                err_snippet = res.stderr.strip()[:200] if res.stderr else res.stdout.strip()[:200]
                results.append((test["phase"], test["name"], "FAIL", elapsed, err_snippet))
        except Exception as e:
            elapsed = time.time() - start_t
            print(f"    [!] Status: ERROR ({str(e)})")
            results.append((test["phase"], test["name"], "ERROR", elapsed, str(e)))
        print("-" * 80)
        
    total_duration = time.time() - total_start_time
    
    print("\n" + "=" * 80)
    print("                             TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Phase':<10} {'Test Name':<38} {'Status':<10} {'Runtime':<10}")
    print("-" * 80)
    
    all_passed = True
    for phase, name, status, elapsed, err in results:
        status_str = f"[+] {status}" if status == "PASS" else f"[!] {status}"
        print(f"{phase:<10} {name:<38} {status_str:<10} {elapsed:<8.2f}s")
        if status != "PASS":
            all_passed = False
            print(f"    -> Detail: {err}")
            
    print("=" * 80)
    print(f"Total Execution Time: {total_duration:.2f}s")
    
    if all_passed:
        print("\n[+] ALL TESTS PASSED SUCCESSFULLY! The repository is 100% verified.")
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED. Please review the error log above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
