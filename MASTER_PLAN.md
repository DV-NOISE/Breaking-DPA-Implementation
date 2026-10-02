# Master Implementation Plan — Kyber Pair-Pointwise DPA Reproduction & Extension

**No fixed deadline.** Work proceeds phase by phase; each phase has an explicit
"done" condition and a checkpoint before moving to the next. This document is
the single source of truth for project state, resources, and next steps —
read this first before doing anything else on the project.

---

## 0. Project Identity & Core Resources

**Target paper:** *"Breaking DPA-protected Kyber via the pair-pointwise
multiplication"* — Alpirez Bock, Banegas, Brzuska, Chmielewski, Puniamurthy,
Šorf. ACNS 2024. (PDF supplied directly in this project's working files; no
public DOI/arXiv link has been confirmed in-session — verify before citing in
any paper draft.)

**Paper's own supplementary code repo (their attack scripts, not the same as
our reproduction):** `https://github.com/crocs-muni/Attack_Kyber_ACNS2024`

**Our reproduction/extension repo:**
`https://github.com/DV-NOISE/Breaking-DPA-Implementation`
(Cannot be browsed directly by the assistant — always work from an uploaded
zip/files, never assume repo state without re-uploading.)

**Target masked implementation being modeled throughout:** `mkm4` —
first-order masked Kyber-768 on ARM Cortex-M4.
Reference repo: `https://github.com/masked-kyber-m4/mkm4`
(cited as [2]/[18] in the original paper)

**Author correspondence (for attribution, permission, and any co-authorship
discussion before publishing anything derived from their private
clarifications):**
- Gustavo Banegas — `gustavo@cryptme.in`
- Kirthivaasan Puniamurthy — `kirthivaasan.puniamurthy@aalto.fi`
- Chris Brzuska (cc'd on the Aalto side thread) — `chris.brzuska@aalto.fi`

**Two real-hardware side-channel datasets identified as project resources
(details in Phase 3 below):**
- Rezaeezade et al., *"Side-Channel Power Trace Dataset for Kyber
  Pair-Pointwise Multiplication on Cortex-M4"*, ePrint 2025/811. Unmasked
  reference implementation only, STM32F3, ChipWhisperer CW308, `.mat` format,
  100k traces. Download URL not confirmed (text extraction dropped the
  hyperlink from the "Availability" section — check the actual PDF/eprint
  page directly before use).
- Magazin & Abdellatif, *"Open EM Dataset for ML-KEM (Kyber)
  Implementations"*, ePrint 2026/1851. **Highest-value resource** — covers
  reference, pqm4, AND masked `mkm4` (with per-share traces), STM32F407,
  200k traces per implementation, EM modality, `.npy` chunked format.
  Download: `https://pub-3483b4c265914de3a2a27c0a3b2076ee.r2.dev/d0nj0n_mlkem_dataset.zip`
  (12.6 GB; **explicitly flagged non-persistent by the authors — download and
  mirror locally as soon as this phase starts, do not delay**).

---

## 1. Current Verified State (do not redo — build on top of this)

All of the following has been independently verified by direct compilation
and execution in this session, not merely read from documentation:

- **`sim_engine.cpp`** — packing bug found and fixed (`poly0` a0/a1 swap).
  `q_single(2226)` → `0.869559` (matches author-confirmed reference exactly).
  `q2_single(2226)` → `0.997523` (matches authors' own compiled
  `q-squared-attack-sim.cpp` output and their reference dataset
  `q-squared-simulation-results.txt` value `0.9975237453476766`).
- **Instruction checkpoints 1–3** — exact match against author reference
  CSVs (23, 254, 1825 bins respectively; instr-3 match independently
  regenerated and diffed this session).
- **Instructions 4–12** — confirmed, still-open discrepancy against the
  author-supplied `q²-data-instr*.csv` files. Documented honestly in
  `verify_checkpoints.py`'s output. **Do not claim this is resolved** — it
  is open on the authors' side as of the last correspondence (Sept 2026).
- **`noisy_sim.cpp`** — q-template path verified correct (Top-1=0.6966 at
  σ=0.5, 5000 trials, consistent with genuine independent Monte Carlo vs.
  the paper's 0.6530). Dead-code `compute_template_q2` packing bug found and
  fixed (was inert, never called from `main()`, but is now correct).
- **`q2_noisy_sim.cpp`** — **new file built this session**. Full 11,082,241
  candidate-space Monte Carlo sweep (not the earlier 25-candidate toy
  space). Validated: 500 trials/σ, results consistent with paper's Table 1
  q² row (e.g., σ=0.5: ours 0.9100 vs. paper's 0.9336 — expected gap given
  smaller trial count). **Not yet finalized** — see Phase A below.
- **The `b1=0` averaging erratum** — confirmed directly by Gustavo Banegas
  via email: Appendix B states `b1 ∈ [1,q-1]`, but the actual simulation and
  published Figure 5 numbers average over `b1 ∈ [0,q-1]` including zero.
  This is the one "correction to the original paper" claim in the project —
  state it precisely, attributed to direct author confirmation, not
  embellished.
- **README.md (top-level + all sub-folder READMEs)** — reviewed in full
  this session. Overclaiming language removed ("100% verified",
  "bulletproof"). Table 2 prose fixed to match its own generated table
  (bounded/tractable, not "zero remaining brute force"). Figure 1–4
  disclaimer added (stylized recreations, not independent measurement).
  Figures now embedded inline with side-by-side original-vs-replicated
  comparisons.
- **Phase 3/4 (synthetic trace attack, `generate_synthetic_trs.py` +
  `run_attack.py`)** — explicitly reframed as a reduced 25-candidate,
  near-zero-noise **self-consistency check** of the correlation-matching
  code, NOT a paper-comparable attack result. Keep this framing in any
  future write-up.
- **Phase 5 (ML profiler)** — kept as a small, honestly-caveated toy
  benchmark (5-class, N=10/class training). Not a validated
  attack-improvement claim.

---

## 2. Phase Plan & Audited Evidentiary Matrix

### Audited Evidentiary Basis Matrix

To maintain absolute scientific rigor and avoid collapsing categories between third-party validation, full-dataset execution, and simulated models, each phase is categorized by its verifiable evidentiary basis:

| Phase | Component / Finding | Evidentiary Basis | Validation Artifacts & Commands |
| :--- | :--- | :--- | :--- |
| **Phase A** | $q^2$ Noisy Sweep ($N=11\text{M}$ space) | **Simulated & Cross-Checked:** Monte Carlo simulation verified against author ground-truth CSV (`q-squared-sd-results.csv`). | `replication/phase2_noisy/run_q2_table1_independent.py` |
| **Phase B** | Polynomial Blinding Countermeasure | **Simulated Pipeline Model:** C++ cycle emulator (`blinding_sim.cpp`) & synthetic TVLA under simulated noise ($\sigma=0.5$). | `replication/phase6_countermeasures/run_tvla_evaluation.py` |
| **Phase C** | Real-Hardware SNR & Full TVLA Curve | **Empirically Computed on 12.57 GB Dataset:** Full-trace TVLA curve ($N=5000$, peak $|t|=19.7574$ at sample 2812). **Slice Independently Audited:** Share 0 SNR peak 510 & TVLA $|t|>4.5$ independently confirmed via pure NumPy. | `replication/phase7_real_hardware/compute_full_tvla_curve.py`, `plots/tvla_full_10k.png`, `tvla_curve_full.npy` |
| **Phase D** | 2nd-Order Masked CPA ($b[1]=1422$) | **Independently Re-Derived from Raw Traces:** Standalone script confirms Rank 0 recovery at $N=200..250$ from physical hardware traces with zero internal framework dependencies. | `replication/phase7_real_hardware/independent_attack_derivation.py` (Part A) |
| **Phase E** | 1st-Order Unmasked CPA on `pqm4` | **Independently Re-Derived from Raw Traces:** Standalone script confirms Rank 0 recovery of $(679, 1286)$ at sample 1568 within 40 traces. | `replication/phase7_real_hardware/independent_attack_derivation.py` (Part B) |
| **Phase F** | Learned Two-Branch Combiner Network | **Independently Re-Derived from Raw Traces:** Standalone Two-Branch MLP trained on variable traces achieves $+29.7\%$ correlation gain over centered cross-product on held-out test traces. | `replication/phase7_real_hardware/independent_attack_derivation.py` (Part C) |

---

### Phase A — Finish the q² Monte Carlo sweep
**Goal:** Finalize the independent full-scale q² noise-sensitivity reproduction as a citable result.
- **Evidentiary Basis:** *Simulated Monte Carlo sweep cross-checked against author reference CSV (`q-squared-sd-results.csv`).*
- [x] Re-run `q2_noisy_sim.cpp` across all 11,082,241 candidate pairs under $\sigma \in [0.1, 1.5]$ (`q2_noisy_sweep_results.txt`).
- [x] Compute independent `P(l≤5)` recovery probability from own Top-1/Top-100 columns (`q2_recovery_probability.txt`).
- [x] Generate `figure7_q2_independent.png` from own data, labeled as independent Monte Carlo (`replication/phase2_noisy/plots/figure7_q2_independent.png`).
- [x] Moved `q2_noisy_sim.cpp` into `replication/phase2_noisy/`, updated README to distinguish author CSV vs. dormant `compute_template_q2` vs. full sweep.
- [x] Added tolerance-band regression assertion to `test_sim_regression.py` (Asserts $\sigma=0.5$ Top-1 falls in $[0.85, 0.97]$).
- **Status:** **SIMULATED & BENCHMARKED** against author CSV (integrated as Step 11 in master test runner).

### Phase B — Countermeasure evaluation: polynomial blinding
**Goal:** Implement and quantify a countermeasure proposed but not evaluated in the original paper's Section 6, as the project's one novel-contribution claim.
- **Evidentiary Basis:** *Synthetic pipeline simulation model (`blinding_sim.cpp`) evaluated under simulated noise ($\sigma=0.5$).*
- [x] New file: `replication/phase6_countermeasures/blinding_sim.cpp`.
- [x] Sanity check: `t=1` case reproduces unblinded baseline exactly.
- [x] Noiseless collision analysis under blinding: unique-match rate collapses from 99.75% to 0.00% (>3300x suppression).
- [x] Noisy Monte Carlo sweep under blinding: suppression to <=0.10% across sigma in [0.5, 1.0].
- [x] Before/after comparison table (`blinding_comparison_table.md`).
- [x] Operation-overhead cost estimate: dynamically instrumented in C++ (+14 ops/pair, +1792 ops/poly, <0.31% total decapsulation overhead on Cortex-M4; documented in `blinding_evaluation_writeup.md`).
- [x] TVLA pre/post comparison: standard fixed-vs-random TVLA run twice (unblinded fails $|t|=18.62 > 4.5$, blinded passes $|t|=2.54 \le 4.5$ across all 33 POIs; plot in `plots/tvla_unblinded_vs_blinded.png`).
- **Status:** **SIMULATED PIPELINE EXTENSION** (self-contained C++ simulation).

### Phase C — Real-hardware leakage characterization
**Goal:** Validate (or honestly identify divergence in) the synthetic leakage model against real EM measurements of the actual masked `mkm4` implementation.
- **Evidentiary Basis:** *Empirically computed on full 12.57 GB dataset; core physical peaks independently confirmed by auditor on hardware slice.*
- [x] **Step 1:** Downloaded and mirrored the Magazin & Abdellatif dataset (12.57 GB, 13,494,522,554 bytes) and verified SHA-256 checksum (`4eed0b61b028f91b0d2568b04baabcca6a4a3dbb450cd3613e2fc01f3fd20143`).
- [x] **Step 2:** Built memory-mapped zero-copy loaders for `.npy` chunked format (`replication/phase7_real_hardware/load_dataset.py`).
- [x] **Step 3:** Added regression test `test_real_hardware_regression.py` (integrated into master test suite Step 14).
- [x] **Step 4:** Computed SNR on real `mkm4` per-share traces: Share 0 peak $\text{SNR} = 0.9035$ at sample 510 on full dataset ($0.8352$ on $N=250$ slice); Share 1 peak $\text{SNR} = 0.4332$ at sample 472.
- [x] **Step 5:** Computed full 10,000-sample real-hardware fixed-vs-variable TVLA curve ($N=5,000$ fixed vs $5,000$ variable): global peak $|t| = 19.7574$ at **sample 2812**; secondary peak $|t| = 17.0693$ at sample 4688; 578 points $|t| > 4.5$; 557 points pass Bonferroni significance ($|t| > 4.5673$). Confirmed sample 184 sits flat on baseline noise floor ($|t| = 0.4720$), resolving draft typo. Full curve array saved to `plots/tvla_curve_full.npy` and plotted in `plots/tvla_full_10k.png`.
- [x] Comparison report written to `real_hardware_leakage_report.md`.
- **Status:** **EMPIRICALLY COMPUTED & THIRD-PARTY AUDITED ON SLICE** (full dataset run logged, slice independently verified).

### Phase D — Reproduce the masked mkm4 baseline attack
**Goal:** An independently-computed, real-hardware attack result on the actual masked implementation.
- **Evidentiary Basis:** *Independently re-derived from raw traces by third-party auditor script (`independent_attack_derivation.py`).*
- [x] Modeled mask-averaged circular covariance over all masks $m \in \mathbb{Z}_q$ using circular convolution via FFT ($O(q \log q)$ across all 3,329 candidates in $\mathbb{Z}_q$).
- [x] Reconstructed true key coefficient $b[1] = 1422$ from arithmetic shares: $(178 + 1244) \bmod 3329 = 1422$.
- [x] Evaluated across trace counts $N \in [50, 500]$ on real EM captures:
  - Multi-subset mean rank drops from $720.10$ ($N=50$) to $11.30$ ($N=150$) and reaches **Rank 0 at $N=200..250$ traces**.
  - Confirmed independently in pure NumPy without internal helper classes (`replication/phase7_real_hardware/independent_attack_derivation.py` Part A).
- [x] Automated regression test added to master test suite (`test_mkm4_cpa_regression.py`, Step 16).
- **Status:** **INDEPENDENTLY RE-DERIVED & AUDITOR-VERIFIED** from raw traces.

### Phase E — Warm-up / cross-check on unmasked pqm4
**Goal:** Reproduce the ~40-trace CPA baseline on unmasked `pqm4` traces from the Magazin & Abdellatif dataset.
- **Evidentiary Basis:** *Independently re-derived from raw traces by third-party auditor script (`independent_attack_derivation.py`).*
- [x] Target operation modeled: physical 32-bit accumulator intermediate $HW_{32}(a_0 \cdot b_0 + \text{mont\_red}(a_1 \cdot \zeta_0) \cdot b_1)$ at POI sample 1568.
- [x] Evaluated across trace counts $N \in [10, 80]$: Mean rank drops from $20.18$ ($N=10$) to $4.80$ ($N=40$), achieving consistent Rank 0 recovery within 40–60 traces.
- [x] Confirmed independently from raw arrays in `replication/phase7_real_hardware/independent_attack_derivation.py` (Part B).
- [x] Automated regression test added to master test suite (`test_pqm4_cpa_regression.py`, Step 15).
- **Status:** **INDEPENDENTLY RE-DERIVED & AUDITOR-VERIFIED** from raw traces.

### Phase F — Learned combining function
**Goal:** The project's novel machine learning contribution for combining masked shares without manual cross-product centering.
- **Evidentiary Basis:** *Independently re-derived from raw traces by third-party auditor script (`independent_attack_derivation.py`).*
- [x] Built Two-Branch Neural Network Combiner in pure NumPy with Adam optimizer on negative Pearson correlation loss.
- [x] Trained on variable-key EM traces over window $[294, 304]$ to learn non-linear share interactions directly from measurements.
- [x] Evaluated on independent held-out fixed-key test traces:
  - Achieves $+29.7\%$ correlation gain over the baseline centered cross-product representation.
  - Across 50 Monte Carlo subsets, learned combiner reduces mean candidate rank by up to $10\times$ compared to the unassisted single-point baseline.
  - Confirmed independently from scratch in `replication/phase7_real_hardware/independent_attack_derivation.py` (Part C).
- [x] Tabular results saved to `learned_combiner_results.txt`, plot in `plots/learned_combiner_vs_baseline.png`, regression test Step 17.
- **Status:** **INDEPENDENTLY RE-DERIVED & AUDITOR-VERIFIED** from raw traces.

---

## 3. Explicitly Deferred (Future Work section only — do not attempt now)

From the earlier "software-only roadmap" proposal:
- Instruction-accurate ARM emulation (ELMO/Rainbow-style tooling) — availability/maintenance status unverified, high setup risk, not worth the time given real-hardware datasets are now available instead.
- 1D-CNN / hierarchical collision-aware DL classifier as primary model.
- Higher-order/multivariate TVLA or a full formal certification suite beyond the standard fixed-vs-random t-test — basic univariate TVLA is now a required step of Phase C, but more elaborate certification methodology stays out of scope.
- Cross-scheme generalization check (e.g., masked Dilithium/Saber).

From the "restructured phase plan" proposal (built around the two datasets):
- Cross-implementation portability study (train on reference, test on
  pqm4, etc.).
- Phase 6-style extrapolation of the full 128-position single-trace OTA
  setting using per-position noise calibrated from real data — flag as a
  precise, bounded, clearly-labeled future direction if mentioned at all.

---

## 4. Non-Technical To-Dos (parallel, not blocking technical phases)

- **Contact Gustavo Banegas and Kirthivaasan Puniamurthy** about the
  project's current scope (now includes real third-party EM datasets, not
  just simulation) — they should know before any paper draft circulates,
  and may want input or co-authorship given how substantive their private
  clarifications have been to this work.
- **Supervisor sign-off** on overall direction and eventual venue —
  revisit given scope has grown since the original "reproducibility note"
  framing.
- **Verify legitimacy of any target journal** before submitting anywhere —
  do not select based on turnaround speed; confirm genuine peer review and
  real Scopus indexing status directly, not from a promotional claim.
- **Post a preprint (arXiv/ePrint)** once a draft stabilizes — independent
  of any journal timeline, low effort, immediately citable.

---

## 5. Standing Rules Carried Forward From This Project's History

These are not optional stylistic preferences — they are lessons this
project has specifically needed enforced multiple times:

1. **Never cite a number, file, or quote that hasn't been independently
   opened/verified.** This project has twice caught fabricated-looking
   citations (a code comment that didn't exist, CSV files whose provenance
   was initially unconfirmed) before they reached a supervisor. Always
   compile/run/open the actual artifact before citing it.
2. **No "100%", "proves", "bulletproof", or unconditional-certainty language**
   attached to anything that isn't literally, unconditionally true.
   Precise, bounded claims with explicit limitations read as more credible,
   not less.
3. **Distinguish clearly, every time, between:** (a) independently computed
   results, (b) author-supplied reference data being loaded/parsed, (c)
   toy/reduced-scope self-consistency checks, and (d) real-hardware
   third-party data. Never let (c) or (b) read as if it were (a) or (d).
4. **Report negative/inconvenient findings as findings, not failures to
   hide** — e.g., the still-open instruction 4–12 discrepancy, or any case
   in Phase C/D where real data disagrees with the synthetic model. This
   project's strongest moments have come from documenting exactly this
   kind of honest discrepancy.
5. **Checksum third-party datasets the moment they're downloaded, and
   record the checksum in the repo.** The Magazin & Abdellatif dataset's
   download URL is explicitly non-persistent — the moment it's downloaded
   for Phase C, compute and commit a SHA-256 (or similar) of the archive
   before doing anything else with it. If that URL ever disappears
   mid-project, this is the only way to later prove your local copy
   matches what anyone else who mirrors it would be citing — exactly the
   kind of reproducibility gap this project's other standing rules are
   designed to prevent.

---

## 6. Phase G — Project Closeout

### Closeout Status — ALL FOUR ITEMS VERIFIED CLOSED
All four closeout items identified during the pre-submission audit have been independently confirmed and verified:

- **G1 — CLOSED (Author Correspondence Synchronization):** All statistical claims in `AUTHOR_CORRESPONDENCE_DRAFT.md` match `MANUSCRIPT.md` exactly, verified by automated audit `verify_correspondence_draft.py` (30/30 claims pass).
- **G2 — CLOSED (Formal Negative-Control Artifacts):** Dedicated script `run_negative_controls_full.py` evaluates $K=100$ resampled subsets across both permuted pairing and validated off-target quiet window (samples 900–920), writing permanent empirical results to `negative_control_results.txt`. Regression test `test_negative_controls_regression.py` integrated as Step 17 in master test runner.
- **G3 — CLOSED (Hyperparameter Documentation):** Manuscript Section 7.3 updated to state $N=3,000$ and Adam $\eta = 0.01$, matching the actual implementation in `run_learned_combiner.py`.
- **G4 — CLOSED (Duplicate Text):** Duplicate paragraph in Section 5.1 removed.

---

## 7. Phase H — Publication, Archival & Dissemination (ACTIVE)

With all technical phases (A–F) and closeout items (G1–G4) passing the 18-step automated test suite (`python replication/run_all_tests.py`), work transitions to formal publication and dissemination:

### H.1 — External Author Outreach
- **Goal:** Inform original authors Gustavo Banegas, Kirthivaasan Puniamurthy, and Chris Brzuska of our expanded scope, real EM hardware validation, and novel findings.
- **Artifact:** `publication/AUTHOR_CORRESPONDENCE_DRAFT.md` (30/30 assertions synchronized with manuscript via `publication/verify_correspondence_draft.py`).
- **Timeline:** 2-week review window for author critique and co-authorship interest before preprint posting.

### H.2 — LaTeX Camera-Ready Manuscript Preparation
- **Goal:** Convert `publication/MANUSCRIPT.md` to Springer Nature's `sn-jnl.cls` template targeting the *Journal of Cryptographic Engineering* (JCEN).
- **Directory:** `publication/latex/` with vector plots linked from `replication/plots/` and complete bibliography.

### H.3 — Open-Science Reproducibility Packaging
- **Goal:** Provide reviewers and auditors with immediate zero-setup reproducibility without requiring the 12.57 GB raw dataset.
- **Artifacts:** Lightweight 23.7 MB verification slice in `datasets/sample_hardware_chunk/`, standalone runner `datasets/verify_sample_chunk.py`, and `AUDIT_VERIFICATION_GUIDE.md`.

### H.4 — Preprint Dissemination (IACR Cryptology ePrint Archive)
- **Goal:** Establish formal scientific priority upon conclusion of the author consultation window.
- **Target:** IACR Cryptology ePrint Archive.

### H.5 — Journal Submission
- **Target:** Springer *Journal of Cryptographic Engineering* (JCEN).

