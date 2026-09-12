import os
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
import matplotlib.pyplot as plt

Q = 3329
QINV = 3327

def to_int16(x):
    x = int(x) & 0xFFFF
    return x if x < 32768 else x - 65536

def smul(x, y):
    return to_int16(x) * to_int16(y)

def compute_q_intermediates(a1, b1, zeta):
    # 5 intermediate states for q-template (odd coefficients)
    poly0 = (to_int16(a1) << 16)
    
    h0 = bin(poly0 & 0xFFFFFFFF).count('1')
    tmp = smul(a1, b1)
    h1 = bin(tmp & 0xFFFFFFFF).count('1')
    tmp2 = smul(tmp, QINV)
    h2 = bin(tmp2 & 0xFFFFFFFF).count('1')
    tmp2 = smul(Q, tmp2) + tmp
    h3 = bin(tmp2 & 0xFFFFFFFF).count('1')
    tmp2 = smul(tmp2 >> 16, zeta)
    h4 = bin(tmp2 & 0xFFFFFFFF).count('1')
    return np.array([h0, h1, h2, h3, h4], dtype=np.float32)

def pearson_corr(a, b):
    a_diff = a - np.mean(a)
    b_diff = b - np.mean(b)
    denom = np.sqrt(np.sum(a_diff ** 2) * np.sum(b_diff ** 2))
    return float(np.sum(a_diff * b_diff) / denom) if denom > 1e-12 else 0.0

def run_ml_benchmark(noise_sigma=0.35, n_train_per_class=10, n_test=500):
    print(f"\n[*] Benchmarking Machine Learning vs Pearson Correlation for q-attack...")
    print(f"[*] Noise standard deviation: sigma = {noise_sigma}")
    
    b1 = 2345
    zeta = 2226
    
    # In Kyber, secret coefficients are small integers in {-2, -1, 0, 1, 2} mod 3329
    candidate_classes = [0, 1, 2, 3327, 3328]
    class_map = {c: i for i, c in enumerate(candidate_classes)}
    n_classes = len(candidate_classes)
    
    # 1. Generate Training Dataset (Profiling Phase)
    X_train = []
    y_train = []
    
    for c in candidate_classes:
        clean_template = compute_q_intermediates(c, b1, zeta)
        for _ in range(n_train_per_class):
            noise = np.random.normal(0, noise_sigma, size=5)
            X_train.append(clean_template + noise)
            y_train.append(class_map[c])
            
    X_train = np.array(X_train)
    y_train = np.array(y_train)
    
    # 2. Train Multi-Layer Perceptron (MLP) Neural Network with Feature Scaling
    print(f"[*] Training Neural Network Profiler on {len(X_train)} noisy traces...")
    mlp = make_pipeline(
        StandardScaler(),
        MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=1000, random_state=42, activation='relu')
    )
    mlp.fit(X_train, y_train)
    
    # 3. Test Phase (Attack Phase)
    pearson_ranks = []
    ml_ranks = []
    
    clean_templates = {c: compute_q_intermediates(c, b1, zeta) for c in candidate_classes}
    
    for _ in range(n_test):
        true_c = np.random.choice(candidate_classes)
        true_label = class_map[true_c]
        test_trace = clean_templates[true_c] + np.random.normal(0, noise_sigma, size=5)
        
        # Method A: Pearson Correlation Matching (Authors' Method)
        corrs = []
        for c in candidate_classes:
            r = pearson_corr(test_trace, clean_templates[c])
            corrs.append((class_map[c], r))
        corrs.sort(key=lambda x: x[1], reverse=True)
        p_rank = [i for i, item in enumerate(corrs) if item[0] == true_label][0] + 1
        pearson_ranks.append(p_rank)
        
        # Method B: Machine Learning Profiling (Proposed Improvement)
        probs = mlp.predict_proba(test_trace.reshape(1, -1))[0]
        ml_sorted = np.argsort(-probs)
        ml_rank = np.where(ml_sorted == true_label)[0][0] + 1
        ml_ranks.append(ml_rank)
        
    p_top1 = np.mean(np.array(pearson_ranks) == 1) * 100.0
    p_top2 = np.mean(np.array(pearson_ranks) <= 2) * 100.0
    ml_top1 = np.mean(np.array(ml_ranks) == 1) * 100.0
    ml_top2 = np.mean(np.array(ml_ranks) <= 2) * 100.0
    
    print("\n" + "="*70)
    print("      RESEARCH COMPARISON: PEARSON CORRELATION VS ML PROFILING")
    print("="*70)
    print(f"Metric                        Pearson (Authors)    ML Profiler (Ours)")
    print("-" * 70)
    print(f"Top-1 Candidate Accuracy      {p_top1:15.2f}%    {ml_top1:15.2f}%")
    print(f"Top-2 Candidate Accuracy      {p_top2:15.2f}%    {ml_top2:15.2f}%")
    print(f"Average Rank of True Key      {np.mean(pearson_ranks):15.2f}     {np.mean(ml_ranks):15.2f}")
    print("="*70 + "\n")
    
    # Save comparative visualization
    plots_dir = os.path.dirname(os.path.abspath(__file__))
    plt.figure(figsize=(7, 4.5))
    methods = ['Top-1 Accuracy', 'Top-2 Accuracy']
    x = np.arange(len(methods))
    width = 0.35
    plt.bar(x - width/2, [p_top1, p_top2], width, label='Pearson Correlation (Paper)', color='#4C72B0')
    plt.bar(x + width/2, [ml_top1, ml_top2], width, label='ML Profiler (Proposed)', color='#55A868')
    plt.ylabel('Accuracy (%)')
    plt.title(f'Improvement in q+q Attack Recovery (sigma = {noise_sigma})')
    plt.xticks(x, methods)
    plt.ylim(0, 105)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(loc='lower right')
    plt.tight_layout()
    plot_path = os.path.join(plots_dir, "ml_vs_pearson_improvement.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"[+] Saved comparative evaluation figure to: {plot_path}")

if __name__ == '__main__':
    run_ml_benchmark()
