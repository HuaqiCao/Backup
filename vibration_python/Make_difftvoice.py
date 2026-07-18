import numpy as np
from scipy.io import wavfile
from pathlib import Path

# ====== 参数 ======
FREQUENCY = 440      # 频率 (Hz)
DURATION = 2         # 持续时间 (秒)
VOLUME = 5         # 音量 (0.0 ~ 1.0)
SAMPLE_RATE = 44100  # 采样率 (Hz)
# ============================

# 生成正弦波
t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)
wave = VOLUME * np.sin(2 * np.pi * FREQUENCY * t)

# 1. 使用 .astype() 替代 np.int16()，避免警告
# 2. 使用 np.clip() 确保数值严格在 [-32767, 32767] 范围内，防止溢出爆音
wave_int16 = (wave * 32767).clip(-32767, 32767).astype(np.int16)

output_path = Path.cwd() / f"tone_{FREQUENCY}Hz.wav"

wavfile.write(str(output_path), SAMPLE_RATE, wave_int16)
print(f"✅ 已保存到: {output_path}")