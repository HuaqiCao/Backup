import numpy as np
import matplotlib.pyplot as plt

# 1. 加载数据
waveform = np.load(r"D:\Backup\single_cycle_smoothed.npy")

# 2. 自动获取点数，防止长度对不上报错
n = len(waveform) 

# 3. 绘图：横轴除以 5000，纵轴直接用 waveform
plt.plot(np.arange(n) / 5000, waveform)
plt.show()