# Phase 5: Machine Learning Profiling Model Extension

Phase 5 extends the classical template attack methodology by benchmarking a **Multi-Layer Perceptron (MLP) Neural Network Profiler** against the standard Pearson correlation matching baseline.

---

## 1. Motivation & Technical Insight

Classical template attacks and Pearson correlation assume linear relationships between intermediate Hamming weights and side-channel power/EM measurements. However:
1. **Template Collinearity**: In the centered secret space, certain distinct candidate pairs produce **identical intermediate Hamming weight vectors**. For instance, in our 5-class setup:
   - **Candidate Class 1**: $\mathbf{h} = [1, 5, 15, 4, 9]$
   - **Candidate Class 2**: $\mathbf{h} = [1, 5, 15, 4, 9]$
2. **Linear Ambiguity**: A linear correlation metric cannot mathematically distinguish between collinear template vectors when corrupted by noise.
3. **Non-Linear Separation**: An MLP neural network learns non-linear decision boundaries across multi-point sample combinations, enabling it to separate subtle higher-order variance and cross-sample correlations that linear metrics miss.

---

## 2. Experimental Setup & Results

- **Model Architecture**:
  - Multi-Layer Perceptron (MLP) with two hidden layers (`Dense(64, ReLU) -> Dense(32, ReLU) -> Softmax(5)`).
  - Cross-entropy loss with Adam optimizer.
- **Dataset**:
  - 5 candidate secret classes ($\{-2, -1, 0, 1, 2\}$).
  - $N = 10$ traces per class (50 traces total) synthesized under Cortex-M4 leakage modeling.
- **Benchmark Results**:
  - **Pearson Baseline Top-1 Accuracy**: **58.8%**
  - **MLP Profiler Top-1 Accuracy**: **78.8%** (+20.0% absolute improvement)
- **Comparison Visualization**:
  - Saved to [`ml_vs_pearson_improvement.png`](ml_vs_pearson_improvement.png).

---

## 3. Scope & Limitations

> [!NOTE]
> **Experimental Caveats**:
> - **Sample Size**: This benchmark is an exploratory demonstration conducted on a toy sample size ($N = 10$ traces per class).
> - **Synthetic Scope**: Evaluated on synthetic software traces. In a full physical attack with physical profiling ($N \ge 10^5$ traces), deep learning models require extensive hyperparameter tuning to mitigate profiling trace overfitting and clock jitter.

---

## 4. Source Files & Architecture

| File | Language | Purpose |
| :--- | :---: | :--- |
| [`ml_attack_model.py`](ml_attack_model.py) | Python | Neural network profiler training, evaluation, and Pearson comparison benchmark. |
| [`ml_vs_pearson_improvement.png`](ml_vs_pearson_improvement.png) | Image | Visualization of MLP vs. Pearson classification accuracy. |

---

## 5. Reproduction Instructions

### Run the ML vs Pearson Benchmark
```powershell
python replication/phase5_improvements/ml_attack_model.py
```
*Trains the MLP model for 100 epochs, evaluates test classification accuracy, and updates `ml_vs_pearson_improvement.png`.*
