import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
from tkinter import Tk, filedialog
from scipy.interpolate import interp1d

# 数值积分函数
def cumulative_trapezoid(y, x):
    return np.concatenate([[0], np.cumsum((y[1:] + y[:-1]) * np.diff(x) / 2)])

mass = 2.0  # 铜锅质量 (kg)
sampling_rate = 5000.0  # 采样率 Hz

root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(title="选择冷盘加速度数据 CSV 文件")

# --- 读取 CSV 数据 ---
data = pd.read_csv(file_path, skiprows=5, header=None)
time = data[0].values
acc_voltage = data[1].values

# --- 预处理加速度 ---
acc_voltage -= np.mean(acc_voltage)
vel = cumulative_trapezoid(acc_voltage, time)
disp = cumulative_trapezoid(vel, time)

# --- 插值函数：y(t), y'(t) ---
y_interp = interp1d(time, disp, bounds_error=False, fill_value="extrapolate")
y_dot_interp = interp1d(time, vel, bounds_error=False, fill_value="extrapolate")

# --- 铜锅运动微分方程 ---
def copper_pot_ode(t, x, k, c):
    y = y_interp(t)
    y_dot = y_dot_interp(t)
    x1, x2 = x  # x1: 铜锅对地位移, x2: 铜锅对地速度
    dx1dt = x2
    dx2dt = -(c / mass) * (x2 - y_dot) - (k / mass) * (x1 - y)
    return [dx1dt, dx2dt]

# --- 目标函数：最小化铜锅对地位移 RMS(x(t)) ---
def cost(params):
    k, c = params
    x0 = [0.0, 0.0]  # 铜锅初始静止在地面
    sol = solve_ivp(copper_pot_ode, [time[0], time[-1]], x0, t_eval=time, args=(k, c),
                    rtol=1e-5, atol=1e-8)
    x = sol.y[0]  # 铜锅对地位移
    return np.sqrt(np.mean(x**2))  # RMS of x(t)

# --- 优化 ---
initial_guess = [1.0, 1.0]  # 初始猜测
bounds = [(10, 10000), (0.01, 1000)]  # 弹簧刚度 k 和阻尼系数 c 的范围
result = minimize(cost, initial_guess, method='L-BFGS-B', bounds=bounds)
best_k, best_c = result.x

# --- 使用最优参数再模拟一次 ---
sol = solve_ivp(copper_pot_ode, [time[0], time[-1]], [0.0, 0.0], t_eval=time, args=(best_k, best_c))
copper_disp = sol.y[0]  # x(t)

# --- 绘图 ---
plt.figure(figsize=(12, 6))
plt.plot(time, disp, label="冷盘位移 y(t)", color='blue')
plt.plot(time, copper_disp, label="铜锅位移 x(t)", color='red')
plt.plot(time, disp - copper_disp, label="y(t) - x(t)", color='green', linestyle='--')
plt.xlabel("时间 (s)")
plt.ylabel("位移 (单位未知)")
plt.title(f"优化结果：k = {best_k:.2f} N/m, c = {best_c:.2f} Ns/m\n铜锅 RMS 位移 = {np.sqrt(np.mean(copper_disp**2)):.4e}")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
