import numpy as np
import matplotlib.pyplot as plt
from ipywidgets import interact, FloatSlider

# 1. 准备好 x 轴的数据
x = np.linspace(-100, 100, 1000)

# 2. 定义绘图函数，放入你的完整公式
def plot_f_y(a, b):
    # 这里已经帮你把 MATLAB 公式翻译成了 Python 语法
    f = (-2 * (119.2 - np.sqrt((a - x)**2 + b**2)) * (a - x) * 0.362 / np.sqrt((a - x)**2 + b**2) +
         2 * (119.2 - np.sqrt(x**2 + b**2)) * x * 0.1825 / np.sqrt(x**2 + b**2) +
         2 * (119.2 - np.sqrt((a + x)**2 + b**2)) * (a + x) * 0.362 / np.sqrt((a + x)**2 + b**2) +
         (153.1 - 67 - x) * 0.3843)
    
    plt.figure(figsize=(10, 6))
    plt.plot(x, f, linewidth=2, color='blue')
    plt.title(f"f(x) 的图像, a = {a}, b = {b}", fontsize=14)
    plt.xlabel('x', fontsize=12)
    plt.ylabel('f(x)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.show()

# 3. 生成滑动条交互界面
# 设置 a 和 b 的最小值、最大值和步长
interact(plot_f_y, 
         a=FloatSlider(min=24, max=44, step=1, value=34, description='a:'), 
         b=FloatSlider(min=55, max=80, step=1, value=67, description='b:'))