import numpy as np

# waveforms1 = np.load(r"D:\Backup\single_cycle_smoothed_300K.npy ")
waveforms1 = np.load(r"D:\Backup\all_cycles_smoothed_300K.npy ")
# waveforms2 = np.load(r"D:\Backup\single_cycle_smoothed_MXC.npy")
waveforms2 = np.load(r"D:\Backup\all_cycles_smoothed_springs.npy")


#print(waveforms.shape)        # (872, 3000)  →  872 noise waveforms, 3000 samples each

# Access a single waveform
waveforms1[0]                  # first noise waveform
waveforms1[100]                 # 43rd noise waveform

waveforms2[0]                  # first noise waveform
waveforms2[100]                 # 43rd noise waveform

# Loop over all
for i, wf in enumerate(waveforms1):
    print(i, wf.shape)       

for i, wf in enumerate(waveforms2):
    print(i, wf.shape)

# Plot one
import matplotlib.pyplot as plt
plt.plot(np.arange(7142) / 10000, waveforms1[100], label="MXC", linewidth=2)
plt.plot(np.arange(7142) / 10000, waveforms2[100], label="springs", linewidth=2, alpha=0.8)
plt.legend(loc="best")
plt.show()