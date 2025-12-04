# ===============================================================
# 本程序用于根据冷盘加速度数据推算铜锅（质量 m）在弹簧–阻尼系统中
# 的最优弹簧刚度 k 和阻尼系数 c。
#
# 整体流程如下：
# 1. 读取冷盘加速度 CSV（电压转加速度步骤未在此处理，假定输入已是有效信号）。
# 2. 对加速度信号做一次积分得到速度，再积分得到位移：y(t), y'(t)。
# 3. 使用插值函数构造连续的 y(t) 和 y_dot(t)，用于微分方程求解。
# 4. 搭建铜锅相对地运动方程：
#       x' = v
#       v' = -(c/m) * (v - y_dot) - (k/m) * (x - y)
# 5. 定义目标函数：使铜锅位移 x(t) 的 RMS 最小（即振动最小）。
# 6. 通过 L-BFGS-B 优化搜索最优 k、c。
# 7. 使用最优参数重新求解微分方程，得到铜锅位移随时间变化。
# 8. 绘制冷盘位移、铜锅位移以及相对位移 y(t)-x(t)。
#
# 注意：
# - 单位未做物理校准（如电压→加速度），此代码仅用于结构优化流程验证。
# - solve_ivp 每次优化都要积分一次微分方程，计算量较大。
# ===============================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
from tkinter import Tk, filedialog
from scipy.interpolate import interp1d

# ---------------- 数值积分（梯形法累积） ----------------
def cumulative_trapezoid(y, x):
    """梯形积分：返回从 0 到每个时间点的积分值"""
    return np.concatenate([[0], np.cumsum((y[1:] + y[:-1]) * np.diff(x) / 2)])

# 系统参数
mass = 2.0              # 铜锅质量 (kg)
sampling_rate = 5000.0  # 采样率 Hz（未直接使用，仅参考）

# ---------------- 选择 CSV 文件 ----------------
root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(title="选择冷盘加速度数据 CSV 文件")

# ---------------- 读取 CSV ----------------
data = pd.read_csv(file_path, skiprows=5, header=None)
time = data[0].values
acc_voltage = data[1].values

# ---------------- 加速度预处理：去均值 ----------------
acc_voltage -= np.mean(acc_voltage)

# ---------------- 两次积分：得到速度、位移 ----------------
vel = cumulative_trapezoid(acc_voltage, time)      # y'(t)
disp = cumulative_trapezoid(vel, time)             # y(t)

# ---------------- 建立插值函数（用于 ODE 求解） ----------------
y_interp = interp1d(time, disp, bounds_error=False, fill_value="extrapolate")
y_dot_interp = interp1d(time, vel, bounds_error=False, fill_value="extrapolate")

# ---------------- 铜锅运动微分方程 ----------------
def copper_pot_ode(t, x, k, c):
    """铜锅的状态方程：x1=位移, x2=速度"""
    y = y_interp(t)      # 冷盘位移
    y_dot = y_dot_interp(t)
    x1, x2 = x

    dx1dt = x2
    dx2dt = -(c / mass) * (x2 - y_dot) - (k / mass) * (x1 - y)
    return [dx1dt, dx2dt]

# ---------------- 目标函数：最小化铜锅位移 RMS ----------------
def cost(params):
    """给定 k, c，计算铜锅位移 RMS"""
    k, c = params
    x0 = [0.0, 0.0]  # 初始静止
    sol = solve_ivp(copper_pot_ode, [time[0], time[-1]], x0,
                    t_eval=time, args=(k, c), rtol=1e-5, atol=1e-8)
    x = sol.y[0]
    return np.sqrt(np.mean(x**2))

# ---------------- 优化 k 和 c ----------------
initial_guess = [1.0, 1.0]
bounds = [(10, 10000), (0.01, 1000)]  # k, c 的范围
result = minimize(cost, initial_guess, method='L-BFGS-B', bounds=bounds)
best_k, best_c = result.x

# ---------------- 使用最优参数再求解一次 ----------------
sol = solve_ivp(copper_pot_ode, [time[0], time[-1]], [0.0, 0.0],
                t_eval=time, args=(best_k, best_c))
copper_disp = sol.y[0]

# ---------------- 绘图 ----------------
plt.figure(figsize=(12, 6))
plt.plot(time, disp, label="冷盘位移 y(t)", color='blue')
plt.plot(time, copper_disp, label="铜锅位移 x(t)", color='red')
plt.plot(time, disp - copper_disp, label="y(t) - x(t)", color='green', linestyle='--')
plt.xlabel("时间 (s)")
plt.ylabel("位移 (单位未知)")
plt.title(
    f"优化结果：k = {best_k:.2f} N/m, c = {best_c:.2f} Ns/m\n"
    f"铜锅 RMS 位移 = {np.sqrt(np.mean(copper_disp**2)):.4e}"
)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
