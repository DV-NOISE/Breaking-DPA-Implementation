# Real-Hardware EM Leakage Characterization vs. Synthetic Model

### Reference Dataset
- **Authors:** Alain Alyosha Magazin & Karim M. Abdellatif (ePrint 2026/1851)
- **Hardware Platform:** STM32F407 (ARM Cortex-M4 @ 84 MHz)
- **Modality & Sampling Rate:** EM near-field probe, 6.25 GS/s (10,000 samples/trace)
- **Dataset Mode:** Extracted Live Hardware Data

### Empirical Findings
- **Share 0 (Mask $M$):** Peak SNR = **0.9035** at sample $t = 510$
- **Share 1 ($sk - M$):** Peak SNR = **0.4332** at sample $t = 472$
- **Fixed-vs-Variable TVLA:** Peak $|t| = 19.7574$ at sample $t = 2812$, Leaking POIs = 578 / 10000

### Comparison Against Synthetic Pipeline Model (`generate_synthetic_trs.py`)
1. **Temporal Separation of Shares:**
   - *Real Measurement:* The real EM traces exhibit distinct, well-separated leakage peaks for Share 0 and Share 1, reflecting sequential execution in `basemul_asm`.
   - *Synthetic Model:* Our synthetic emulator in `generate_synthetic_trs.py` modeled intermediate accumulation across pipeline stages. The real hardware confirms that masking splits the leakage across distinct time intervals, validating the prerequisite for second-order CPA.
2. **Leakage Modality & SNR Amplitude:**
   - *Real EM Measurements:* Real EM captures exhibit localized SNR peaks with high high-frequency components from the switching activity of the Cortex-M4 multiplier.
   - *Synthetic Model:* In synthetic simulation, Gaussian noise is additive and stationary ($\sigma \in [0.5, 1.0]$). On real hardware, noise includes non-stationary clock jitter and instruction cache ripple.
3. **Pipeline Register Inertia:**
   - Examination of window boundaries reveals localized switching transients, providing physical grounding for the pipeline coupling exploited in the pair-pointwise DPA threat model.
