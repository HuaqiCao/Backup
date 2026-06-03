#f = (2*k2*(sqrt(d^2+（c-x）^2)-b)*(c-x))/sqrt(d^2+（c-x）^2)-k1*x;


#f=-2*k2*(sqrt((sqrt((delt1+b)^2-d^2)+x)^2+d^2)-b)*(sqrt((delt1+b)^2-d^2)+x)/((sqrt((delt1+b)^2-d^2)+x)^2+d^2)+k1*(delt-x);

#-2*k2*delt1*(sqrt(b+delt1)^2-d^2)/(b+delt1) + k1*delt =0

import numpy as np
import matplotlib.pyplot as plt
import os

# 【关键】设置后端为 Agg，这样绘图时不会弹出窗口，适合批量生成图片
plt.switch_backend('Agg')

# ================= 自动获取桌面路径 =================
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
print(f"图片将自动保存到桌面：{desktop_path}\n")

# ================= 参数遍历设置区 =================
# 你可以在这里给每个参数设置多个想要遍历的值
b_values = [10.0, 12.0]
d_values = [5.0]
delt1_values = [2.0, 3.0]
delt = 15.0  # 如果 delt 不需要遍历，直接写一个固定值即可
k2 = 1.0

# ================= 开始循环遍历计算并绘图 =================
plot_count = 0

for b in b_values:
    for d in d_values:
        for delt1 in delt1_values:
            # 1. 物理条件检查：根号下的数必须大于等于0，否则跳过这组参数
            if (b + delt1)**2 - d**2 < 0:
                print(f"跳过无效参数组合: b={b}, d={d}, delt1={delt1} (根号下为负数)")
                continue

            # 2. 自动计算 k1
            term_sqrt = np.sqrt((b + delt1)**2 - d**2)
            k1 = (2 * k2 * delt1 * term_sqrt) / ((b + delt1) * delt)

            # 3. 定义并计算 f(x)
            def calculate_f(x):
                common_term = np.sqrt((delt1 + b)**2 - d**2) + x
                denominator = common_term**2 + d**2
                part1 = -2 * k2 * (np.sqrt(denominator) - b) * common_term / denominator
                part2 = k1 * (delt - x)
                return part1 + part2

            x_values = np.linspace(0, 30, 400)
            f_values = calculate_f(x_values)

            # 4. 绘图与保存
            plt.figure(figsize=(10, 6))
            plt.plot(x_values, f_values, label='f(x)', color='blue', linewidth=2)
            plt.axhline(0, color='black', linewidth=1, linestyle='--')
            
            # 生成图片标题和文件名（包含当前这组参数的信息）
            title_str = f'f(x) Curve (b={b}, d={d}, delt1={delt1}, delt={delt})'
            plt.title(title_str, fontsize=12)
            plt.xlabel('x', fontsize=12)
            plt.ylabel('f', fontsize=12)
            plt.grid(True, linestyle=':', alpha=0.7)
            plt.legend(fontsize=10)

            # 安全文件名（把小数点换成下划线，防止文件名出错）
            safe_filename = f"plot_b{b}_d{d}_delt1{delt1}_delt{delt}.png".replace('.', '_')
            save_path = os.path.join(desktop_path, safe_filename)
            
            plt.savefig(save_path, dpi=150) # 保存图片到桌面，dpi=150保证清晰度
            plt.close() # 关闭当前图片，释放内存，准备画下一张

            plot_count += 1
            print(f"成功生成第 {plot_count} 张图片：{safe_filename}")

print(f"\n全部完成！共在桌面生成了 {plot_count} 张图片。")