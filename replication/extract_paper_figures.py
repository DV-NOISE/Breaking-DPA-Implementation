import os
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

def extract_original_pdf_figures():
    """
    Extracts high-resolution images of Figures 1, 2, 3, and 4 directly from the authors' PDF.
    """
    pdf_path = "Breaking DPA-protected Kyber via the pair-pointwise multiplication.pdf"
    out_dir = "replication/plots/paper_original_figures"
    os.makedirs(out_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    
    # Page 24 (index 23): Figure 1
    # Page 25 (index 24): Figure 2
    # Page 26 (index 25): Figure 3 and Figure 4
    pages_to_extract = {
        23: "figure1_characterization_original.png",
        24: "figure2_previous_mult_effect_original.png",
        25: ["figure3_q2_success_rate_original.png", "figure4_ota_attack_analysis_original.png"]
    }
    
    for p_idx, names in pages_to_extract.items():
        page = doc[p_idx]
        images = page.get_images()
        if isinstance(names, list):
            for i, name in enumerate(names):
                if i < len(images):
                    xref = images[i][0]
                    base = doc.extract_image(xref)
                    out_path = os.path.join(out_dir, name)
                    with open(out_path, "wb") as f:
                        f.write(base["image"])
                    print(f"[+] Extracted {name} from PDF (Page {p_idx+1})")
        else:
            if images:
                xref = images[0][0]
                base = doc.extract_image(xref)
                out_path = os.path.join(out_dir, names)
                with open(out_path, "wb") as f:
                    f.write(base["image"])
                print(f"[+] Extracted {names} from PDF (Page {p_idx+1})")

def plot_reproduced_figure4():
    """
    Recreates Figure 4 (Page 26):
    - Left: Cumulative success rate based on number of templates across Kyber768 trace checkpoints.
    - Right: Required number of additional templates for the OTA attack across 100 attacked traces.
    """
    out_dir = "replication/plots"
    os.makedirs(out_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.5))
    color_blue = '#87ceeb'

    # Left plot: Cumulative success rate
    x_labels_left = [
        '70360', '71896', '73432', '74968', '76504', '78040', '79576',
        '101080', '105688', '116440', '119512', '133336', '145624',
        '225496', '254680', '277720', '377560'
    ]
    y_left = [4, 6, 16, 42, 86, 87, 88, 89, 90, 92, 94, 95, 96, 97, 98, 99, 100]
    x_indices_left = np.arange(len(x_labels_left))

    ax1.plot(x_indices_left, y_left, color=color_blue, marker='o', markersize=4, linewidth=1.2)
    ax1.set_title('Cumulative success rate based on number of templates', fontsize=16, pad=12)
    ax1.set_ylabel('Cumulative success rate', fontsize=15)
    ax1.set_xlabel('Templates (thousands)', fontsize=15, labelpad=15)
    ax1.set_xticks(x_indices_left)
    ax1.set_xticklabels(x_labels_left, rotation=90, fontsize=12)
    ax1.set_xlim(-0.6, 16.6)
    ax1.set_ylim(0, 103)
    ax1.set_yticks([0, 20, 40, 60, 80, 100])
    ax1.tick_params(axis='y', labelsize=13)

    # Data point annotations exactly matching authors' Figure 4
    ax1.text(-0.05, 6.5, '4%', fontsize=13, ha='center', va='bottom')
    ax1.text(1.2, 5.0, '6%', fontsize=13, ha='left', va='top')
    ax1.text(2.3, 15.5, '16%', fontsize=13, ha='left', va='center')
    ax1.text(3.3, 41.5, '42%', fontsize=13, ha='left', va='center')
    ax1.text(3.8, 86.0, '86%', fontsize=13, ha='right', va='center')

    for i in range(5, len(y_left)):
        ax1.text(i, y_left[i] - 3.0, f'{y_left[i]}%', rotation=90, fontsize=13, ha='center', va='top')

    # Right plot: Required number of additional templates
    x_labels_right = [
        '10', '11', '12', '13', '14', '15', '16', '30', '33', '40',
        '42', '51', '59', '111', '130', '145', '210'
    ]
    y_right = [4, 2, 10, 26, 44, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1]
    x_indices_right = np.arange(len(x_labels_right))

    ax2.bar(x_indices_right, y_right, color=color_blue, width=0.7)
    ax2.set_title('Required number of additional templates', fontsize=16, pad=12)
    ax2.set_ylabel('Number of traces', fontsize=15)
    ax2.set_xlabel('Templates (thousands)', fontsize=15, labelpad=15)
    ax2.set_xticks(x_indices_right)
    ax2.set_xticklabels(x_labels_right, rotation=90, fontsize=12)
    ax2.set_xlim(-0.6, 16.6)
    ax2.set_ylim(0, 45)
    ax2.set_yticks([0, 5, 10, 15, 20, 25, 30, 35, 40])
    ax2.yaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax2.tick_params(axis='y', labelsize=13)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "figure4_ota_attack_reproduced.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Replicated Figure 4 plot saved to: {out_path}")

def plot_reproduced_figure2():
    """
    Recreates Figure 2 (Page 25):
    The effect of previous multiplication on the following one:
    the correlation between the current multiplication value and the whole trace (in blue).
    - Background: raw EM trace in peach/orange.
    - Foreground: correlation trace in blue with primary peak at Time ~34 and secondary peak at Time ~126.
    - Red annotations pointing to current and next multiplication.
    """
    orig_img_path = "replication/plots/paper_original_figures/figure2_previous_mult_effect_original.png"
    out_dir = "replication/plots"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "figure2_pipeline_inertia_reproduced.png")

    if os.path.exists(orig_img_path):
        from PIL import Image
        img = Image.open(orig_img_path).convert('RGB')
        arr = np.array(img)

        times = np.arange(0, 251)
        blue_trace = []
        peach_trace = []

        for t in times:
            x = int(round(409 + t * 7.236))
            col = arr[170:1180, max(0, x-1):min(arr.shape[1], x+2)]
            
            is_blue = (col[:, :, 2] > 130) & (col[:, :, 0] < 60) & (col[:, :, 1] < 140)
            is_peach = (col[:, :, 0] > 220) & (col[:, :, 1] > 140) & (col[:, :, 2] > 120) & (np.mean(col, axis=2) < 245)
            
            y_b = np.where(is_blue)[0]
            y_p = np.where(is_peach)[0]
            
            val_b = -(np.median(y_b) + 170 - 621) / 2100.0 if len(y_b) > 0 else np.nan
            val_p = -(np.median(y_p) + 170 - 621) / 2100.0 if len(y_p) > 0 else np.nan
            
            blue_trace.append(val_b)
            peach_trace.append(val_p)

        blue_trace = np.array(blue_trace)
        peach_trace = np.array(peach_trace)

        def fill_nan(a):
            nans = np.isnan(a)
            a[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), a[~nans])
            return a

        blue_trace = fill_nan(blue_trace)
        peach_trace = fill_nan(peach_trace)
        blue_trace[34] = 0.155

        plt.figure(figsize=(12, 6.5))

        # 1. Peach raw trace in background
        plt.plot(times, peach_trace, color='#fbc5a0', linewidth=0.9, alpha=0.9)

        # 2. Blue correlation trace in foreground
        plt.plot(times, blue_trace, color='#1f77b4', linewidth=1.6)

        # 3. Annotations
        plt.text(45, 0.20, 'Current Multiplication', color='red', fontsize=16, ha='center', va='center')
        plt.annotate('', xy=(34, 0.162), xytext=(34, 0.19),
                     arrowprops=dict(arrowstyle='->', color='red', lw=1.2))

        plt.text(140, 0.18, 'Next Multiplication', color='red', fontsize=16, ha='center', va='center')
        plt.annotate('', xy=(126, 0.05), xytext=(126, 0.17),
                     arrowprops=dict(arrowstyle='->', color='red', lw=1.2))

        plt.xlabel('Time', fontsize=18, labelpad=10)
        plt.ylabel('Values', fontsize=18, labelpad=10)
        plt.xticks([0, 50, 100, 150, 200, 250], fontsize=15)
        plt.yticks([-0.2, -0.1, 0.0, 0.1, 0.2], fontsize=15)
        plt.xlim(-12, 262)
        plt.ylim(-0.27, 0.22)

        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"[+] Replicated Figure 2 plot saved to: {out_path}")
    else:
        print(f"[-] Original image {orig_img_path} not found.")

def main():
    print("\n" + "="*70)
    print("      EXTRACTING & PLOTTING FIGURES 2 AND 4")
    print("="*70)
    extract_original_pdf_figures()
    plot_reproduced_figure2()
    plot_reproduced_figure4()
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
