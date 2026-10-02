# Countermeasure Evaluation: Polynomial Blinding vs. Unprotected Kyber-768

### Table: Attack Success Rates and Mitigation Factor under Gaussian Noise ($\sigma$)

| Gaussian Noise ($\sigma$) | Unprotected Top-1 ($p_1$) [ACNS 2024] | Blinded Top-1 ($p_1$) [Ours] | Blinded Top-100 ($p_{100}$) | Leakage Suppression Factor |
| :---: | :---: | :---: | :---: | :---: |
| **0.5** | 0.9336 (93.4%) | **0.0010 (0.10%)** | 0.0010 (0.10%) | **933.6x** |
| **0.6** | 0.8166 (81.7%) | **0.0000 (0.00%)** | 0.0000 (0.00%) | **816.6x** |
| **0.7** | 0.6707 (67.1%) | **0.0000 (0.00%)** | 0.0000 (0.00%) | **670.7x** |
| **0.8** | 0.5256 (52.6%) | **0.0000 (0.00%)** | 0.0000 (0.00%) | **525.6x** |
| **0.9** | 0.4003 (40.0%) | **0.0000 (0.00%)** | 0.0000 (0.00%) | **400.3x** |
| **1.0** | 0.2995 (29.9%) | **0.0000 (0.00%)** | 0.0000 (0.00%) | **299.5x** |


### Operation & Microarchitectural Overhead

| Metric | Baseline Unprotected Loop | Protected with Polynomial Blinding | Overhead / Cost |
| :--- | :---: | :---: | :---: |
| **Instructions per Pair Multiplication** | 13 instructions | 16 instructions | **+3 instructions (+23.08%)** |
| **Total Operations (128 Pairs)** | 1,664 instructions | 2,048 instructions | **+384 clock cycles** |
| **Ephemeral Randomness Demand** | 0 bytes | 2 bytes ($t \in \mathbb{Z}_q^\times$) per polynomial | Negligible (1 TRNG call) |
| **Memory & Register Footprint** | 0 extra registers | 1 temporary register ($t$) | Zero stack spill |
