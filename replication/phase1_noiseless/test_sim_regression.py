import subprocess
import re
import os
import sys

def test_regression():
    print("=" * 70)
    print("  AUTOMATED REGRESSION TEST: SIM_ENGINE GROUND TRUTH CONSTANTS")
    print("=" * 70)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sim_exe = os.path.join(script_dir, "sim_engine.exe")
    if not os.path.exists(sim_exe):
        sim_exe = "replication/phase1_noiseless/sim_engine.exe"
        
    assert os.path.exists(sim_exe), f"sim_engine.exe not found at {sim_exe}"
    
    # 1. Assert q_single(2226) == 0.869559 (Figure 5 Upper Table, zeta0=2226)
    print("[*] Running q_single 2226...")
    res_q = subprocess.run([sim_exe, "q_single", "2226"], capture_output=True, text=True, check=True)
    match_q1 = re.search(r"1-way:\s*([0-9\.]+)", res_q.stdout)
    assert match_q1, "Failed to parse 1-way probability from q_single output"
    val_q1 = float(match_q1.group(1))
    target_q1 = 0.869559
    assert abs(val_q1 - target_q1) < 1e-4, f"Regression failure! q_single(2226)={val_q1}, expected {target_q1}"
    print(f"[+] PASS: q_single(2226) 1-way = {val_q1:.6f} matches ground truth {target_q1} (Paper Figure 5: 0.8696)")

    # 2. Assert q2_single(2226) == 0.997523 (Figure 5 Lower Table, zeta0=2226)
    print("[*] Running q2_single 2226...")
    res_q2 = subprocess.run([sim_exe, "q2_single", "2226"], capture_output=True, text=True, check=True)
    match_q2 = re.search(r"1-way:\s*([0-9\.]+)", res_q2.stdout)
    assert match_q2, "Failed to parse 1-way probability from q2_single output"
    val_q2 = float(match_q2.group(1))
    target_q2 = 0.997523
    assert abs(val_q2 - target_q2) < 1e-4, f"Regression failure! q2_single(2226)={val_q2}, expected {target_q2}"
    print(f"[+] PASS: q2_single(2226) 1-way = {val_q2:.6f} matches ground truth {target_q2} (Paper Figure 5: 0.9974)")

    # 3. Check that the buggy value 0.999346 is NOT present
    assert abs(val_q2 - 0.999346) > 1e-3, "Critical Bug! Inverted halfword packing bug detected (0.999346)!"

    # 4. Assert static source code packing consistency across all simulators
    root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))
    sim_cpp = os.path.join(root_dir, "replication", "phase1_noiseless", "sim_engine.cpp")
    noisy_cpp = os.path.join(root_dir, "replication", "phase2_noisy", "noisy_sim.cpp")
    q2_noisy_cpp = os.path.join(root_dir, "replication", "phase2_noisy", "q2_noisy_sim.cpp")
    blinding_cpp = os.path.join(root_dir, "replication", "phase6_countermeasures", "blinding_evaluation.cpp")

    with open(noisy_cpp, "r", encoding="utf-8") as f:
        noisy_code = f.read()
    m_noisy = re.search(r"compute_template_q2\s*\([^)]*\)\s*\{(.*?)\}", noisy_code, re.DOTALL)
    assert m_noisy, "compute_template_q2 definition not found in noisy_sim.cpp!"
    noisy_q2_body = m_noisy.group(1)
    assert not re.search(r"poly0\s*=.*a1.*<<\s*16.*a0", noisy_q2_body), "Inverted packing bug detected in noisy_sim.cpp!"
    assert re.search(r"poly0\s*=.*a0.*<<\s*16.*a1", noisy_q2_body), "Correct packing (a0<<16)|a1 not found in noisy_sim.cpp!"
    print("[+] PASS: Static verification in noisy_sim.cpp confirms correct poly0 packing (a0<<16)|a1.")

    with open(sim_cpp, "r", encoding="utf-8") as f:
        sim_code = f.read()
    m_sim = re.search(r"simulate_q2_histogram\s*\([^)]*\)\s*\{(.*?)\n\}", sim_code, re.DOTALL)
    assert m_sim, "simulate_q2_histogram definition not found in sim_engine.cpp!"
    sim_q2_body = m_sim.group(1)
    assert not re.search(r"poly0\s*=.*a1.*<<\s*16.*a0", sim_q2_body), "Inverted packing bug detected in sim_engine.cpp!"
    assert re.search(r"poly0\s*=.*a0.*<<\s*16.*a1", sim_q2_body), "Correct packing (a0<<16)|a1 not found in sim_engine.cpp!"
    print("[+] PASS: Static verification in sim_engine.cpp confirms correct poly0 packing (a0<<16)|a1.")

    if os.path.exists(q2_noisy_cpp):
        with open(q2_noisy_cpp, "r", encoding="utf-8") as f:
            q2_code = f.read()
        assert not re.search(r"poly0\s*=.*a1.*<<\s*16.*a0", q2_code), "Inverted packing bug detected in q2_noisy_sim.cpp!"
        assert re.search(r"poly0\s*=.*a0.*<<\s*16.*a1", q2_code), "Correct packing (a0<<16)|a1 not found in q2_noisy_sim.cpp!"
        print("[+] PASS: Static verification in q2_noisy_sim.cpp confirms correct poly0 packing (a0<<16)|a1.")

    if os.path.exists(blinding_cpp):
        with open(blinding_cpp, "r", encoding="utf-8") as f:
            blind_code = f.read()
        assert not re.search(r"poly0\s*=.*a1_eff.*<<\s*16.*a0_eff", blind_code), "Inverted packing bug in blinding_evaluation.cpp!"
        assert re.search(r"poly0\s*=.*a0_eff.*<<\s*16.*a1_eff", blind_code), "Correct packing not found in blinding_evaluation.cpp!"
        print("[+] PASS: Static verification in blinding_evaluation.cpp confirms correct poly0 packing.")

    # 5. Assert empirical tolerance bounds on independent q^2 simulation output
    q2_results_txt = os.path.join(root_dir, "replication", "phase2_noisy", "q2_noisy_sweep_results.txt")
    if os.path.exists(q2_results_txt):
        with open(q2_results_txt, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 6 and not parts[0].startswith('#') and not parts[0].startswith('sigma'):
                    if abs(float(parts[0]) - 0.5) < 1e-4:
                        p1_val = float(parts[1])
                        assert 0.85 <= p1_val <= 0.97, f"Independent q2 sweep regression! sigma=0.5 Top-1={p1_val}, expected in [0.85, 0.97]"
                        print(f"[+] PASS: Independent q2 simulation at sigma=0.5: Top-1={p1_val:.4f} within tolerance [0.85, 0.97] (Paper: 0.9336).")
                        break

    # 6. Assert empirical tolerance bounds on blinding countermeasure evaluation output
    blinding_results_txt = os.path.join(root_dir, "replication", "phase6_countermeasures", "blinding_noisy_sweep_results.txt")
    if os.path.exists(blinding_results_txt):
        with open(blinding_results_txt, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4 and not parts[0].startswith('#') and not parts[0].startswith('sigma'):
                    if abs(float(parts[0]) - 0.5) < 1e-4:
                        b_p1_val = float(parts[2])
                        assert b_p1_val < 0.01, f"Countermeasure failure! Blinded Top-1={b_p1_val}, expected < 0.01 (random guess baseline)"
                        print(f"[+] PASS: Blinding countermeasure at sigma=0.5: Top-1={b_p1_val:.4f} < 0.01 (suppressed to random guess).")
    # 7. Assert TVLA statistical significance (Unblinded leaks |t| > 4.5, Blinded passes |t| <= 4.5)
    tvla_results_txt = os.path.join(root_dir, "replication", "phase6_countermeasures", "tvla_results.txt")
    if os.path.exists(tvla_results_txt):
        max_u = 0.0
        max_b = 0.0
        with open(tvla_results_txt, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5 and not parts[0].startswith('#') and not parts[0].startswith('Sample'):
                    max_u = max(max_u, abs(float(parts[1])))
                    max_b = max(max_b, abs(float(parts[2])))
        assert max_u > 4.5, f"TVLA baseline regression failure! Max unblinded |t|={max_u}, expected > 4.5"
        assert max_b <= 4.5, f"TVLA countermeasure regression failure! Max blinded |t|={max_b}, expected <= 4.5"
        print(f"[+] PASS: TVLA statistical validation: Unblinded leaks (|t|={max_u:.2f} > 4.5), Blinded passes (|t|={max_b:.2f} <= 4.5).")

    print("-" * 70)
    print("ALL SIMULATION REGRESSION ASSERTIONS PASSED DETERMINISTICALLY.")
    print("=" * 70 + "\n")
    return True

if __name__ == '__main__':
    try:
        test_regression()
        sys.exit(0)
    except AssertionError as e:
        print(f"[-] REGRESSION TEST FAILED: {e}")
        sys.exit(1)
