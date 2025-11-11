from nptdms import TdmsFile
import pandas as pd

# 设置文件路径
tdms_file_path = r"E:\Vibration_at_300K\NI Project Data\记录-2024-06-13 042905 243.tdms"
csv_file_path = r"E:\Vibration_at_300K\NI Project Data\记录-2024-06-13 042905 243.csv"

# 读取 .tdms 文件
tdms_data = TdmsFile.read(tdms_file_path)

# 获取数据帧
df = tdms_data.as_dataframe()

# 导出为 .csv 文件
df.to_csv(csv_file_path)

print(f"转换完成，CSV 文件保存为：{csv_file_path}")
