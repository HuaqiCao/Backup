import numpy as np
import matplotlib.pyplot as plt
from tkinter import filedialog, Tk
from scipy.optimize import curve_fit
import os

def particle_model(t, A, p1, tau_d1, tau_d2, tau_r, offset):
    """Particle signal model according to the image formula"""
    p2 = 1 - p1  # Constraint: p1 + p2 = 1
    return A * (p1 * np.exp(-t / tau_d1) + p2 * np.exp(-t / tau_d2) - np.exp(-t / tau_r)) + offset

def fit_particle_signal(file_path, fs=5000):
    """Process and fit a single file"""
    try:
        raw_data = np.loadtxt(file_path)
        # Basic preprocessing: baseline removal
        data = raw_data - np.mean(raw_data[:50])
        # Auto-flip pulse to ensure positive peaks
        if np.abs(np.min(data)) > np.max(data):
            data = -data
            
        peak_idx = np.argmax(data)
        fit_data = data[peak_idx:]
        t_fit = np.arange(len(fit_data)) / fs
        
        # Initial parameter guesses: [A, p1, tau_d1, tau_d2, tau_r, offset]
        p0 = [
            max(fit_data) * 2,      # A - amplitude
            0.6,                    # p1 - weight of first decay component
            0.001,                  # tau_d1 - fast decay time constant
            0.01,                   # tau_d2 - slow decay time constant  
            0.0005,                 # tau_r - rise time constant
            0                       # offset - DC offset
        ]
        
        # Set parameter bounds
        bounds = (
            [0, 0, 1e-6, 1e-6, 1e-6, -np.inf],  # lower bounds
            [np.inf, 1, 0.1, 1.0, 0.1, np.inf]   # upper bounds
        )

        popt, _ = curve_fit(particle_model, t_fit, fit_data, p0=p0, 
                          bounds=bounds, maxfev=10000)
        
        # Calculate fitted curve and individual components
        A, p1, tau_d1, tau_d2, tau_r, offset = popt
        p2 = 1 - p1
        
        t_fit_curve = particle_model(t_fit, *popt)
        
        # Calculate individual components
        fast_comp = A * p1 * np.exp(-t_fit / tau_d1) + offset/3
        slow_comp = A * p2 * np.exp(-t_fit / tau_d2) + offset/3
        rise_comp = -A * np.exp(-t_fit / tau_r) + offset/3
        
        return {
            "file_name": os.path.basename(file_path),
            "t_full": (np.arange(len(data)) - peak_idx) / fs,
            "d_full": data,
            "t_fit": t_fit,
            "fit_params": popt,
            "p2": p2,
            "fit_curve": t_fit_curve,
            "components": {
                "fast": fast_comp,
                "slow": slow_comp,
                "rise": rise_comp
            }
        }
    except Exception as e:
        print(f"File {file_path} processing failed: {e}")
        return None

def main():
    # 1. Initialize file selection
    root = Tk()
    root.withdraw()
    print("Please select particle signal files (Ctrl or Shift for multiple selections)...")
    files = filedialog.askopenfilenames(title="Select Particle Signal Files", 
                                        filetypes=[("Text/Tex files", "*.txt *.tex"), ("All files", "*.*")])
    
    if not files:
        print("No files selected.")
        return

    num_files = len(files)
    print(f"Selected {num_files} files. Starting analysis...")

    # 2. Dynamically create canvas layout
    fig, axes = plt.subplots(num_files, 1, figsize=(10, 4 * num_files), squeeze=False)
    
    for i, path in enumerate(files):
        res = fit_particle_signal(path)
        ax = axes[i, 0]
        
        if res:
            A, p1, tau_d1, tau_d2, tau_r, offset = res["fit_params"]
            p2 = res["p2"]
            
            # Terminal output parameters
            print(f"\n>>> [{res['file_name']}]")
            print(f"  A: {A:.3f}")
            print(f"  p1: {p1:.3f}, p2: {p2:.3f} (p1+p2={p1+p2:.3f})")
            print(f"  τ_d1: {tau_d1*1000:.3f} ms")
            print(f"  τ_d2: {tau_d2*1000:.3f} ms") 
            print(f"  τ_r: {tau_r*1000:.3f} ms")
            print(f"  Offset: {offset:.3f}")

            # Plot: raw data and fitted curve
            ax.plot(res["t_full"], res["d_full"], 'k.', alpha=0.15, label='Raw Data')
            ax.plot(res["t_fit"], res["fit_curve"], 'r-', linewidth=2, label='Total Fit')
            
            # Plot: decomposed components
            ax.plot(res["t_fit"], res["components"]["fast"], 'g--', alpha=0.7, 
                   label=f'Fast Decay (τ={tau_d1*1000:.2f}ms)')
            ax.plot(res["t_fit"], res["components"]["slow"], 'b--', alpha=0.7,
                   label=f'Slow Decay (τ={tau_d2*1000:.2f}ms)')
            ax.plot(res["t_fit"], res["components"]["rise"], 'm--', alpha=0.7,
                   label=f'Rise Term (τ={tau_r*1000:.2f}ms)')
            
            ax.set_title(f"File: {res['file_name']} | "
                        f"τ_d1={tau_d1*1000:.2f}ms, τ_d2={tau_d2*1000:.2f}ms, τ_r={tau_r*1000:.2f}ms")
            ax.set_ylabel("Signal Amplitude (ADC)")
            
            # Set y-axis to start from 0
            y_min = min(min(res["d_full"]), 0)
            y_max = max(res["d_full"]) * 1.1
            ax.set_ylim(y_min, y_max)
            
            ax.legend(loc='upper right', fontsize='small')
            ax.grid(True, alpha=0.2)
            
            # Add formula annotation
            formula_text = r"$V = A\left(p_1 e^{-t/\tau_{d1}} + p_2 e^{-t/\tau_{d2}} - e^{-t/\tau_r}\right) + offset$"
            ax.text(0.02, 0.98, formula_text, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        else:
            ax.text(0.5, 0.5, "Fit Failed", ha='center', va='center', transform=ax.transAxes)

    # Set common x-axis label
    for ax in axes[:, 0]:
        ax.set_xlabel("Time (s)")
    
    plt.tight_layout()
    print("\nAll files processed successfully.")
    plt.show()

if __name__ == "__main__":
    main()