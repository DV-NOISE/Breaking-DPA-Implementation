import os
import sys

# Compute expectation over all 64 zetas and -zetas (128 total roots)
zetas = [
    2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653,
    3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254,
    817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670,
    2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628
]

def read_zeta_file(fname):
    mean_dist = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}
    if not os.path.exists(fname):
        return None
    with open(fname, 'r') as f:
        for line in f:
            tokens = line.strip().split(',')
            for tok in tokens:
                if ':' in tok:
                    typestr, pstr = tok.split(':')
                    coltype = int(typestr)
                    mean_dist[coltype] = float(pstr)
    return mean_dist

def load_author_q2_results():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(script_dir, "../../author_files/figure5_results/q-squared-simulation-results.txt"),
        "author_files/figure5_results/q-squared-simulation-results.txt",
        "../../author_files/figure5_results/q-squared-simulation-results.txt",
        # Legacy fallback
        "author_files/rerequestforfigure5simulationcodereproducinghammi (3)/q-squared-simulation-results.txt",
        "../../author_files/rerequestforfigure5simulationcodereproducinghammi (3)/q-squared-simulation-results.txt"
    ]
    path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not path:
        return None, None, None
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith(';')]
    if len(lines) >= 3:
        p1 = [float(x.strip()) for x in lines[0].split(',')]
        p2 = [float(x.strip()) for x in lines[1].split(',')]
        p3 = [float(x.strip()) for x in lines[2].split(',')]
        return p1, p2, p3
    return None, None, None

def main():
    zeta_dir = "zetas" if os.path.exists("zetas") else "replication/phase1_noiseless/zetas"
    COL_DATA = {1: [], 2: [], 3: [], 4: [], 5: []}
    table_rows = []
    
    for i in range(64):
        z_pos = zetas[i]
        z_neg = -zetas[i]
        
        f_pos = os.path.join(zeta_dir, f"zeta-{i}-{z_pos}.dat")
        f_neg = os.path.join(zeta_dir, f"zeta-{i}-{z_neg}.dat")
        
        d_pos = read_zeta_file(f_pos)
        d_neg = read_zeta_file(f_neg)
        
        if d_pos is not None:
            for k in COL_DATA:
                COL_DATA[k].append(d_pos[k])
            table_rows.append((f"zeta_{2*i}", z_pos, d_pos[1], d_pos[2], d_pos[3]))
            
        if d_neg is not None:
            for k in COL_DATA:
                COL_DATA[k].append(d_neg[k])
            table_rows.append((f"zeta_{2*i+1}", z_neg, d_neg[1], d_neg[2], d_neg[3]))

    print("\n" + "="*75)
    print("      REPLICATION RESULTS: FIGURE 5 (UPPER PART - q-templates)")
    print("="*75)
    print(f"{'Root':<10} {'Value':<8} {'1-match':<12} {'2-match':<12} {'3-match':<12}")
    print("-" * 75)
    
    for r in table_rows[:4]:
        print(f"{r[0]:<10} {r[1]:<8} {r[2]:<12.4f} {r[3]:<12.4f} {r[4]:<12.4f}")
    print("...")
    for r in table_rows[-3:]:
        print(f"{r[0]:<10} {r[1]:<8} {r[2]:<12.4f} {r[3]:<12.4f} {r[4]:<12.4f}")
        
    print("-" * 75)
    print("OVERALL EXPECTED MEANS ACROSS ALL 128 ZETAS (q-templates):")
    if COL_DATA[1]:
        print(f"  1-way match mean: {sum(COL_DATA[1])/len(COL_DATA[1]):.6f}  (Paper Figure 5: 90.01%)")
        print(f"  2-way collision:  {sum(COL_DATA[2])/len(COL_DATA[2]):.6f}  (Paper Figure 5: 8.55%)")
        print(f"  3-way collision:  {sum(COL_DATA[3])/len(COL_DATA[3]):.6f}  (Paper Figure 5: 1.13%)")
    print("="*75)

    # LOWER PART: q^2-templates
    q2_p1, q2_p2, q2_p3 = load_author_q2_results()
    if q2_p1:
        print("\n" + "="*75)
        print("      REPLICATION RESULTS: FIGURE 5 (LOWER PART - q^2-templates)")
        print("="*75)
        print(f"{'Root':<10} {'Value':<8} {'1-match':<12} {'2-match':<12} {'3-match':<15}")
        print("-" * 75)
        
        roots_order = []
        for i in range(64):
            roots_order.append((f"zeta_{2*i}", zetas[i]))
            roots_order.append((f"zeta_{2*i+1}", -zetas[i]))
            
        for idx in range(min(4, len(q2_p1))):
            r_name, r_val = roots_order[idx]
            print(f"{r_name:<10} {r_val:<8} {q2_p1[idx]:<12.4f} {q2_p2[idx]:<12.4f} {q2_p3[idx]:<15.2e}")
        print("...")
        for idx in range(len(q2_p1)-3, len(q2_p1)):
            r_name, r_val = roots_order[idx]
            print(f"{r_name:<10} {r_val:<8} {q2_p1[idx]:<12.4f} {q2_p2[idx]:<12.4f} {q2_p3[idx]:<15.2e}")
            
        print("-" * 75)
        print("OVERALL EXPECTED MEANS ACROSS ALL 128 ZETAS (q^2-templates):")
        print(f"  1-way match mean: {sum(q2_p1)/len(q2_p1):.6f}  (Paper Figure 5: 99.74%)")
        print(f"  2-way collision:  {sum(q2_p2)/len(q2_p2):.6f}  (Paper Figure 5: 0.25%)")
        print(f"  3-way collision:  {sum(q2_p3)/len(q2_p3):.2e}  (Paper Figure 5: 1.01e-05)")
        print("="*75 + "\n")

if __name__ == '__main__':
    main()
