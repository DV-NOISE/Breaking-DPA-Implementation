import os
import sys

zetas = [
    2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653,
    3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254,
    817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670,
    2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628
]

# Robust path resolution: find the zetas/ directory regardless of where python is executed from
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ZETAS_DIR = os.path.join(SCRIPT_DIR, "zetas")
if not os.path.exists(ZETAS_DIR):
    # Fallback to current working directory
    ZETAS_DIR = os.path.join(os.getcwd(), "replication/phase1_noiseless/zetas")

def compute_mean(fname):
    mean_dist = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}
    if not os.path.exists(fname):
        print(f"Error: {fname} not found!")
        return None
    with open(fname, 'r') as f:
        i = 0
        for line in f.readlines():
            line = line.rstrip()
            tokens = line.split(',')
            for tok in tokens:
                if ':' in tok:
                    typestr, pstr = tok.split(':')
                    coltype = int(typestr)
                    p = float(pstr)
                    if i > 0:
                        mean_dist[coltype] = (mean_dist[coltype] + p) / 2.0
                    else:
                        mean_dist[coltype] = p
            i += 1
    return mean_dist

def main():
    # Fix author bug: use dictionary or range(6) to prevent IndexError when col == 5
    COL_DATA = {1: [], 2: [], 3: [], 4: [], 5: []}

    for i in range(0, 64):
        fname_pos = os.path.join(ZETAS_DIR, f"zeta-{i}-{zetas[i]}.dat")
        dist_pos = compute_mean(fname_pos)
        if dist_pos:
            for col in dist_pos:
                COL_DATA[col].append(dist_pos[col])

        fname_neg = os.path.join(ZETAS_DIR, f"zeta-{i}-{-zetas[i]}.dat")
        dist_neg = compute_mean(fname_neg)
        if dist_neg:
            for col in dist_neg:
                COL_DATA[col].append(dist_neg[col])

    print("\n" + "="*70)
    print("   EXPECTED COLLISION PROBABILITIES OVER ALL 128 ZETAS")
    print("="*70)
    for col in sorted(COL_DATA.keys()):
        if COL_DATA[col]:
            mu = sum(COL_DATA[col]) / len(COL_DATA[col])
            print(f"Mean col({col}) [Multiplicity {col}-way]: {mu:.6f}")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
