import os
import sys
import trsfile
import matplotlib.pyplot as plt
from trsfile.parametermap import TraceSetParameterMap

default_trs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces_example.trs")
trs_path = sys.argv[1] if len(sys.argv) > 1 else default_trs

if not os.path.exists(trs_path):
    print(f"Error: File not found: {trs_path}")
    sys.exit(1)

start = 0
number = 3

plt.figure(figsize=(12, 5))

with trsfile.open(trs_path, 'r') as traces:
    print(f"=== Headers for {os.path.basename(trs_path)} ===")
    for header, value in traces.get_headers().items():
        print(f"  {header} = {value}")
    print()

    total_traces = len(traces)
    traces_to_plot = min(number, total_traces - start)

    for idx in range(traces_to_plot):
        i = start + idx
        trace = traces[i]
        print(f"Trace {i} contains {len(trace)} samples")
        
        # Plot the actual waveform
        plt.plot(trace.samples, label=f"Trace {i}", alpha=0.8)

        # Extract coefficients if present
        if 'COEFFICIENTS' in trace.parameters:
            try:
                raw_coeffs = trace.parameters['COEFFICIENTS'].value.split()
                if len(raw_coeffs) > 28:
                    raw_coeffs = raw_coeffs[:-28]
                coefficients_str = [raw_coeffs[k] + raw_coeffs[k + 1] for k in range(0, len(raw_coeffs) - 1, 2)]
                coefficients = [int(x, 16) for x in coefficients_str]
                with open("coefficients.txt", "a") as f:
                    f.write(str(coefficients) + "\n")
            except Exception as e:
                pass

plt.xlabel("Sample Index (Time)")
plt.ylabel("Measured Amplitude (Voltage / Power)")
plt.title(f"Traces ({start} to {start + traces_to_plot - 1}) from {os.path.basename(trs_path)}")
plt.legend()
plt.tight_layout()

out_png = "trace_visualization.png"
plt.savefig(out_png, dpi=150)
print(f"\n[+] Successfully plotted {traces_to_plot} traces and saved image to: {out_png}")

# Show GUI window if interactive environment is available
try:
    if sys.stdout.isatty():
        plt.show()
except Exception:
    pass
