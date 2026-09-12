import os
import ast
import trsfile
from trsfile.parametermap import TraceParameterMap
from trsfile.traceparameter import ByteArrayParameter, StringParameter
import numpy as np

# Modulus and constants
Q = 3329
QINV = 3327

ZETAS = [
    2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653,
    3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254,
    817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670,
    2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628
]

def load_positions(positions_file):
    positions = []
    with open(positions_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('['):
                positions.append(ast.literal_eval(line))
    return positions

def to_int16(x):
    x = int(x) & 0xFFFF
    return x if x < 32768 else x - 65536

def smul(x, y):
    return to_int16(x) * to_int16(y)

def compute_multiplication_intermediates(a0, a1, b0, b1, zeta):
    # 13-state leakage simulation according to Listing 1.1
    poly0 = (to_int16(a1) << 16) | (int(a0) & 0xFFFF)
    poly1 = (to_int16(b1) << 16) | (int(b0) & 0xFFFF)
    
    hws = np.zeros(13, dtype=np.float32)
    # 1. ldr poly0
    hws[0] = bin(poly0 & 0xFFFFFFFF).count('1')
    # 8. smultt tmp, poly0, poly1
    tmp = smul(a1, b1)
    hws[1] = bin(tmp & 0xFFFFFFFF).count('1')
    # 9. montgomery (i) smulbt tmp2, tmp, qinv
    tmp2 = smul(tmp, QINV)
    hws[2] = bin(tmp2 & 0xFFFFFFFF).count('1')
    # 9. montgomery (ii) smlabb tmp2, q, tmp2, tmp
    tmp2 = smul(Q, tmp2) + tmp
    hws[3] = bin(tmp2 & 0xFFFFFFFF).count('1')
    # 10. smultb tmp2, tmp2, zeta
    tmp2 = smul(tmp2 >> 16, zeta)
    hws[4] = bin(tmp2 & 0xFFFFFFFF).count('1')
    # 11. smlabb tmp2, poly0, poly1, tmp2
    tmp2 = tmp2 + smul(a0, b0)
    hws[5] = bin(tmp2 & 0xFFFFFFFF).count('1')
    # 12. montgomery (i) smulbt tmp, tmp2, qinv
    tmp = smul(tmp2, QINV)
    hws[6] = bin(tmp & 0xFFFFFFFF).count('1')
    # 12. montgomery (ii) smlabb tmp, q, tmp, tmp2
    tmp = smul(Q, tmp) + tmp2
    hws[7] = bin(tmp & 0xFFFFFFFF).count('1')
    # 14. smuadx tmp2, poly0, poly1
    tmp2 = smul(a1, b0) + smul(a0, b1)
    hws[8] = bin(tmp2 & 0xFFFFFFFF).count('1')
    # 15. montgomery (i) smulbt tmp3, tmp2, qinv
    tmp3 = smul(tmp2, QINV)
    hws[9] = bin(tmp3 & 0xFFFFFFFF).count('1')
    # 15. montgomery (ii) smlabb tmp3, q, tmp3, tmp2
    tmp3 = smul(Q, tmp3) + tmp2
    hws[10] = bin(tmp3 & 0xFFFFFFFF).count('1')
    # pkhTB tmp, tmp3, tmp
    mytmp = (tmp3 >> 16) & 0xFFFF
    tmp = (mytmp << 16) | (tmp & 0xFFFF)
    hws[11] = bin(tmp & 0xFFFFFFFF).count('1')
    # str tmp3
    hws[12] = bin(tmp3 & 0xFFFFFFFF).count('1')
    
    return hws

class SyntheticTraceGenerator:
    def __init__(self, example_trs_path=None, positions_file=None):
        self.num_samples = 9148
        if positions_file is None:
            positions_file = "Attack_Kyber_ACNS2024/attack/positions_0_33_best.txt"
        self.positions = load_positions(positions_file)
        
        # Learn baseline trace statistics from example_trs if available
        if example_trs_path and os.path.exists(example_trs_path):
            with trsfile.open(example_trs_path, 'r') as traces:
                samples = np.array([t.samples for t in traces[:15]])
                self.baseline_mean = np.mean(samples, axis=0)
                self.baseline_std = np.std(samples, axis=0)
        else:
            # Default baseline: mild sinusoidal carrier + background noise
            t = np.linspace(0, 100 * np.pi, self.num_samples)
            self.baseline_mean = 0.05 * np.sin(t).astype(np.float32)
            self.baseline_std = np.full(self.num_samples, 0.01, dtype=np.float32)

    def generate_single_trace(self, a_poly, b_poly, sigma=0.015, snr_scale=0.01):
        """
        Generates a 9148-sample synthetic power trace for a full poly_basemul call.
        a_poly: 256 coefficients (secret key)
        b_poly: 256 coefficients (public ciphertext)
        """
        # Start with baseline profile
        trace = self.baseline_mean.copy()
        
        # Inject intermediate state leakage into the 33 POIs for each of the 128 multiplications
        for m in range(min(128, len(self.positions))):
            a0 = a_poly[2 * m]
            a1 = a_poly[2 * m + 1]
            b0 = b_poly[2 * m]
            b1 = b_poly[2 * m + 1]
            
            # Root zeta for this multiplication
            z_idx = m % 64
            zeta = ZETAS[z_idx] if (m < 64) else -ZETAS[z_idx]
            
            hws = compute_multiplication_intermediates(a0, a1, b0, b1, zeta)
            pois = self.positions[m]  # 33 indices
            
            # Map the 13 intermediate HWs across the 33 POI sample points
            # (Repeated clock cycles and bus transitions)
            for p_idx, sample_idx in enumerate(pois):
                state_idx = p_idx % 13
                leakage = (hws[state_idx] - 16.0) * snr_scale
                trace[sample_idx] += leakage

        # Add Gaussian noise
        noise = np.random.normal(0.0, sigma, self.num_samples).astype(np.float32)
        trace += noise
        return trace.astype(np.float32)

    def write_trs_dataset(self, filename, traces_list, coeffs_list=None):
        """
        Exports traces into a compliant Inspector .trs file.
        """
        num_traces = len(traces_list)
        headers = {
            trsfile.Header.TRS_VERSION: 2,
            trsfile.Header.SAMPLE_CODING: trsfile.SampleCoding.FLOAT,
            trsfile.Header.NUMBER_TRACES: 0,
            trsfile.Header.NUMBER_SAMPLES: self.num_samples,
            trsfile.Header.SCALE_X: 1.0,
            trsfile.Header.SCALE_Y: 1.0,
            trsfile.Header.DESCRIPTION: 'Synthetic STM32F303 Cortex-M4 Kyber Traces'
        }
        
        with trsfile.trs_open(filename, 'w', headers=headers) as out_trs:
            for i, trace in enumerate(traces_list):
                params = TraceParameterMap()
                if coeffs_list and i < len(coeffs_list):
                    # Store coefficients in header parameter
                    coeff_str = " ".join([f"{c:04x}" for c in coeffs_list[i]])
                    params['COEFFICIENTS'] = StringParameter(coeff_str)
                out_trs.append(trsfile.Trace(trsfile.SampleCoding.FLOAT, trace, parameters=params))
        print(f"[+] Successfully wrote {num_traces} traces to {filename}")

def main():
    print("\n" + "="*70)
    print("       PHASE 3: HARDWARE EMULATION & SYNTHETIC .TRS ENGINE")
    print("="*70)
    
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
    example_trs = os.path.join(workspace_root, "Attack_Kyber_ACNS2024/attack/traces_example.trs")
    positions_file = os.path.join(workspace_root, "Attack_Kyber_ACNS2024/attack/positions_0_33_best.txt")
    out_dir = os.path.join(workspace_root, "replication/phase3_hw_emulator/traces")
    os.makedirs(out_dir, exist_ok=True)
    
    gen = SyntheticTraceGenerator(example_trs, positions_file)
    
    # 1. Generate Target Trace with known secret key
    np.random.seed(1337)
    # Kyber secret key centered around 0 in [-2, 2], encoded modulo 3329
    true_secret = np.random.choice([0, 1, 2, 3327, 3328], size=256)
    # Fixed known ciphertext
    public_b = np.random.randint(0, 3329, size=256)
    
    print("[*] Generating synthetic target trace (15 acquisitions for averaging)...")
    target_traces = []
    for _ in range(15):
        target_traces.append(gen.generate_single_trace(true_secret, public_b, sigma=0.012))
        
    target_trs_path = os.path.join(out_dir, "synthetic_target_15.trs")
    gen.write_trs_dataset(target_trs_path, target_traces)
    
    # Save the secret key and ciphertext for verification
    np.save(os.path.join(out_dir, "true_secret_key.npy"), true_secret)
    np.save(os.path.join(out_dir, "public_b.npy"), public_b)
    print(f"[+] Saved secret key and public b vector to {out_dir}")

    # Display immediate preview
    print("\n" + "-"*70)
    print("  TARGET PREVIEW (Generated Ground Truth)")
    print("-" * 70)
    centered_s = [x if x <= 1664 else x - 3329 for x in true_secret[:16]]
    print("  Secret Key (First 16, centered [-2, 2]):", " ".join(f"{v:+2d}" for v in centered_s))
    print("  Secret Key (First 16, raw mod 3329):   ", " ".join(f"{x:4d}" for x in true_secret[:16]))
    print("  Public Ciphertext b (First 16):         ", " ".join(f"{x:4d}" for x in public_b[:16]))
    print("-" * 70)
    # Save waveform preview plot
    try:
        import matplotlib.pyplot as plt
        preview_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trace_preview.png")
        plt.figure(figsize=(10, 3.5), dpi=150)
        for i in range(min(3, len(target_traces))):
            plt.plot(target_traces[i], label=f"Synthetic Trace {i}", alpha=0.8, linewidth=0.8)
        plt.title("Synthetic Cortex-M4 Power Trace Preview (synthetic_target_15.trs, 9148 samples)")
        plt.xlabel("Sample Index (Time)")
        plt.ylabel("Simulated Amplitude (Power/EM)")
        plt.legend(loc="upper right")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(preview_png)
        plt.close()
        print(f"[+] Saved waveform preview plot to {preview_png}")
    except Exception as e:
        pass

    print("[i] To view the full dataset: python replication/phase3_hw_emulator/view_target.py")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
