import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import os
import re
from itertools import combinations

def select_and_plot():
    # Initialize hidden Tkinter root
    root = tk.Tk()
    root.withdraw() 
    
    # Select multiple data files
    file_paths = filedialog.askopenfilenames(
        title="Select one or more data files",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    
    if not file_paths:
        print("No files selected.")
        root.destroy()
        return
    
    # Ask user for plotting mode: all together vs pairwise
    draw_all = messagebox.askyesno(
        "Plot Mode", 
        "Plot all files on the same chart?\n\n"
        "[Yes]: All files together\n"
        "[No]: Pairwise comparison"
    )
    
    # Prompt for observation window start time
    start_time_str = simpledialog.askstring(
        "Observation Window", 
        "Enter start time for 1s window (s)\n(e.g., 5.0 for 5.0s ~ 6.0s)", 
        parent=root
    )
    root.destroy()
    
    if start_time_str is None:
        return
        
    # Parse start time and calculate end time
    try:
        start_time = float(start_time_str)
        window_length = 1.0
        end_time = start_time + window_length
    except ValueError:
        print("Invalid time format. Exiting.")
        return
    
    # Set save directory and initialize units map
    save_dir = os.path.dirname(os.path.abspath(__file__))
    units_map = {}

    # Extract X and Y units from file headers
    for path in file_paths:
        try:
            header_lines = []
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for _ in range(3):
                    header_lines.append(f.readline().strip())
            
            unit_x_match = re.search(r'\((.*?)\)', header_lines[1])
            unit_y_match = re.search(r'\)\s*\((.*?)\)', header_lines[1]) 
            
            x_unit = unit_x_match.group(1) if unit_x_match else "X"
            y_unit = unit_y_match.group(1) if unit_y_match else "Y"
            units_map[path] = (x_unit, y_unit)
        except Exception as e:
            print(f"Error reading header {path}: {e}")
            units_map[path] = ("X", "Y")

    # Mode A: Plot all files on a single chart
    if draw_all:
        try:
            plt.figure(figsize=(12, 6))
            for path in file_paths:
                df = pd.read_csv(path, sep=r'\s+', skiprows=2, header=None, names=['Time', 'Voltage'])
                mask = (df['Time'] >= start_time) & (df['Time'] < end_time)
                plt.plot(df.loc[mask, 'Time'], df.loc[mask, 'Voltage'], 
                         label=os.path.basename(path), linewidth=1)
            
            x_unit, y_unit = units_map.get(file_paths[0], ("X", "Y"))
            plt.xlabel(x_unit)
            plt.ylabel(y_unit)
            plt.xlim(start_time, end_time)
            plt.legend(loc='best', fontsize='small')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            save_name = f"All_Compare_{start_time}s.png"
            save_path = os.path.join(save_dir, save_name)
            plt.savefig(save_path, dpi=150)
            plt.close()
            print(f"Saved (all files): {save_path}")
        except Exception as e:
            print(f"Error plotting all files: {e}")

    # Mode B: Pairwise comparison plots
    else:
        for file_a, file_b in combinations(file_paths, 2):
            try:
                df_a = pd.read_csv(file_a, sep=r'\s+', skiprows=2, header=None, names=['Time', 'Voltage'])
                df_b = pd.read_csv(file_b, sep=r'\s+', skiprows=2, header=None, names=['Time', 'Voltage'])
                
                mask_a = (df_a['Time'] >= start_time) & (df_a['Time'] < end_time)
                mask_b = (df_b['Time'] >= start_time) & (df_b['Time'] < end_time)
                
                plt.figure(figsize=(12, 6))
                plt.plot(df_a.loc[mask_a, 'Time'], df_a.loc[mask_a, 'Voltage'], 
                         label=os.path.basename(file_a), color='#add8e6', linewidth=1.5, alpha=0.8)
                plt.plot(df_b.loc[mask_b, 'Time'], df_b.loc[mask_b, 'Voltage'], 
                         label=os.path.basename(file_b), linewidth=1)
                
                x_unit, y_unit = units_map.get(file_a, ("X", "Y"))
                plt.xlabel(x_unit)
                plt.ylabel(y_unit)
                
                plt.xlim(start_time, end_time)
                plt.legend(loc='best', fontsize='small')
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                save_name = f"Compare_{os.path.splitext(os.path.basename(file_a))[0]}_vs_{os.path.splitext(os.path.basename(file_b))[0]}_{start_time}s.png"
                save_path = os.path.join(save_dir, save_name)
                plt.savefig(save_path, dpi=150)
                plt.close()
                
                print(f"Saved (pairwise): {save_path}")
            except Exception as e:
                print(f"Error comparing {os.path.basename(file_a)} & {os.path.basename(file_b)}: {e}")

if __name__ == "__main__":
    select_and_plot()