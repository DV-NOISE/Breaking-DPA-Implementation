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

    # 4. Assert static source code packing consistency across sim_engine.cpp and noisy_sim.cpp
    root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))
    sim_cpp = os.path.join(root_dir, "replication", "phase1_noiseless", "sim_engine.cpp")
    noisy_cpp = os.path.join(root_dir, "replication", "phase2_noisy", "noisy_sim.cpp")

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
