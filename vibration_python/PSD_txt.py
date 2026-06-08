import tkinter as tk
from tkinter import filedialog
import pandas as pd
import matplotlib.pyplot as plt
import os

def select_and_plot():
    root = tk.Tk()
    root.withdraw() 
    
    file_paths = filedialog.askopenfilenames(
        title="请选择一个或多个数据文件",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    
    if not file_paths:
        print("未选择任何文件。")
        return
    
    plt.figure(figsize=(12, 6))
    
    for i, file_path in enumerate(file_paths):
        try:
            df = pd.read_csv(file_path, sep=r'\s+', skiprows=2, header=None, names=['Time', 'Voltage'])
            label_name = os.path.basename(file_path)
            
            # --- 颜色控制逻辑 ---
            if i == 0:
                # 第一个文件：浅蓝色，稍微透明
                plt.plot(df['Time'], df['Voltage'], 
                        label=label_name, 
                        color='#add8e6', 
                        linewidth=1.5, 
                        alpha=0.8)
            else:
                # 其他文件：使用 Matplotlib 默认的鲜艳颜色
                plt.plot(df['Time'], df['Voltage'], 
                        label=label_name, 
                        linewidth=1)
                        
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            
    plt.title('多文件电压-时间波形图')
    plt.xlabel('时间 (s)')
    plt.ylabel('电压 (V)')
    plt.legend(loc='best', fontsize='small')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    select_and_plot()