import pandas as pd
from tkinter import Tk, filedialog
import os

def psdata_to_csv():
    # 弹出文件选择框
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    psdata_file = filedialog.askopenfilename(
        title="选择 .psdata 文件",
        filetypes=[("PSData 文件", "*.psdata")]
    )
    
    if not psdata_file:
        print("没有选择文件")
        return

    # 尝试读取 .psdata 文件并自动检测分隔符
    try:
        # 使用 'on_bad_lines' 替代 'error_bad_lines'
        data = pd.read_csv(psdata_file, sep=None, engine='python', encoding='latin1', on_bad_lines='skip')
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return

    # 获取当前路径并保存为 .csv 文件
    current_path = os.getcwd()  # 获取当前工作目录
    csv_file = os.path.join(current_path, 'output.csv')  # 生成输出文件路径
    
    # 保存为 .csv 文件
    data.to_csv(csv_file, index=False)
    print(f"文件已保存为 {csv_file}")

if __name__ == "__main__":
    psdata_to_csv()