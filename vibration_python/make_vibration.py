import numpy as np
import soundfile as sf

# --- 参数设置 ---
duration = 70.0      # 时长：60秒
f_start = 0.1        # 起始频率：1Hz
f_end = 10.0    # 结束频率：50Hz
sample_rate = 48000 # 采样率：48kHz
amplitude = 0.5     # 音量

# --- 生成线性扫频信号 ---
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
# 线性扫频公式：sin(2π * (f0 + k*t) * t)，其中 k = (f1-f0)/(2*duration)
phase = 2 * np.pi * (f_start * t + ((f_end - f_start) / (2 * duration)) * t**2)
audio_data = amplitude * np.sin(phase)

# --- 保存为 WAV 文件 ---
filename = "sweep_0.1Hz_to_10Hz_70s_0.5.wav"
sf.write(filename, audio_data, sample_rate)

print(f"✅ 音频已生成: {filename}")
print(f"📊 参数: {f_start}Hz -> {f_end}Hz | 时长: {duration}s | 采样率: {sample_rate}Hz")