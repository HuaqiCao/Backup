import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.font_manager import FontProperties

# 字体
win_font = FontProperties(fname='C:/Windows/Fonts/simsun.ttc')
# Times New Roman
plt.rcParams['font.family'] = 'Times New Roman'
# 负号显示
plt.rcParams['axes.unicode_minus'] = False 
# 保证清晰度
plt.rcParams['figure.dpi'] = 150  

# 全局设置 Streamlit 网页界面字体
st.markdown("""
<style>
    /* 网页全局字体：英文 Times New Roman，中文宋体 */
    html, body, [class*="css"] {
        font-family: 'Times New Roman', 'SimSun', serif !important;
    }
    h1, h2, h3 {
        font-family: 'Times New Roman', 'SimSun', serif !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 距离平衡位置的位移
y = np.linspace(-100, 100, 1000)

# 设置页面标题
st.title("f - y 交互式图像")

# 创建两个滑块（改变a和d的值）
col1, col2 = st.columns(2)
with col1:
    a = st.slider("参数 a", min_value=24, max_value=44, step=1, value=34)
with col2:
    d = st.slider("参数 d", min_value=55, max_value=80, step=1, value=67)

# 定义绘图函数
def plot_f_y(a, d):
    f = (-2 * (119.2 - np.sqrt((a + y)**2 + d**2)) * (a + y) * 0.362 / np.sqrt((a + y)**2 + d**2) +
         2 * (119.2 - np.sqrt((-y)**2 + d**2)) * (-y) * 0.1825 / np.sqrt((-y)**2 + d**2) +
         2 * (119.2 - np.sqrt((a - y)**2 + d**2)) * (a - y) * 0.362 / np.sqrt((a - y)**2 + d**2) +
         (153.1 - 67 + y) * 0.3843)
    
    # 创建 matplotlib 图像
    fig, ax = plt.subplots(figsize=(10, 6),dpi=300)
    ax.plot(y, f, linewidth=2, color='blue')
    
    # 设置字体和标签格式
    ax.set_title(f"f - y图像, a = {a}/mm, d = {d}/mm", fontsize=16, fontproperties=win_font)
    ax.set_xlabel('y / mm', fontsize=14, fontproperties=win_font)
    ax.set_ylabel('f / N', fontsize=14, fontproperties=win_font)
    
    ax.grid(True, linestyle='--', alpha=0.7)
    
    return fig

# 调用函数并展示图像
fig = plot_f_y(a, d)
st.pyplot(fig)