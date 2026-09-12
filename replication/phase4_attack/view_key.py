import os
import numpy as np

def to_centered(val, q=3329):
    """Convert mod 3329 representation to centered range [-q//2, q//2] (e.g., -2 to 2)."""
    return val if val <= q // 2 else val - q

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    recovered_path = os.path.join(base_dir, "recovered_secret_key.npy")
    true_path = os.path.join(base_dir, "../phase3_hw_emulator/traces/true_secret_key.npy")

    if not os.path.exists(recovered_path):
        print(f"[-] Recovered key file not found: {recovered_path}")
        return

    recovered = np.load(recovered_path)
    has_true = os.path.exists(true_path)
    true_key = np.load(true_path) if has_true else None

    centered_recovered = np.array([to_centered(x) for x in recovered])
    centered_true = np.array([to_centered(x) for x in true_key]) if has_true else None

    print("=" * 75)
    print("                    KYBER SECRET KEY INSPECTION")
    print("=" * 75)
    print(f"File: {recovered_path}")
    print(f"Total coefficients: {len(recovered)}")

    if has_true:
        matches = np.sum(recovered == true_key)
        acc = (matches / len(recovered)) * 100
        print(f"Direct Top-1 Matches: {matches} / {len(recovered)} ({acc:.2f}%)")
    print("-" * 75)

    print("\n[+] First 32 Coefficients:")
    print("  Idx   | Raw (mod 3329) | Centered [-2, 2] | True Raw | True Centered | Match")
    print("  " + "-" * 67)
    for i in range(min(32, len(recovered))):
        rec_raw = int(recovered[i])
        rec_cen = int(centered_recovered[i])
        if has_true:
            tru_raw = int(true_key[i])
            tru_cen = int(centered_true[i])
            match_str = "OK" if rec_raw == tru_raw else "MISMATCH"
            print(f"  [{i:3d}] | {rec_raw:14d} | {rec_cen:+16d} | {tru_raw:8d} | {tru_cen:+13d} | {match_str}")
        else:
            print(f"  [{i:3d}] | {rec_raw:14d} | {rec_cen:+16d} |    -     |       -       |   -")

    print("\n[+] Full Polynomial Coefficients (Centered format: {-2, -1, 0, 1, 2}):")
    for row_start in range(0, len(recovered), 16):
        row_vals = centered_recovered[row_start:row_start + 16]
        formatted = " ".join(f"{v:+2d}" for v in row_vals)
        print(f"  Coeffs {row_start:3d}-{row_start+15:3d}: [ {formatted} ]")

    print("\n" + "=" * 75)

if __name__ == "__main__":
    main()
