import os
import numpy as np

def to_centered(val, q=3329):
    """Convert mod 3329 representation to centered range [-q//2, q//2] (e.g., -2 to 2)."""
    return val if val <= q // 2 else val - q

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    traces_dir = os.path.join(base_dir, "traces")
    secret_path = os.path.join(traces_dir, "true_secret_key.npy")
    public_b_path = os.path.join(traces_dir, "public_b.npy")
    trs_path = os.path.join(traces_dir, "synthetic_target_15.trs")

    if not os.path.exists(secret_path):
        print(f"[-] Target secret key not found at {secret_path}")
        print("    Run: python replication/phase3_hw_emulator/generate_synthetic_trs.py first.")
        return

    secret = np.load(secret_path)
    public_b = np.load(public_b_path) if os.path.exists(public_b_path) else None
    centered_s = np.array([to_centered(x) for x in secret])

    print("=" * 75)
    print("             PHASE 3: TARGET GROUND TRUTH & DATASET INSPECTION")
    print("=" * 75)
    print(f"Target TRS Trace: {trs_path} ({'Exists' if os.path.exists(trs_path) else 'Missing'})")
    print(f"Secret Key File:  {secret_path}")
    print(f"Public Vector b:  {public_b_path}")
    print(f"Total Polynomial Coefficients: {len(secret)}")
    print("-" * 75)

    print("\n[+] Secret Key Distribution:")
    for val in [-2, -1, 0, 1, 2]:
        cnt = np.sum(centered_s == val)
        pct = (cnt / len(centered_s)) * 100
        print(f"  Coefficient {val:+2d}: {cnt:3d} occurrences ({pct:5.1f}%)")

    print("\n[+] First 32 Target Secret Coefficients (Ground Truth):")
    print("  Idx   | Raw (mod 3329) | Centered [-2, 2] | Public Ciphertext b[i]")
    print("  " + "-" * 62)
    for i in range(min(32, len(secret))):
        s_raw = int(secret[i])
        s_cen = int(centered_s[i])
        b_val = f"{int(public_b[i]):5d}" if public_b is not None else "  -  "
        print(f"  [{i:3d}] | {s_raw:14d} | {s_cen:+16d} | {b_val:>22s}")

    print("\n[+] Full Secret Key Polynomial (Centered format: {-2, -1, 0, 1, 2}):")
    for row_start in range(0, len(secret), 16):
        row_vals = centered_s[row_start:row_start + 16]
        formatted = " ".join(f"{v:+2d}" for v in row_vals)
        print(f"  Coeffs {row_start:3d}-{row_start+15:3d}: [ {formatted} ]")

    print("\n" + "=" * 75)
    print("[i] Next step: Run Phase 4 attack and compare using view_key.py:")
    print("    1. python replication/phase4_attack/run_attack.py")
    print("    2. python replication/phase4_attack/view_key.py")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    main()
