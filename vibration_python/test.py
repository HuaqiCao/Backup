import numpy as np
import matplotlib.pyplot as plt

def plot_qzs_stiffness_components():
    # =================================================================================
    # 1. 参数设置 (对应MATLAB代码中的目标无量纲参数) - [保持不变]
    # =================================================================================
    delta_hat_target = 0.5      # δ̂ = δ / sqrt(a^2 + h1^2)
    a_hat_target = 0.755        # â = a / sqrt(a^2 + h1^2)
    alpha_target = 0.942        # α = k1/k2 (上/下弹簧与底部弹簧刚度比)
    alpha1_target = 0.501       # α₁ = k3/k2 (中弹簧与底部弹簧刚度比)
    gamma_target = 2.143        # γ = h/d (高度比)

    # 位移扫描范围 (对应MATLAB的 y_hat)
    y_hat = np.linspace(-10, 10, 1000)

    # =================================================================================
    # 2. 中间变量计算 (几何关系推导) - [保持不变]
    # =================================================================================
    rho_target = (1 - a_hat_target**2) / (gamma_target - 1)**2
    
    Delta_target = np.sqrt(1 + a_hat_target**2 * gamma_target**2 - 2 * a_hat_target**2 * gamma_target)
    
    delta_hat1_target = 1 - np.sqrt(1 + 2*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target) + rho_target) + delta_hat_target
    
    delta_hat2_target = 1 - np.sqrt(1 + 4*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target) + 4*rho_target) + delta_hat_target

    x_e_hat_target = np.sqrt(1 - a_hat_target**2) + np.sqrt(rho_target)

    # =================================================================================
    # 3. 初始化存储数组 - [新增分量数组]
    # =================================================================================
    K_hat = np.zeros_like(y_hat)      # 总刚度
    f_hat_curve = np.zeros_like(y_hat) # 无量纲力
    xi_hat = np.zeros_like(y_hat)     # 总位移变量
    
    # 新增：用于存储四个刚度分量的数组
    K_linear = np.ones_like(y_hat)    # 线性刚度项 (常数 1)
    K_N1 = np.zeros_like(y_hat)       # 第一组非线性项导数
    K_N3 = np.zeros_like(y_hat)       # 第二组非线性项导数
    K_N5 = np.zeros_like(y_hat)       # 第三组非线性项导数

    # =================================================================================
    # 4. 核心循环计算 - [增加分量赋值]
    # =================================================================================
    for i in range(len(y_hat)):
        xi_hat[i] = x_e_hat_target + y_hat[i]
        
        # --- 几何中间变量 P1 - P9 ---
        P1 = np.sqrt(1 - a_hat_target**2) - xi_hat[i]
        P2 = 1 - 2*np.sqrt(1 - a_hat_target**2)*xi_hat[i] + xi_hat[i]**2
        P3 = 1 + delta_hat_target
        
        P4 = np.sqrt(1 - a_hat_target**2 + rho_target + 2*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target)) - xi_hat[i]
        P5 = 1 + rho_target + 2*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target) - \
             2*np.sqrt(1 - a_hat_target**2 + rho_target + 2*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target))*xi_hat[i] + xi_hat[i]**2
        P6 = np.sqrt(1 + 2*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target) + rho_target) + delta_hat1_target
        
        P7 = np.sqrt(1 - a_hat_target**2) + 2*np.sqrt(rho_target) - xi_hat[i]
        P8 = 1 + 4*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target) + 4*rho_target - \
             2*(np.sqrt(1 - a_hat_target**2) + 2*np.sqrt(rho_target))*xi_hat[i] + xi_hat[i]**2
        P9 = np.sqrt(1 + 4*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target) + 4*rho_target) + delta_hat2_target

        # --- 导数项 dP ---
        dP1 = -1
        dP2 = -2*np.sqrt(1 - a_hat_target**2) + 2*xi_hat[i]
        dP4 = -1
        dP5 = -2*np.sqrt(1 - a_hat_target**2 + rho_target + 2*np.sqrt(1 - a_hat_target**2)*np.sqrt(rho_target)) + 2*xi_hat[i]
        dP7 = -1
        dP8 = -2*(np.sqrt(1 - a_hat_target**2) + 2*np.sqrt(rho_target)) + 2*xi_hat[i]

        # --- 刚度导数项 dN/dy ---
        # 计算各项的值
        val_dN1 = -2 * alpha_target * (1 - P3 * P2**(-0.5)) * dP1 - \
                  alpha_target * P1 * P2**(-1.5) * P3 * dP2
        
        val_dN3 = -2 * alpha1_target * (1 - P6 * P5**(-0.5)) * dP4 - \
                  alpha1_target * P4 * P5**(-1.5) * P6 * dP5
        
        val_dN5 = -2 * alpha_target * (1 - P9 * P8**(-0.5)) * dP7 - \
                  alpha_target * P7 * P8**(-1.5) * P9 * dP8

        # 存储到数组中
        K_N1[i] = val_dN1
        K_N3[i] = val_dN3
        K_N5[i] = val_dN5

        # 总刚度 = 1 + dN1 + dN3 + dN5
        K_hat[i] = 1 + val_dN1 + val_dN3 + val_dN5
        
        # 力 f (恢复力)
        term1 = 2 * alpha_target * P1 * (np.sqrt(P2) - P3) / np.sqrt(P2)
        term2 = 2 * alpha1_target * P4 * (np.sqrt(P5) - P6) / np.sqrt(P5)
        term3 = 2 * alpha_target * P7 * (np.sqrt(P8) - P9) / np.sqrt(P8)
        
        f_hat_curve[i] = xi_hat[i] - term1 - term2 - term3

    # =================================================================================
    # 5. 绘图 - [修改为绘制 5 条曲线的单轴图]
    # =================================================================================
    plt.figure(figsize=(12, 8))
    
    # 设置坐标轴范围 (根据你的截图偏好调整)
    plt.xlim(-2, 2)
    # 刚度可能会很大，这里设置一个合理的上限，或者让程序自动调整
    plt.ylim(-2, 8) 

    # 绘制四个分量 (使用较细的虚线或浅色实线，以免干扰主线)
    plt.plot(y_hat, K_linear, color='gray', linestyle=':', linewidth=1.5, label='Linear Term ($1$)')
    plt.plot(y_hat, K_N1, color='purple', linestyle='--', linewidth=1.5, label='Component $dN_1/d\hat{y}$')
    plt.plot(y_hat, K_N3, color='green', linestyle='--', linewidth=1.5, label='Component $dN_3/d\hat{y}$')
    plt.plot(y_hat, K_N5, color='orange', linestyle='--', linewidth=1.5, label='Component $dN_5/d\hat{y}$')

    # 绘制总刚度 (使用粗实线突出显示)
    plt.plot(y_hat, K_hat, color='red', linewidth=2.5, label='Total Stiffness $\hat{K}$')

    # 标签和标题
    plt.xlabel('Dimensionless Displacement $\hat{y}$', fontsize=16)
    plt.ylabel('Dimensionless Stiffness', fontsize=16)
    plt.title('Stiffness Components and Total Stiffness Curve', fontsize=18)
    
    # 添加网格和图例
    plt.grid(True, which='both', linestyle='-', alpha=0.3)
    plt.legend(fontsize=12, loc='best')
    
    plt.tight_layout()
    plt.show()

# 调用函数执行绘图
plot_qzs_stiffness_components()