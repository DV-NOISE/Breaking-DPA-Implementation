import os
import math
import matplotlib.pyplot as plt

def nCr(n, r):
    return math.comb(n, r)

def compute_recovery_probability(p1, p100, max_brute=5, total_coeffs=128):
    # Formula from Section 4.3 (page 23):
    # p_100^128 * sum_{l=0}^{5} (128 choose l) * (1 - p1)^l * p1^(128 - l)
    binomial_sum = 0.0
    for l in range(max_brute + 1):
        term = nCr(total_coeffs, l) * ((1.0 - p1) ** l) * (p1 ** (total_coeffs - l))
        binomial_sum += term
    return (p100 ** total_coeffs) * binomial_sum

def load_results_file(fname):
    data = []
    with open(fname, 'r') as f:
        lines = [line.strip().split() for line in f if line.strip()]
    header = lines[0]
    for r in lines[1:]:
        data.append({
            'x': float(r[0]),
            'y1': float(r[1]),
            'y2': float(r[2]),
            'y3': float(r[3]),
            'y10': float(r[4]),
            'y100': float(r[5])
        })
    return data

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_dirs = [
        os.path.join(script_dir, "../../author_files/checkpoints_and_datasets"),
        os.path.join(script_dir, "../../../author_files/checkpoints_and_datasets"),
        "author_files/checkpoints_and_datasets",
        "../../author_files/checkpoints_and_datasets"
    ]
    author_dir = next((d for d in possible_dirs if os.path.isdir(d)), possible_dirs[0])
    q_file = os.path.join(author_dir, "q+q-sd-results.csv")
    q2_file = os.path.join(author_dir, "q-squared-sd-results.csv")
    plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    q_data = load_results_file(q_file)
    q2_data = load_results_file(q2_file)
    
    print("\n" + "="*75)
    print("  TABLE 1: NOISY SIMULATION DATA (Author Reference Dataset Parsing)")
    print("="*75)
    print(f"{'# templates':<15} {'sigma':<8} {'Top 1':<10} {'Top 2':<10} {'Top 3':<10} {'Recovery P(l<=5)':<15}")
    print("-" * 75)
    
    print("q-templates:")
    for sigma in [0.3, 0.4, 0.5, 0.6, 0.7]:
        match = [d for d in q_data if abs(d['x'] - sigma) < 1e-4]
        if match:
            d = match[0]
            p_rec = compute_recovery_probability(d['y1'], d['y100'])
            print(f"{'q':<15} {d['x']:<8.1f} {d['y1']:<10.4f} {d['y2']:<10.4f} {d['y3']:<10.4f} {p_rec:<15.4e}")
            
    print("-" * 75)
    print("q^2-templates:")
    for sigma in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        match = [d for d in q2_data if abs(d['x'] - sigma) < 1e-4]
        if match:
            d = match[0]
            p_rec = compute_recovery_probability(d['y1'], d['y100'])
            print(f"{'q^2':<15} {d['x']:<8.1f} {d['y1']:<10.4f} {d['y2']:<10.4f} {d['y3']:<10.4f} {p_rec:<15.4e}")
            
    print("="*75 + "\n")

    # Generate Figure 6 (q-templates noise curves)
    plt.figure(figsize=(9, 5))
    x_q = [d['x'] for d in q_data if d['x'] <= 1.0]
    plt.plot(x_q, [d['y1'] for d in q_data if d['x'] <= 1.0], label="top 1", color="blue")
    plt.plot(x_q, [d['y2'] for d in q_data if d['x'] <= 1.0], label="top 2", color="orange")
    plt.plot(x_q, [d['y3'] for d in q_data if d['x'] <= 1.0], label="top 3", color="green")
    plt.plot(x_q, [d['y10'] for d in q_data if d['x'] <= 1.0], label="top 10", color="red")
    plt.plot(x_q, [d['y100'] for d in q_data if d['x'] <= 1.0], label="top 100", color="purple")
    plt.xlabel("Gaussian Noise Standard Deviation (sigma)")
    plt.ylabel("Probability of match")
    plt.title("Figure 6 Replication: q-template Candidate Match Probabilities vs Noise")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(loc="lower left")
    fig6_path = os.path.join(plots_dir, "figure6_q_candidates.png")
    plt.tight_layout()
    plt.savefig(fig6_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 6 replication plot to: {fig6_path}")

    # Generate Figure 7 (q^2-templates noise curves)
    plt.figure(figsize=(9, 5))
    x_q2 = [d['x'] for d in q2_data if d['x'] <= 1.0]
    plt.plot(x_q2, [d['y1'] for d in q2_data if d['x'] <= 1.0], label="top 1", color="blue")
    plt.plot(x_q2, [d['y2'] for d in q2_data if d['x'] <= 1.0], label="top 2", color="orange")
    plt.plot(x_q2, [d['y3'] for d in q2_data if d['x'] <= 1.0], label="top 3", color="green")
    plt.plot(x_q2, [d['y10'] for d in q2_data if d['x'] <= 1.0], label="top 10", color="red")
    plt.plot(x_q2, [d['y100'] for d in q2_data if d['x'] <= 1.0], label="top 100", color="purple")
    
    # Add recovery probability curve
    rec_q2 = [compute_recovery_probability(d['y1'], d['y100']) for d in q2_data if d['x'] <= 1.0]
    plt.plot(x_q2, rec_q2, label="P(recover full key, l<=5)", color="black", linestyle="--", linewidth=2)
    
    plt.xlabel("Gaussian Noise Standard Deviation (sigma)")
    plt.ylabel("Probability of match")
    plt.title("Figure 7 Replication: q^2-template Candidate Match & Key Recovery vs Noise")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(loc="lower left")
    fig7_path = os.path.join(plots_dir, "figure7_q2_candidates.png")
    plt.tight_layout()
    plt.savefig(fig7_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 7 replication plot to: {fig7_path}")

if __name__ == '__main__':
    main()
